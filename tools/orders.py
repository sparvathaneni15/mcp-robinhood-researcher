import json
from datetime import datetime, timezone, timedelta
from typing import Literal

import robin_stocks.robinhood as rh
from mcp.server.fastmcp import FastMCP


def register_orders_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_recent_orders(
        days_back: int = 30,
        asset_type: Literal["stocks", "options", "crypto", "all"] = "all",
    ) -> str:
        """
        Order history for the past `days_back` days (default 30).
        Filter by asset_type: stocks, options, crypto, or all.
        Use to audit trade execution, review fill prices, or reconcile P&L.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        def _filter_by_date(orders: list, date_field: str = "created_at") -> list:
            out = []
            for o in orders:
                ts = o.get(date_field) or ""
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt >= cutoff:
                        out.append(o)
                except (ValueError, AttributeError):
                    out.append(o)
            return out

        result: dict[str, list] = {}

        if asset_type in ("stocks", "all"):
            result["stocks"] = _filter_by_date(rh.orders.get_all_stock_orders() or [])

        if asset_type in ("options", "all"):
            result["options"] = _filter_by_date(rh.orders.get_all_option_orders() or [])

        if asset_type in ("crypto", "all"):
            result["crypto"] = _filter_by_date(rh.orders.get_all_crypto_orders() or [])

        return json.dumps({
            "days_back": days_back,
            "order_counts": {k: len(v) for k, v in result.items()},
            "orders": result,
        }, indent=2)

    @mcp.tool()
    def get_dividend_history() -> str:
        """
        Full dividend history: per-symbol breakdown sorted by total received
        and a running grand total. Use to assess income yield on holdings.
        """
        dividends = rh.account.get_dividends() or []

        by_symbol: dict[str, float] = {}
        history = []

        for d in dividends:
            sym = d.get("symbol") or ""
            if not sym:
                instrument_url = d.get("instrument") or ""
                if instrument_url:
                    try:
                        instrument = rh.stocks.get_instrument_by_url(instrument_url) or {}
                        sym = instrument.get("symbol", "UNKNOWN")
                    except Exception:
                        sym = "UNKNOWN"

            amount = float(d.get("amount") or 0)
            by_symbol[sym] = round(by_symbol.get(sym, 0) + amount, 4)
            history.append({
                "symbol": sym,
                "amount": round(amount, 4),
                "rate": d.get("rate"),
                "position": d.get("position"),
                "state": d.get("state"),
                "paid_at": d.get("paid_at"),
                "payable_date": d.get("payable_date"),
                "record_date": d.get("record_date"),
            })

        total = round(sum(by_symbol.values()), 2)
        by_symbol_sorted = dict(sorted(by_symbol.items(), key=lambda x: -x[1]))

        return json.dumps({
            "total_dividends": total,
            "by_symbol": by_symbol_sorted,
            "history": history,
        }, indent=2)
