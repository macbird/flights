# Basic Auth opcional em MCP (FastMCP + SSE)

Este guia mostra como proteger um servidor MCP (Model Context Protocol) exposto via **SSE** usando **Basic Authentication**, sem afetar o transporte **stdio**.

O objetivo é simples:

- Se `MCP_BASIC_USER` e `MCP_BASIC_PASSWORD` estiverem definidos, o servidor exige `Authorization: Basic ...`
- Se não estiverem definidos, o servidor permanece **sem autenticação** (comportamento padrão)

> Observação: Basic Auth **não é recomendado** para produção na Internet sem TLS (HTTPS). Use apenas atrás de HTTPS (ex.: Render/NGINX) e, idealmente, migre para OAuth2/JWT depois.

## TL;DR (mecanismo por `env`)

Você pode controlar o mecanismo de autenticação via `MCP_AUTH_MODE`:

- `auto` (padrão): ativa Basic **se** `MCP_BASIC_USER/PASSWORD` existirem; ativa Bearer/JWT **se** `MCP_OAUTH2_JWKS_URL` existir
- `none`: desativa autenticação
- `basic`: força Basic
- `oauth2`: força Bearer/JWT (útil para OAuth2 na prática; alias: `bearer-jwt`)

## Pré-requisitos

- Python 3.10+ (recomendado)
- Dependências instaladas:

```bash
pip install -r requirements.txt
```

## 1) Criar o middleware (arquivo isolado)

Crie um módulo, por exemplo `auth/basic_auth.py`, com:

```python
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
```

## 2) Subir o SSE via Uvicorn (para poder aplicar middleware)

Em projetos com `FastMCP`, o método `mcp.run(transport="sse")` inicia o servidor internamente.
Para aplicar middleware HTTP (Basic), você pode expor o **ASGI app** do FastMCP e rodar com `uvicorn`.

Exemplo (trecho do seu `server.py`/`flight_server.py`):

```python
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from auth.basic_auth import wrap_app_with_optional_basic_auth
from auth.bearer_jwt import wrap_app_with_optional_bearer_jwt_auth


def _listen_host() -> str:
    if os.environ.get("MCP_TRANSPORT", "").lower() == "sse":
        return os.environ.get("FASTMCP_HOST", "0.0.0.0")
    return "127.0.0.1"


def _listen_port() -> int:
    port_str = os.environ.get("PORT") or os.environ.get("FASTMCP_PORT")
    return int(port_str) if port_str else 8000


mcp = FastMCP("my-mcp", host=_listen_host(), port=_listen_port())


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
        return wrap_app_with_optional_bearer_jwt_auth(app)

    raise ValueError("Invalid MCP_AUTH_MODE. Use one of: auto, none, basic, oauth2")


if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT", "").lower() == "sse":
        import uvicorn

        uvicorn.run(
            _sse_app_with_optional_basic_auth(),
            host=_listen_host(),
            port=_listen_port(),
            log_level="info",
        )
    else:
        mcp.run(transport="stdio")
```

### O que isso faz?

- `mcp.sse_app()` cria um app ASGI (`Starlette`) com as rotas do MCP (ex.: `/sse` e `/messages/`).
- `wrap_app_with_optional_basic_auth(...)` adiciona Basic somente quando as env vars existirem (ou quando `MCP_AUTH_MODE=basic`).
- `wrap_app_with_optional_bearer_jwt_auth(...)` adiciona Bearer/JWT somente quando `MCP_OAUTH2_JWKS_URL` existir (ou quando `MCP_AUTH_MODE=bearer-jwt`).
- `uvicorn.run(app, ...)` sobe o servidor HTTP hospedando o MCP.

## 3) Variáveis de ambiente

- `MCP_AUTH_MODE`: `auto` (default), `none`, `basic`, `oauth2` (alias: `bearer-jwt`)
- `MCP_BASIC_USER`: usuário do Basic Auth
- `MCP_BASIC_PASSWORD`: senha do Basic Auth
- `MCP_OAUTH2_JWKS_URL`: JWKS URL (habilita validação Bearer/JWT)
- `MCP_OAUTH2_ISSUER` (opcional): `iss` esperado do token
- `MCP_OAUTH2_AUDIENCE` (opcional): `aud` esperado do token

Quando você **não** definir essas variáveis, o Basic Auth fica desativado.

## 4) Teste local (PowerShell / Windows)

Subir o servidor com SSE + Basic:

```powershell
$env:MCP_TRANSPORT="sse"
$env:MCP_AUTH_MODE="basic"
$env:MCP_BASIC_USER="admin"
$env:MCP_BASIC_PASSWORD="admin123"
python .\flight_server.py
```

Testar sem credencial (esperado: `401`):

```powershell
curl -i http://127.0.0.1:8000/sse
```

Testar com Basic (esperado: `200` e início do stream SSE):

```powershell
curl -i -u admin:admin123 http://127.0.0.1:8000/sse
```

### Teste rápido (OAuth2 na prática via Bearer/JWT)

Se você tiver um access token OAuth2 (JWT) de um IdP (ex.: Keycloak), configure:

```powershell
$env:MCP_TRANSPORT="sse"
$env:MCP_AUTH_MODE="oauth2"
$env:MCP_OAUTH2_JWKS_URL="https://<keycloak-host>/auth/realms/<realm>/protocol/openid-connect/certs"
# opcionais:
# $env:MCP_OAUTH2_ISSUER="https://<keycloak-host>/auth/realms/<realm>"
# $env:MCP_OAUTH2_AUDIENCE="<client-id-ou-audience>"
python .\flight_server.py
```

E chame o SSE com:

```powershell
curl -i -H "Authorization: Bearer <access_token>" http://127.0.0.1:8000/sse
```

## 5) Deploy (Render / produção)

- Garanta que o endpoint esteja em **HTTPS**
- Configure `MCP_TRANSPORT=sse` (se for o seu modo de deploy)
- Configure `MCP_AUTH_MODE` (recomendado: `basic` ou `oauth2`)
- Configure secrets `MCP_BASIC_USER` e `MCP_BASIC_PASSWORD` (quando usar Basic)
- Configure secrets `MCP_OAUTH2_JWKS_URL` (e opcionais `MCP_OAUTH2_ISSUER`, `MCP_OAUTH2_AUDIENCE`) quando usar Bearer/JWT

## 6) Dicas e limitações

- **Basic Auth não resolve autorização granular** (scopes/roles). É apenas “pode/ não pode entrar”.
- Para produção, o passo seguinte comum é OAuth2 com **Bearer/JWT** (validação via JWKS).
- Se você expor o MCP na Internet, proteja também com rate limit/WAF e logs adequados.

