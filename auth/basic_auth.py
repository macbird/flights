import base64
import os
import logging
from typing import Any, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from auth.bearer_jwt import auth_exempt_paths_from_env


class BasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, username: str, password: str) -> None:
        super().__init__(app)
        self._username = username
        self._password = password
        self._debug = os.environ.get("MCP_AUTH_DEBUG", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self._logger = logging.getLogger("mcp.auth.basic")
        self._exempt_paths = auth_exempt_paths_from_env()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        auth = request.headers.get("authorization")
        if not auth:
            if self._debug:
                self._logger.warning(
                    "401: Missing Authorization header (path=%s method=%s)",
                    request.url.path,
                    request.method,
                )
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        scheme, _, value = auth.partition(" ")
        if scheme.lower() != "basic" or not value:
            if self._debug:
                self._logger.warning(
                    "401: Invalid Authorization scheme (got=%s path=%s method=%s)",
                    scheme,
                    request.url.path,
                    request.method,
                )
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        try:
            decoded = base64.b64decode(value).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            if self._debug:
                self._logger.warning(
                    "401: Invalid Basic credentials encoding (path=%s method=%s)",
                    request.url.path,
                    request.method,
                )
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        expected = f"{self._username}:{self._password}"
        if decoded != expected:
            if self._debug:
                self._logger.warning(
                    "401: Basic credentials rejected (path=%s method=%s)",
                    request.url.path,
                    request.method,
                )
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        return await call_next(request)


def basic_auth_credentials_from_env() -> Optional[Tuple[str, str]]:
    username = os.environ.get("MCP_BASIC_USER")
    password = os.environ.get("MCP_BASIC_PASSWORD")
    if username and password:
        return username, password
    return None


def wrap_app_with_optional_basic_auth(app: Any) -> Any:
    creds = basic_auth_credentials_from_env()
    if not creds:
        return app
    username, password = creds
    app.add_middleware(BasicAuthMiddleware, username=username, password=password)
    return app

