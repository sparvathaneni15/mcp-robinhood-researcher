import json
from typing import Literal, Optional

import robin_stocks.robinhood as rh
from mcp.server.fastmcp import FastMCP


def register_market_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_market_hours(
        market: str = "XNAS",
        date: Optional[str] = None,
    ) -> str:
        """
        Open/close hours and whether the market is open today or on a specific date.
        market: MIC code — XNAS (Nasdaq), XNYS (NYSE), XASE (AMEX).
        date: ISO date YYYY-MM-DD; omit for today.
        Use before placing trades to confirm market status or plan around holidays.
        """
        if date:
            data = rh.markets.get_market_hours(market, date)
        else:
            data = rh.markets.get_market_today_hours(market)
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_sp500_movers(direction: Literal["up", "down"] = "up") -> str:
        """
        Today's top S&P 500 movers. direction='up' for gainers, 'down' for losers.
        Use at market open to spot momentum and sector rotations.
        """
        data = rh.markets.get_top_movers_sp500(direction) or []
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_market_movers() -> str:
        """
        Today's broadly trending stocks across all markets (not limited to S&P 500).
        Use to spot emerging momentum names outside the benchmark.
        """
        data = rh.markets.get_top_movers() or []
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_top_100() -> str:
        """
        Robinhood's top-100 most popular stocks by user ownership count.
        Use as a retail sentiment and crowding indicator.
        """
        data = rh.markets.get_top_100() or []
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_stocks_by_tag(tag: str) -> str:
        """
        All stocks under a Robinhood market tag/theme.
        Common tags: 'technology', 'healthcare', 'etf', 'upcoming-earnings',
        '100-most-popular', 'cannabis', 'energy', 'finance'.
        Use for sector screening or theme-based research.
        """
        data = rh.markets.get_all_stocks_from_market_tag(tag) or []
        return json.dumps({"tag": tag, "count": len(data), "stocks": data}, indent=2)
