import json
from typing import Literal

import robin_stocks.robinhood as rh
from mcp.server.fastmcp import FastMCP


def register_portfolio_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_portfolio_summary() -> str:
        """
        Morning snapshot: total equity, extended-hours equity, cash, buying power,
        day P&L ($ and %), and invested vs cash split.
        The first call a PM makes each day before reviewing individual positions.
        """
        profile = rh.account.load_portfolio_profile()
        account = rh.account.load_account_profile()

        if not profile:
            return json.dumps({"error": "Could not load portfolio — check authentication"})

        total_equity = float(profile.get("equity") or 0)
        ext_equity = float(profile.get("extended_hours_equity") or total_equity)
        prev_close = float(profile.get("adjusted_equity_previous_close") or 0)
        day_pnl = total_equity - prev_close
        day_pnl_pct = (day_pnl / prev_close * 100) if prev_close else 0

        acct = account or {}
        cash = float(acct.get("cash") or 0) + float(acct.get("uncleared_deposits") or 0)
        buying_power = float(acct.get("buying_power") or 0)

        return json.dumps({
            "total_equity": round(total_equity, 2),
            "extended_hours_equity": round(ext_equity, 2),
            "prev_close_equity": round(prev_close, 2),
            "day_pnl": round(day_pnl, 2),
            "day_pnl_pct": round(day_pnl_pct, 2),
            "cash": round(cash, 2),
            "buying_power": round(buying_power, 2),
            "invested_equity": round(total_equity - cash, 2),
            "cash_weight_pct": round((cash / total_equity * 100) if total_equity else 0, 2),
        }, indent=2)

    @mcp.tool()
    def get_holdings(
        sort_by: Literal["weight", "pnl_pct", "pnl_abs", "day_change", "symbol"] = "weight",
    ) -> str:
        """
        Full equity position list: symbol, weight %, quantity, avg cost, current price,
        equity, unrealized P&L ($ and %), day change ($ and %), and PE ratio.
        sort_by: weight (default), pnl_pct, pnl_abs, day_change, symbol.
        Primary PM view for reviewing concentration and performance.
        """
        holdings = rh.account.build_holdings(with_dividends=False)
        if not holdings:
            return json.dumps({"error": "No holdings found or not logged in"})

        profile = rh.account.load_portfolio_profile()
        acct = rh.account.load_account_profile() or {}
        total_equity = float((profile or {}).get("equity") or 0)
        cash = float(acct.get("cash") or 0) + float(acct.get("uncleared_deposits") or 0)
        invested = total_equity - cash

        rows = []
        type_dist: dict[str, float] = {}

        for symbol, data in holdings.items():
            price = float(data.get("price") or 0)
            qty = float(data.get("quantity") or 0)
            avg_buy = float(data.get("average_buy_price") or 0)
            equity = float(data.get("equity") or 0)
            equity_change = float(data.get("equity_change") or 0)
            day_pct = float(data.get("percent_change") or 0)
            cost_basis = avg_buy * qty
            unrealized_pnl = equity - cost_basis
            unrealized_pct = (unrealized_pnl / cost_basis * 100) if cost_basis else 0
            weight = (equity / invested * 100) if invested else 0
            asset_type = data.get("type", "stock")
            type_dist[asset_type] = round(type_dist.get(asset_type, 0) + weight, 2)

            rows.append({
                "symbol": symbol,
                "name": data.get("name", ""),
                "type": asset_type,
                "price": round(price, 4),
                "quantity": round(qty, 6),
                "avg_buy_price": round(avg_buy, 4),
                "equity": round(equity, 2),
                "weight_pct": round(weight, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pct, 2),
                "day_change": round(equity_change, 2),
                "day_change_pct": round(day_pct, 2),
                "pe_ratio": data.get("pe_ratio"),
            })

        sort_keys = {
            "weight": lambda r: -r["weight_pct"],
            "pnl_pct": lambda r: -r["unrealized_pnl_pct"],
            "pnl_abs": lambda r: -r["unrealized_pnl"],
            "day_change": lambda r: -r["day_change"],
            "symbol": lambda r: r["symbol"],
        }
        rows.sort(key=sort_keys.get(sort_by, sort_keys["weight"]))

        top5_weight = sum(r["weight_pct"] for r in rows[:5])

        return json.dumps({
            "total_equity": round(total_equity, 2),
            "invested_equity": round(invested, 2),
            "cash": round(cash, 2),
            "position_count": len(rows),
            "top5_concentration_pct": round(top5_weight, 2),
            "type_distribution": type_dist,
            "positions": rows,
        }, indent=2)

    @mcp.tool()
    def get_portfolio_history(
        interval: Literal["5minute", "10minute", "hour", "day", "week"] = "day",
        span: Literal["day", "week", "month", "3month", "year", "5year", "all"] = "3month",
        bounds: Literal["regular", "extended", "trading"] = "regular",
    ) -> str:
        """
        Historical equity curve for the account.
        interval controls data granularity; span sets the total time window.
        Use to chart portfolio performance or compute Sharpe/drawdown metrics.
        """
        data = rh.account.get_historical_portfolio(
            interval=interval, span=span, account_number=None, info=None
        )
        if not data:
            return json.dumps({"error": "No historical data returned"})

        points = data.get("equity_historicals") or []
        return json.dumps({
            "interval": interval,
            "span": span,
            "open_time": data.get("open_time"),
            "data_points": len(points),
            "equity_curve": [
                {
                    "timestamp": pt.get("begins_at"),
                    "open_equity": round(float(pt.get("open_equity") or 0), 2),
                    "close_equity": round(float(pt.get("close_equity") or 0), 2),
                    "net_return": round(float(pt.get("net_return") or 0), 6),
                    "session": pt.get("session"),
                }
                for pt in points
            ],
        }, indent=2)

    @mcp.tool()
    def get_watchlists() -> str:
        """
        All watchlists and their constituent symbols.
        Use to review the PM's monitoring universe or compare watchlist coverage to holdings.
        """
        all_lists = rh.account.get_all_watchlists()
        if not all_lists:
            return json.dumps({})

        names: list[str] = []
        if isinstance(all_lists, list):
            names = [wl.get("display_name") or wl.get("name", f"List{i}") for i, wl in enumerate(all_lists)]
        elif isinstance(all_lists, dict):
            for wl in all_lists.get("results", []):
                names.append(wl.get("display_name") or wl.get("name", "Unnamed"))

        result: dict[str, list[str]] = {}
        for name in names:
            items = rh.account.get_watchlist_by_name(name) or []
            symbols = []
            for item in items:
                sym = (
                    item.get("symbol")
                    or (item.get("instrument_data") or {}).get("symbol")
                    or ""
                )
                if sym:
                    symbols.append(sym)
            result[name] = symbols

        return json.dumps(result, indent=2)

    @mcp.tool()
    def get_full_report() -> str:
        """
        Comprehensive portfolio report: equity summary, stock unrealized P&L,
        crypto value, open options count, and total dividends earned.
        Use as an end-of-day or weekly review snapshot.
        """
        profile = rh.account.load_portfolio_profile() or {}
        acct = rh.account.load_account_profile() or {}
        holdings = rh.account.build_holdings(with_dividends=True) or {}
        crypto_positions = rh.crypto.get_crypto_positions() or []
        options_positions = rh.options.get_open_option_positions() or []
        dividends = rh.account.get_dividends() or []

        total_equity = float(profile.get("equity") or 0)
        cash = float(acct.get("cash") or 0) + float(acct.get("uncleared_deposits") or 0)

        stock_equity = 0.0
        stock_cost = 0.0
        for data in holdings.values():
            stock_equity += float(data.get("equity") or 0)
            qty = float(data.get("quantity") or 0)
            avg = float(data.get("average_buy_price") or 0)
            stock_cost += qty * avg

        crypto_value = 0.0
        for pos in crypto_positions:
            currency = pos.get("currency") or {}
            code = currency.get("code") or ""
            qty = float(pos.get("quantity") or 0)
            if code and qty:
                try:
                    q = rh.crypto.get_crypto_quote(code) or {}
                    price = float(q.get("mark_price") or q.get("bid_price") or 0)
                    crypto_value += price * qty
                except Exception:
                    pass

        total_dividends = sum(float(d.get("amount") or 0) for d in dividends)

        return json.dumps({
            "total_equity": round(total_equity, 2),
            "extended_hours_equity": float(profile.get("extended_hours_equity") or total_equity),
            "cash": round(cash, 2),
            "stock_equity": round(stock_equity, 2),
            "stock_cost_basis": round(stock_cost, 2),
            "stock_unrealized_pnl": round(stock_equity - stock_cost, 2),
            "stock_unrealized_pnl_pct": round(
                ((stock_equity - stock_cost) / stock_cost * 100) if stock_cost else 0, 2
            ),
            "crypto_value": round(crypto_value, 2),
            "open_options_count": len(options_positions),
            "total_dividends_earned": round(total_dividends, 2),
        }, indent=2)
