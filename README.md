# mcp-robinhood-researcher

An MCP server for conversing with your Robinhood portfolio using Claude. Exposes portfolio data, stock research, options, crypto, order history, and market data as MCP tools — accessible from Claude Desktop or Claude mobile via Tailscale Funnel.

---

## Technology

| Layer | Technology |
|---|---|
| MCP framework | [FastMCP](https://github.com/jlowin/fastmcp) (`mcp[cli]` >= 1.9.0) |
| Robinhood API | [robin_stocks](https://github.com/jmfernandes/robin_stocks) 3.x |
| Auth | OAuth 2.0 (MCP 2025-03 spec) via in-process `LocalOAuthProvider` |
| Transport | Streamable HTTP (uvicorn) |
| Reverse proxy | nginx — strips `/robinhood/` path prefix for OAuth route compatibility |
| Tunnel | [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) — HTTPS exposure without port forwarding |
| Runtime | Python 3.11+, Docker (multi-stage build) |

---

## Architecture

```
Claude (mobile / desktop)
        │  HTTPS
        ▼
Tailscale Funnel  (:443)
        │
        ▼
nginx  (:80)
  /robinhood/*  →  strip prefix  →  MCP server (:8000)
  /*            →  obsidian MCP server (:3000)  [optional coexistence]
        │
        ▼
FastMCP + LocalOAuthProvider
  OAuth discovery  /.well-known/oauth-authorization-server
  OpenID Connect   /.well-known/openid-configuration
  MCP endpoint     /mcp
```

Claude completes a one-time OAuth 2.0 PKCE flow on first connect. The server auto-approves all registrations — Tailscale Funnel provides the actual network security boundary.

---

## Setup

### 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Tailscale](https://tailscale.com/) installed and authenticated on the host machine
- A Robinhood account

### 2. Clone and configure

```bash
git clone https://github.com/sparvathaneni15/mcp-robinhood-researcher.git
cd mcp-robinhood-researcher
cp .env.example .env
```

Edit `.env` and fill in your credentials (see **Getting your Robinhood tokens** below).

### 3. Getting your Robinhood tokens

Robinhood uses device-linked passkeys, so login must be done interactively in a browser. Extract the session tokens from Chrome DevTools:

1. Log into [robinhood.com](https://robinhood.com) in Chrome
2. Open DevTools (`F12`) → **Network** tab
3. Click any request to `api.robinhood.com`
4. In **Headers** → copy the value after `Authorization: Bearer ` — this is your `ROBINHOOD_ACCESS_TOKEN`
5. For the refresh token (recommended): filter the Network tab for `oauth2/token`, click the POST request → **Response** tab → copy `refresh_token`

Add both to `.env`:

```env
ROBINHOOD_ACCESS_TOKEN=eyJ...
ROBINHOOD_REFRESH_TOKEN=...   # optional but keeps session alive 23h without restart
ROBINHOOD_DEVICE_TOKEN=...    # UUID from your existing Robinhood session (optional)
```

The server auto-refreshes the access token every 23 hours using the refresh token. Without a refresh token you'll need to paste a fresh access token and restart the container when it expires (~24h).

### 4. Configure Tailscale Funnel

```bash
# Expose nginx (port 80) via Tailscale Funnel
tailscale funnel --bg 80
```

Note your machine's public URL — it looks like `https://<machine>.<tailnet>.ts.net`.

Update `MCP_BASE_URL` in `.env` and in `docker-compose.yml` to match:

```env
MCP_BASE_URL=https://<machine>.<tailnet>.ts.net/robinhood
```

### 5. Build and run

```bash
docker compose up -d --build
```

Verify the server is running:

```bash
curl https://<machine>.<tailnet>.ts.net/robinhood/.well-known/oauth-authorization-server
```

### 6. Add to Claude

In Claude Desktop or Claude mobile:

- **Settings → Connectors → Add custom connector**
- **URL:** `https://<machine>.<tailnet>.ts.net/robinhood/mcp`
- Leave OAuth Client ID and Secret blank — the server handles dynamic registration automatically

Claude will open a browser window to complete a one-time OAuth flow, then connect.

---

## Available Tools

| Category | Tools |
|---|---|
| Portfolio | `get_portfolio_summary`, `get_holdings`, `get_portfolio_history`, `get_watchlists`, `get_full_report` |
| Research | `get_stock_overview`, `get_news`, `get_earnings`, `get_analyst_ratings`, `get_price_history`, `get_fundamentals`, `get_events`, `search_stocks` |
| Options | `get_options_positions`, `get_options_chain`, `get_options_report` |
| Orders | `get_recent_orders`, `get_dividend_history` |
| Crypto | `get_crypto_holdings`, `get_crypto_quote`, `get_crypto_price_history` |
| Account | `get_account_summary`, `get_day_trades`, `get_transfer_history` |
| Market | `get_market_hours`, `get_sp500_movers`, `get_market_movers`, `get_top_100`, `get_stocks_by_tag` |

---

## Coexisting with another MCP server

nginx routes all non-`/robinhood/` traffic to port 3000 on the host, so a second MCP server (e.g. an Obsidian notes server) can share the same Tailscale URL without conflict. Its Claude connector URL remains unchanged at `https://<machine>.<tailnet>.ts.net/mcp`.

---

## Project structure

```
server.py          # FastMCP entry point + LocalOAuthProvider
auth.py            # Token injection + 23h refresh loop
nginx.conf         # Path-prefix stripping reverse proxy
docker-compose.yml # nginx + mcp services
Dockerfile         # Multi-stage Python build
requirements.txt   # Python dependencies
tools/
  portfolio.py
  research.py
  options.py
  orders.py
  crypto.py
  account.py
  market.py
```
