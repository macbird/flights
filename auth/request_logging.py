import logging
import os
from typing import Any, Mapping

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SENSITIVE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
    }
)


def _is_truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def request_logging_enabled_from_env() -> bool:
    return _is_truthy_env("MCP_REQUEST_LOG")


def _mask_header_value(name: str, value: str, log_sensitive: bool) -> str:
    if log_sensitive:
        return value

    lowered = name.lower()
    if lowered not in _SENSITIVE_HEADER_NAMES:
        return value

    if lowered == "authorization":
        scheme, _, token = value.partition(" ")
        if not token:
            return value
        visible = token[:12]
        return f"{scheme} {visible}***"

    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***"


def format_request_headers(
    headers: Mapping[str, str], *, log_sensitive: bool
) -> str:
    parts: list[str] = []
    for name, value in headers.items():
        masked = _mask_header_value(name, value, log_sensitive)
        parts.append(f"{name}={masked}")
    return "; ".join(parts) if parts else "(none)"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._logger = logging.getLogger("mcp.request")
        self._log_sensitive = _is_truthy_env("MCP_REQUEST_LOG_SENSITIVE")

    async def dispatch(self, request: Request, call_next) -> Response:
        client = request.client.host if request.client else "unknown"
        headers_repr = format_request_headers(
            request.headers, log_sensitive=self._log_sensitive
        )
        self._logger.info(
            "Incoming request client=%s method=%s path=%s query=%s headers=[%s]",
            client,
            request.method,
            request.url.path,
            request.url.query or "",
            headers_repr,
        )

        response = await call_next(request)
        self._logger.info(
            "Outgoing response client=%s method=%s path=%s status=%s",
            client,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response


def wrap_app_with_optional_request_logging(app: Any) -> Any:
    if not request_logging_enabled_from_env():
        return app
    app.add_middleware(RequestLoggingMiddleware)
    return app
