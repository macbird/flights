import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


@dataclass(frozen=True)
class JwtAuthConfig:
    jwks_url: str
    issuer: Optional[str]
    audience: Optional[str]


def jwt_auth_config_from_env() -> Optional[JwtAuthConfig]:
    jwks_url = os.environ.get("MCP_OAUTH2_JWKS_URL")
    if not jwks_url:
        return None
    issuer = os.environ.get("MCP_OAUTH2_ISSUER")
    audience = os.environ.get("MCP_OAUTH2_AUDIENCE")
    return JwtAuthConfig(jwks_url=jwks_url, issuer=issuer, audience=audience)


class BearerJwtAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, config: JwtAuthConfig) -> None:
        super().__init__(app)
        self._config = config
        self._jwk_client = PyJWKClient(config.jwks_url)

    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("authorization")
        if not auth:
            return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})

        scheme, _, value = auth.partition(" ")
        if scheme.lower() != "bearer" or not value:
            return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})

        token = value.strip()
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token).key

            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": self._config.issuer is not None,
                "verify_aud": self._config.audience is not None,
            }

            jwt.decode(
                token,
                signing_key,
                algorithms=["RS256", "RS384", "RS512"],
                issuer=self._config.issuer,
                audience=self._config.audience,
                options=options,
            )
        except Exception:
            return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})

        return await call_next(request)


def wrap_app_with_optional_bearer_jwt_auth(app: Any) -> Any:
    cfg = jwt_auth_config_from_env()
    if not cfg:
        return app
    app.add_middleware(BearerJwtAuthMiddleware, config=cfg)
    return app

