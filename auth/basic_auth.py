import base64
import os
from typing import Any, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class BasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, username: str, password: str) -> None:
        super().__init__(app)
        self._username = username
        self._password = password

    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("authorization")
        if not auth:
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        scheme, _, value = auth.partition(" ")
        if scheme.lower() != "basic" or not value:
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        try:
            decoded = base64.b64decode(value).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        expected = f"{self._username}:{self._password}"
        if decoded != expected:
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

