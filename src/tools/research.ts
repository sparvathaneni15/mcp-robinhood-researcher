import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as api from "../api/stocks.js";

export function registerResearchTools(server: McpServer) {
  server.tool(
    "get_stock_overview",
    "Return a combined research snapshot for a symbol: price, fundamentals (PE, EPS, market cap, 52-week range, dividend yield), and analyst rating counts — all in one call.",
    { symbol: z.string().describe("Ticker symbol (e.g. AAPL)") },
    async ({ symbol }) => {
      const upper = symbol.toUpperCase();
      const [quote, fundamentals, ratings] = await Promise.all([
        api.getQuote(upper),
        api.getFundamentals([upper]),
        api.getRatings(upper),
      ]);

      const fund = (fundamentals as Record<string, unknown>[])[0] ?? {};
      let buy = 0, hold = 0, sell = 0;
      if (Array.isArray((ratings as Record<string, unknown>).ratings)) {
        for (const r of (ratings as Record<string, unknown[]>).ratings) {
          const t = ((r as Record<string, unknown>).type as string ?? "").toLowerCase();
          if (t === "buy") buy++;
          else if (t === "sell") sell++;
          else hold++;
        }
      }

      const result = {
        symbol: upper,
        name: (quote as Record<string, unknown>).instrument,
        price: (quote as Record<string, unknown>).last_trade_price,
        previous_close: (quote as Record<string, unknown>).adjusted_previous_close,
        ask: (quote as Record<string, unknown>).ask_price,
        bid: (quote as Record<string, unknown>).bid_price,
        volume: (quote as Record<string, unknown>).last_trade_size,
        market_cap: fund.market_cap,
        pe_ratio: fund.pe_ratio,
        pb_ratio: fund.pb_ratio,
        eps: fund.earnings_per_share,
        dividend_yield: fund.dividend_yield,
        "52_week_high": fund.high_52_weeks,
        "52_week_low": fund.low_52_weeks,
        description: fund.description,
        analyst_ratings: { buy, hold, sell },
      };

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_news",
    "Return the latest news articles for a stock symbol.",
    { symbol: z.string() },
    async ({ symbol }) => {
      const result = await api.getNews(symbol.toUpperCase());
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_earnings",
    "Return earnings history and upcoming estimates: EPS actual vs. estimate, report date, and call time.",
    { symbol: z.string() },
    async ({ symbol }) => {
      const result = await api.getEarnings(symbol.toUpperCase());
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_analyst_ratings",
    "Return a full analyst ratings breakdown with individual firm-level ratings and aggregated buy/hold/sell counts.",
    { symbol: z.string() },
    async ({ symbol }) => {
      const result = await api.getRatings(symbol.toUpperCase());
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_price_history",
    "Return OHLCV price history for a stock.",
    {
      symbol: z.string(),
      interval: z
        .enum(["5minute", "10minute", "hour", "day", "week"])
        .default("day"),
      span: z
        .enum(["day", "week", "month", "3month", "year", "5year"])
        .default("3month"),
      bounds: z.enum(["regular", "extended", "trading"]).default("regular"),
    },
    async ({ symbol, interval, span, bounds }) => {
      const result = await api.getHistoricals(symbol.toUpperCase(), interval, span, bounds);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_events",
    "Return corporate events for a stock: splits, spinoffs, mergers, etc.",
    { symbol: z.string() },
    async ({ symbol }) => {
      const result = await api.getEvents(symbol.toUpperCase());
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "search_stocks",
    "Search for stocks by company name or ticker keyword. Returns matching instruments.",
    { query: z.string().describe("Company name or partial ticker") },
    async ({ query }) => {
      const result = await api.searchInstruments(query);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );
}
