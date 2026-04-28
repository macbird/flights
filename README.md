# flights-mcp

MCP server for flight search via [SerpAPI](https://serpapi.com) (Google Flights), based on [skarlekar/mcp_travelassistant](https://github.com/skarlekar/mcp_travelassistant).

## Local (stdio)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set SERPAPI_KEY=your_key
python flight_server.py
```

Or with FastMCP CLI and SSE on `http://127.0.0.1:8765/sse`:

```bash
set SERPAPI_KEY=your_key
python -m fastmcp run flight_server.py --transport sse --host 127.0.0.1 --port 8765
```

## Deploy on Render

1. Push this repo to GitHub.
2. In Render: **New** → **Blueprint** (connect repo) or **Web Service** with:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `python flight_server.py`
   - **Environment:** `MCP_TRANSPORT=sse` (already in `render.yaml`), `SERPAPI_KEY` = your secret.
   - **Optional Basic Auth (recommended if public):** set `MCP_BASIC_USER` and `MCP_BASIC_PASSWORD` as secrets.
3. Render sets `PORT` automatically; the app listens with SSE on `0.0.0.0`.

### Cursor (`mcp.json`)

Use your service URL and the SSE path (often `/sse`):

```json
{
  "mcpServers": {
    "flights": {
      "url": "https://<service>.onrender.com/sse"
    }
  }
}
```

## Environment variables

| Variable         | Required | Description                          |
|------------------|----------|--------------------------------------|
| `SERPAPI_KEY`    | Yes      | SerpAPI key                          |
| `MCP_TRANSPORT`  | No       | Set to `sse` on Render; omit locally for stdio |
| `PORT`           | No       | Set by Render (bind port for SSE)    |
| `FASTMCP_HOST`   | No       | Override bind host (default `0.0.0.0` when `MCP_TRANSPORT=sse`) |
| `MCP_BASIC_USER` | No       | Optional Basic Auth username for SSE |
| `MCP_BASIC_PASSWORD` | No   | Optional Basic Auth password for SSE |
| `MCP_OAUTH2_JWKS_URL` | No  | Optional OAuth2/JWT auth: JWKS URL (enables Bearer auth when set) |
| `MCP_OAUTH2_ISSUER` | No    | Optional OAuth2/JWT auth: expected `iss` claim |
| `MCP_OAUTH2_AUDIENCE` | No  | Optional OAuth2/JWT auth: expected `aud` claim |
| `MCP_AUTH_MODE` | No       | Auth mode for SSE: `auto` (default), `none`, `basic`, `oauth2` (alias: `bearer-jwt`) |
| `MCP_AUTH_DEBUG` | No      | When `true`, logs authentication failures (never logs tokens/passwords) |
| `MCP_AUTH_EXEMPT_PATHS` | No | Comma-separated paths that bypass auth (default: `/`, `/health`, `/favicon.ico`) |

This project uses **`mcp.server.fastmcp.FastMCP`** (from the `mcp` package). Host and port are set on the constructor, not on `run()`; `PORT` from Render is mapped at import time.
