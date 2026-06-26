import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as api from "../api/crypto.js";

export function registerCryptoTools(server: McpServer) {
  server.tool(
    "get_crypto_quote",
    "Return the latest quote for a crypto asset.",
    { symbol: z.string().describe("Crypto ticker, e.g. BTC, ETH, SOL, DOGE") },
    async ({ symbol }) => {
      const result = await api.getCryptoQuote(symbol.toUpperCase());
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_crypto_price_history",
    "Return OHLCV price history for a crypto asset.",
    {
      symbol: z.string().describe("Crypto ticker, e.g. BTC, ETH"),
      interval: z
        .enum(["15second", "5minute", "10minute", "hour", "day", "week"])
        .default("day"),
      span: z
        .enum(["hour", "day", "week", "month", "3month", "year", "5year"])
        .default("3month"),
    },
    async ({ symbol, interval, span }) => {
      const result = await api.getCryptoHistoricals(symbol.toUpperCase(), interval, span);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );
}
