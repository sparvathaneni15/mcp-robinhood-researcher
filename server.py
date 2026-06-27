#!/usr/bin/env python3
"""Robinhood portfolio research MCP server (robin_stocks backend)."""
import os
import secrets
import time
from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import (
    OAuthAuthorizationServerProvider,
    OAuthClientInformationFull,
    AuthorizationParams,
    AuthorizationCode,
    AccessToken,
    RefreshToken,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.shared.auth import OAuthToken

from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from auth import login, start_refresh_loop
from tools.portfolio import register_portfolio_tools
from tools.research import register_research_tools
from tools.options import register_options_tools
from tools.orders import register_orders_tools
from tools.crypto import register_crypto_tools
from tools.account import register_account_tools
from tools.market import register_market_tools


class LocalOAuthProvider(OAuthAuthorizationServerProvider):
    """
    Minimal in-process OAuth 2.0 server for personal use.
    Auto-approves all client registrations and authorization requests.
    Tailscale Funnel provides the actual network security boundary.
    """

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._tokens: dict[str, AccessToken] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id:
            client_info.client_id = secrets.token_urlsafe(16)
        self._clients[client_info.client_id] = client_info

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        code = secrets.token_urlsafe(32)
        self._codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or ["mcp"],
            expires_at=time.time() + 300,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
        )
        redirect = str(params.redirect_uri)
        sep = "&" if "?" in redirect else "?"
        redirect += f"{sep}code={code}"
        if params.state:
            redirect += f"&state={params.state}"
        return redirect

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        return self._codes.get(authorization_code)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._codes.pop(authorization_code.code, None)
        token = secrets.token_urlsafe(32)
        self._tokens[token] = AccessToken(
            token=token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + 86400,
        )
        return OAuthToken(
            access_token=token,
            token_type="Bearer",
            expires_in=86400,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        raise NotImplementedError("Refresh tokens not supported")

    async def load_access_token(self, token: str) -> AccessToken | None:
        return self._tokens.get(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        t = token.token if hasattr(token, "token") else str(token)
        self._tokens.pop(t, None)


_base_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")
_mcp_path = os.getenv("MCP_PATH", "/mcp")

mcp = FastMCP(
    name="robinhood-researcher",
    instructions=(
        "Robinhood portfolio research server. "
        "Authenticate once; tokens auto-refresh every 23 hours via Google Authenticator TOTP. "
        "Tools cover: portfolio summary/holdings/history, stock research (overview, news, "
        "earnings, ratings, price history), options positions and chains, crypto holdings, "
        "order history, dividend income, account details, and market data."
    ),
    host="0.0.0.0",   # prevents FastMCP auto-enabling localhost-only DNS rebinding protection
    auth_server_provider=LocalOAuthProvider(),
    auth=AuthSettings(
        issuer_url=_base_url,
        resource_server_url=f"{_base_url.rstrip('/')}{_mcp_path}",
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=None,
            default_scopes=["mcp"],
        ),
    ),
    streamable_http_path=_mcp_path,
)

register_portfolio_tools(mcp)
register_research_tools(mcp)
register_options_tools(mcp)
register_orders_tools(mcp)
register_crypto_tools(mcp)
register_account_tools(mcp)
register_market_tools(mcp)

# Claude also probes /.well-known/openid-configuration during connector setup.
# FastMCP only serves oauth-authorization-server; add OpenID Connect discovery
# manually so registration doesn't fail.
async def _openid_config(request: Request) -> JSONResponse:
    base = _base_url.rstrip("/")
    return JSONResponse({
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "registration_endpoint": f"{base}/register",
        "scopes_supported": ["openid", "mcp"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
    })

mcp._custom_starlette_routes.append(
    Route("/.well-known/openid-configuration", endpoint=_openid_config, methods=["GET", "OPTIONS"])
)


def main() -> None:
    login()
    start_refresh_loop()

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))

    if transport == "http":
        import uvicorn
        app = mcp.streamable_http_app()
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
