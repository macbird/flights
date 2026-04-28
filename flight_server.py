import os
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional

from auth.basic_auth import wrap_app_with_optional_basic_auth
from auth.bearer_jwt import wrap_app_with_optional_bearer_jwt_auth
from tools.external_tools import register_external_tools
from tools.core_tools import register_core_tools
from tools.resources import register_resources
from tools.prompts import register_prompts

# Directory to store flight search results
FLIGHTS_DIR = "flights"


def _listen_host() -> str:
    """HTTP bind host for SSE (mcp.server.fastmcp reads host/port from FastMCP settings, not run())."""
    if os.environ.get("MCP_TRANSPORT", "").lower() == "sse":
        return os.environ.get("FASTMCP_HOST", "0.0.0.0")
    return "127.0.0.1"


def _listen_port() -> int:
    """HTTP port: Render sets PORT; optional FASTMCP_PORT for local SSE."""
    port_str = os.environ.get("PORT") or os.environ.get("FASTMCP_PORT")
    return int(port_str) if port_str else 8000


# Initialize FastMCP server (host/port apply to SSE/streamable-http; ignored for stdio)
mcp = FastMCP("flight-assistant", host=_listen_host(), port=_listen_port())


def _sse_app_with_optional_basic_auth() -> Any:
    app = mcp.sse_app()
    mode = os.environ.get("MCP_AUTH_MODE", "").strip().lower()
    if mode in ("", "auto"):
        app = wrap_app_with_optional_bearer_jwt_auth(app)
        app = wrap_app_with_optional_basic_auth(app)
        return app

    if mode in ("none", "off", "disabled"):
        return app

    if mode in ("basic",):
        return wrap_app_with_optional_basic_auth(app)

    if mode in ("bearer", "bearer-jwt", "jwt", "oauth2"):
        if not os.environ.get("MCP_OAUTH2_JWKS_URL"):
            raise ValueError(
                "MCP_AUTH_MODE=oauth2 requires MCP_OAUTH2_JWKS_URL to be set."
            )
        return wrap_app_with_optional_bearer_jwt_auth(app)

    raise ValueError(
        "Invalid MCP_AUTH_MODE. Use one of: auto, none, basic, oauth2"
    )
    return app


def get_serpapi_key() -> str:
    """Get SerpAPI key from environment variable."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY environment variable is required")
    return api_key


def normalize_location_id(location_id: str) -> str:
    """Normalize SerpAPI location IDs (uppercase 3-letter IATA); keep Google kgmid paths."""
    trimmed = location_id.strip()
    if len(trimmed) == 3 and trimmed.isalpha():
        return trimmed.upper()
    return trimmed


register_external_tools(
    mcp,
    get_serpapi_key=get_serpapi_key,
    normalize_location_id=normalize_location_id,
    flights_dir=FLIGHTS_DIR,
)

register_core_tools(mcp, flights_dir=FLIGHTS_DIR)
register_resources(mcp, flights_dir=FLIGHTS_DIR)
register_prompts(mcp)


if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT", "").lower() == "sse":
        # mcp.server.fastmcp.FastMCP.run() only accepts transport= and mount_path=;
        # host/port are taken from FastMCP(...) above (PORT / FASTMCP_HOST).
        import uvicorn

        uvicorn.run(
            _sse_app_with_optional_basic_auth(),
            host=_listen_host(),
            port=_listen_port(),
            log_level="info",
        )
    else:
        mcp.run(transport="stdio")
