import json
from typing import Literal, Optional

import robin_stocks.robinhood as rh
from robin_stocks.robinhood.helper import request_get
from mcp.server.fastmcp import FastMCP


def register_research_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_stock_overview(symbol: str) -> str:
        """
        Combined research snapshot for a ticker: current price, bid/ask, day change,
        fundamentals (PE, EPS, market cap, 52-week range, dividend yield, sector,
        description), and aggregated analyst buy/hold/sell counts.
        Use before making any position entry or sizing decision.
        """
        sym = symbol.upper()
        quotes = rh.stocks.get_quotes(sym) or []
        quote = quotes[0] if isinstance(quotes, list) and quotes else (quotes if isinstance(quotes, dict) else {})
        funds = rh.stocks.get_fundamentals(sym) or []
        fund = funds[0] if isinstance(funds, list) and funds else (funds if isinstance(funds, dict) else {})
        ratings = rh.stocks.get_ratings(sym) or {}

        buy = hold = sell = 0
        for r in (ratings.get("ratings") or []):
            t = (r.get("type") or "").lower()
            if t == "buy":
                buy += 1
            elif t == "sell":
                sell += 1
            else:
                hold += 1

        last_price = float(quote.get("last_trade_price") or 0)
        prev_close = float(quote.get("adjusted_previous_close") or 0)
        day_change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close else 0

        return json.dumps({
            "symbol": sym,
            "price": round(last_price, 4),
            "prev_close": round(prev_close, 4),
            "day_change_pct": round(day_change_pct, 2),
            "ask": quote.get("ask_price"),
            "bid": quote.get("bid_price"),
            "ask_size": quote.get("ask_size"),
            "bid_size": quote.get("bid_size"),
            "volume": quote.get("last_trade_size"),
            "market_cap": fund.get("market_cap"),
            "pe_ratio": fund.get("pe_ratio"),
            "pb_ratio": fund.get("pb_ratio"),
            "eps": fund.get("earnings_per_share"),
            "dividend_yield": fund.get("dividend_yield"),
            "52w_high": fund.get("high_52_weeks"),
            "52w_low": fund.get("low_52_weeks"),
            "shares_outstanding": fund.get("shares_outstanding"),
            "float": fund.get("float"),
            "sector": fund.get("sector"),
            "industry": fund.get("industry"),
            "description": fund.get("description"),
            "analyst_ratings": {
                "buy": buy,
                "hold": hold,
                "sell": sell,
                "summary": ratings.get("summary"),
            },
        }, indent=2)

    @mcp.tool()
    def get_news(symbol: str, limit: int = 10) -> str:
        """
        Latest news headlines for a stock (up to `limit` articles).
        Use to understand price movement catalysts or prep for earnings.
        """
        articles = rh.stocks.get_news(symbol.upper()) or []
        return json.dumps([
            {
                "title": a.get("title"),
                "source": a.get("source"),
                "published_at": a.get("published_at"),
                "summary": a.get("preview_text"),
                "url": a.get("url"),
            }
            for a in articles[:limit]
        ], indent=2)

    @mcp.tool()
    def get_earnings(symbol: str) -> str:
        """
        Earnings history and upcoming estimates: EPS actual vs estimate,
        report date, call time, and revenue. Use to track catalysts and
        assess whether a stock beat/missed expectations.
        """
        data = rh.stocks.get_earnings(symbol.upper()) or []
        if isinstance(data, dict):
            data = data.get("results", [])
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_analyst_ratings(symbol: str) -> str:
        """
        Full analyst ratings breakdown: individual firm ratings and aggregated
        buy/hold/sell counts with a summary. Use to gauge conviction shifts
        or compare sentiment across your watchlist.
        """
        data = rh.stocks.get_ratings(symbol.upper())
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_price_history(
        symbol: str,
        interval: Literal["5minute", "10minute", "hour", "day", "week"] = "day",
        span: Literal["day", "week", "month", "3month", "year", "5year"] = "3month",
        bounds: Literal["regular", "extended", "trading"] = "regular",
    ) -> str:
        """
        OHLCV price history for a stock.
        Use for technical analysis, trend identification, or comparison against portfolio history.
        """
        data = rh.stocks.get_stock_historicals(symbol.upper(), interval=interval, span=span, bounds=bounds)
        # robin_stocks wraps single-symbol result in a list
        if isinstance(data, list) and data:
            data = data[0]
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_events(symbol: str) -> str:
        """
        Corporate events for a stock: splits, spinoffs, mergers.
        Use to identify structural changes that affect position sizing or cost basis.
        """
        instruments = rh.stocks.find_instrument_data(symbol.upper()) or []
        if not instruments:
            return json.dumps({"error": f"No instrument found for {symbol}"})
        instrument_id = instruments[0].get("id") if isinstance(instruments, list) else None
        if not instrument_id:
            return json.dumps({"error": "Could not determine instrument ID"})

        data = request_get(
            "https://api.robinhood.com/marketdata/events/",
            "results",
            {"equity_instrument_id": instrument_id},
        )
        return json.dumps(data or [], indent=2)

    @mcp.tool()
    def search_stocks(query: str) -> str:
        """
        Search for stocks by company name or partial ticker.
        Returns matching instruments with symbol, name, type, and exchange.
        Use to discover tickers before researching or adding to a watchlist.
        """
        results = rh.stocks.find_instrument_data(query) or []
        if isinstance(results, dict):
            results = results.get("results", [])
        return json.dumps([
            {
                "symbol": r.get("symbol"),
                "name": r.get("simple_name") or r.get("name"),
                "type": r.get("type"),
                "exchange": r.get("primary_exchange_mic") or r.get("exchange"),
                "tradability": r.get("tradability"),
            }
            for r in results[:20]
        ], indent=2)

    @mcp.tool()
    def get_fundamentals(symbols: str) -> str:
        """
        Fundamental data for one or more tickers (comma-separated).
        Returns PE, EPS, market cap, revenue, dividend yield, 52-week range, sector.
        Use for cross-stock screening or to compare position fundamentals side-by-side.
        """
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        data = rh.stocks.get_fundamentals(sym_list) or []
        return json.dumps(data, indent=2)
