import json
from typing import Literal

import robin_stocks.robinhood as rh
from mcp.server.fastmcp import FastMCP


def register_crypto_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_crypto_holdings() -> str:
        """
        All crypto positions: symbol, quantity, current price, market value,
        cost basis, and unrealized P&L. Use for the crypto slice of the portfolio.
        """
        positions = rh.crypto.get_crypto_positions() or []

        assets = []
        total_value = 0.0
        total_cost = 0.0

        for pos in positions:
            currency = pos.get("currency") or {}
            code = currency.get("code") or pos.get("currency_code", "")
            qty = float(pos.get("quantity") or 0)
            if not code or qty == 0:
                continue

            try:
                quote = rh.crypto.get_crypto_quote(code) or {}
                price = float(quote.get("mark_price") or quote.get("bid_price") or 0)
            except Exception:
                price = 0.0

            value = price * qty
            cost_bases = pos.get("cost_bases") or []
            cost = float(cost_bases[0].get("direct_cost_basis") or 0) if cost_bases else 0.0
            unrealized_pnl = value - cost
            unrealized_pct = (unrealized_pnl / cost * 100) if cost else 0.0

            total_value += value
            total_cost += cost

            assets.append({
                "symbol": code,
                "name": currency.get("name", code),
                "quantity": qty,
                "price": round(price, 6),
                "value": round(value, 2),
                "cost_basis": round(cost, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pct, 2),
            })

        assets.sort(key=lambda a: -a["value"])

        return json.dumps({
            "total_crypto_value": round(total_value, 2),
            "total_cost_basis": round(total_cost, 2),
            "total_unrealized_pnl": round(total_value - total_cost, 2),
            "total_unrealized_pnl_pct": round(
                ((total_value - total_cost) / total_cost * 100) if total_cost else 0, 2
            ),
            "assets": assets,
        }, indent=2)

    @mcp.tool()
    def get_crypto_quote(symbol: str) -> str:
        """
        Real-time quote for a crypto asset (BTC, ETH, SOL, DOGE, etc.).
        Returns bid, ask, mark price, and 24-hour volume.
        """
        data = rh.crypto.get_crypto_quote(symbol.upper()) or {}
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_crypto_price_history(
        symbol: str,
        interval: Literal["15second", "5minute", "10minute", "hour", "day", "week"] = "day",
        span: Literal["hour", "day", "week", "month", "3month", "year", "5year"] = "3month",
        bounds: Literal["regular", "extended", "24_7"] = "24_7",
    ) -> str:
        """
        OHLCV price history for a crypto asset.
        bounds='24_7' includes round-the-clock data (recommended for crypto).
        Use to chart crypto vs equity portfolio performance.
        """
        data = rh.crypto.get_crypto_historicals(
            symbol.upper(), interval=interval, span=span, bounds=bounds
        )
        return json.dumps(data, indent=2)
