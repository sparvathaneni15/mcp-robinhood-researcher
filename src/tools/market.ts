import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as api from "../api/markets.js";

export function registerMarketTools(server: McpServer) {
  server.tool(
    "get_sp500_movers",
    "Return today's top S&P 500 movers in a given direction.",
    { direction: z.enum(["up", "down"]).default("up") },
    async ({ direction }) => {
      const result = await api.getSP500Movers(direction);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_top_100",
    "Return Robinhood's current top-100 most popular stocks.",
    {},
    async () => {
      const result = await api.getTop100();
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_market_movers",
    "Return today's broadly trending stocks across all markets.",
    {},
    async () => {
      const result = await api.getTopMovers();
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_stocks_by_tag",
    "Return all stocks under a Robinhood market tag/theme.",
    {
      tag: z
        .string()
        .describe(
          "Tag slug, e.g. 'technology', 'healthcare', 'upcoming-earnings', 'etf', '100-most-popular'",
        ),
    },
    async ({ tag }) => {
      const result = await api.getStocksByTag(tag);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_market_hours",
    "Return open/close hours and whether a market is open today or on a specific date.",
    {
      market: z
        .string()
        .default("XNAS")
        .describe("Market MIC code: XNAS (Nasdaq), XNYS (NYSE), XASE (AMEX)"),
      date: z
        .string()
        .optional()
        .describe("ISO date (YYYY-MM-DD); omit for today"),
    },
    async ({ market, date }) => {
      const result = date
        ? await api.getMarketHoursForDate(market, date)
        : await api.getMarketTodayHours(market);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );
}
