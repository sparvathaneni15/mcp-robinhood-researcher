import json
from typing import Literal, Optional

import robin_stocks.robinhood as rh
from mcp.server.fastmcp import FastMCP


def register_options_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_options_positions() -> str:
        """
        All open options positions: symbol, strike, expiration, call/put, quantity,
        avg cost, and total cost basis (quantity × avg_price × 100).
        Use to review the current options book and flag upcoming expirations.
        """
        positions = rh.options.get_open_option_positions() or []

        rows = []
        calls = puts = 0
        expirations: set[str] = set()

        for pos in positions:
            opt_type = pos.get("option_type") or pos.get("type", "")
            if opt_type == "call":
                calls += 1
            elif opt_type == "put":
                puts += 1

            expiry = pos.get("expiration_date") or ""
            if expiry:
                expirations.add(expiry)

            qty = float(pos.get("quantity") or 0)
            avg_price = float(pos.get("average_price") or 0)
            cost_basis = qty * avg_price * 100  # one contract = 100 shares

            rows.append({
                "symbol": pos.get("chain_symbol"),
                "option_type": opt_type,
                "strike_price": pos.get("strike_price"),
                "expiration_date": expiry,
                "quantity": qty,
                "avg_price": round(avg_price, 4),
                "cost_basis": round(cost_basis, 2),
                "tradability": pos.get("tradability"),
                "created_at": pos.get("created_at"),
            })

        rows.sort(key=lambda p: (p.get("expiration_date") or "", p.get("symbol") or ""))

        return json.dumps({
            "open_count": len(rows),
            "calls": calls,
            "puts": puts,
            "upcoming_expirations": sorted(expirations),
            "positions": rows,
        }, indent=2)

    @mcp.tool()
    def get_options_chain(
        symbol: str,
        expiration_date: Optional[str] = None,
        option_type: Optional[Literal["call", "put"]] = None,
    ) -> str:
        """
        Options chain for a ticker. Filter by expiration_date (YYYY-MM-DD) and/or
        option_type (call/put). Without filters, returns chain metadata.
        Use to evaluate hedging, covered calls, or speculative positions.
        """
        sym = symbol.upper()
        if expiration_date:
            data = rh.options.find_options_by_expiration(
                sym,
                expirationDate=expiration_date,
                optionType=option_type,
            )
        else:
            data = rh.options.get_chains(sym)
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_options_report() -> str:
        """
        Summarized options book: count by type, nearest expiration, total cost basis,
        and full position list. Use as a morning options exposure check.
        """
        positions = rh.options.get_open_option_positions() or []

        calls = [p for p in positions if (p.get("option_type") or p.get("type")) == "call"]
        puts = [p for p in positions if (p.get("option_type") or p.get("type")) == "put"]
        expirations = sorted({
            p.get("expiration_date") for p in positions if p.get("expiration_date")
        })
        total_cost = sum(
            float(p.get("quantity") or 0) * float(p.get("average_price") or 0) * 100
            for p in positions
        )

        return json.dumps({
            "open_count": len(positions),
            "calls": len(calls),
            "puts": len(puts),
            "total_cost_basis": round(total_cost, 2),
            "nearest_expiration": expirations[0] if expirations else None,
            "all_expirations": expirations,
            "positions": positions,
        }, indent=2)
