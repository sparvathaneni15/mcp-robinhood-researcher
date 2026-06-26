import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as accountApi from "../api/accounts.js";
import * as portfolioApi from "../api/portfolio.js";
import * as optionsApi from "../api/options.js";
import * as cryptoApi from "../api/crypto.js";
import * as stockApi from "../api/stocks.js";

export function registerReportTools(server: McpServer) {
  server.tool(
    "get_portfolio_report",
    "Generate a comprehensive portfolio report: total equity, stock/crypto/cash breakdown, total unrealized P&L across all positions, open options count, and total dividends earned.",
    {
      account_number: z
        .string()
        .optional()
        .describe("Account number; omit for default"),
    },
    async ({ account_number }) => {
      const [positions, portfolio, account, options, cryptoPositions, totalDividends] =
        await Promise.all([
          portfolioApi.getOpenPositions(account_number),
          accountApi.getPortfolioProfile(account_number),
          accountApi.getAccount(account_number),
          optionsApi.getOpenOptionPositions(account_number),
          cryptoApi.getCryptoPositions(),
          portfolioApi.getTotalDividends(),
        ]);

      // compute stock P&L
      const instruments = await Promise.all(
        positions.map((p: Record<string, unknown>) =>
          portfolioApi.getInstrumentByUrl(p.instrument as string).catch(() => null),
        ),
      );
      const symbols = instruments
        .map((i) => (i as Record<string, unknown> | null)?.symbol as string)
        .filter(Boolean);

      const quotes = symbols.length ? await stockApi.getQuotes(symbols) : [];
      const priceMap = Object.fromEntries(
        (quotes as Record<string, unknown>[]).map((q) => [
          q.symbol,
          parseFloat(q.last_trade_price as string),
        ]),
      );

      let stockEquity = 0, costBasis = 0;
      positions.forEach((p: Record<string, unknown>, i: number) => {
        const symbol = (instruments[i] as Record<string, unknown> | null)?.symbol as string;
        if (!symbol) return;
        const price = priceMap[symbol] ?? 0;
        const qty = parseFloat(p.quantity as string);
        const avg = parseFloat(p.average_buy_price as string);
        stockEquity += price * qty;
        costBasis += avg * qty;
      });

      // crypto value
      let cryptoValue = 0;
      await Promise.all(
        (cryptoPositions as Record<string, unknown>[]).map(async (c) => {
          const code = (c.currency as Record<string, unknown>)?.code as string;
          if (!code) return;
          const quote = (await cryptoApi.getCryptoQuote(code).catch(() => null)) as Record<string, unknown> | null;
          const price = parseFloat((quote?.mark_price as string) ?? "0");
          cryptoValue += parseFloat(c.quantity as string) * price;
        }),
      );

      const unrealizedPnl = stockEquity - costBasis;
      const unrealizedPct = costBasis ? (unrealizedPnl / costBasis) * 100 : 0;
      const cash =
        parseFloat(account?.cash ?? "0") +
        parseFloat(account?.uncleared_deposits ?? "0");

      const result = {
        account_number: account?.account_number,
        total_equity: portfolio?.equity,
        extended_hours_equity: portfolio?.extended_hours_equity,
        cash: +cash.toFixed(2),
        stock_equity: +stockEquity.toFixed(2),
        stock_cost_basis: +costBasis.toFixed(2),
        unrealized_pnl: +unrealizedPnl.toFixed(2),
        unrealized_pnl_pct: +unrealizedPct.toFixed(2),
        crypto_value: +cryptoValue.toFixed(2),
        open_options_count: (options as unknown[]).length,
        total_dividends_earned: +totalDividends.toFixed(2),
      };

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_dividend_report",
    "Return full dividend history with a per-symbol breakdown sorted by total received and a running total.",
    {},
    async () => {
      const [dividends, total] = await Promise.all([
        portfolioApi.getDividends(),
        portfolioApi.getTotalDividends(),
      ]);

      const bySymbol: Record<string, number> = {};
      for (const d of dividends as Record<string, unknown>[]) {
        const symbol = (d.symbol as string) ?? "UNKNOWN";
        bySymbol[symbol] = +((bySymbol[symbol] ?? 0) + parseFloat(d.amount as string)).toFixed(2);
      }

      const sorted = Object.fromEntries(
        Object.entries(bySymbol).sort(([, a], [, b]) => b - a),
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              { total_dividends: +total.toFixed(2), by_symbol: sorted, history: dividends },
              null,
              2,
            ),
          },
        ],
      };
    },
  );

  server.tool(
    "get_options_report",
    "Return a summary of all open options positions: total count, calls vs puts, expiration dates, and raw positions.",
    {
      account_number: z.string().optional().describe("Account number; omit for default"),
    },
    async ({ account_number }) => {
      const positions = (await optionsApi.getOpenOptionPositions(
        account_number,
      )) as Record<string, unknown>[];

      const calls = positions.filter((p) => p.option_type === "call");
      const puts = positions.filter((p) => p.option_type === "put");
      const expirations = [
        ...new Set(positions.map((p) => p.expiration_date as string).filter(Boolean)),
      ].sort();

      const result = {
        open_count: positions.length,
        calls: calls.length,
        puts: puts.length,
        nearest_expiration: expirations[0] ?? null,
        expirations,
        positions,
      };

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_crypto_report",
    "Return a crypto holdings report: each asset with quantity, current price, current value, and total crypto portfolio value.",
    {},
    async () => {
      const positions = (await cryptoApi.getCryptoPositions()) as Record<string, unknown>[];
      const assets: Record<string, unknown>[] = [];
      let totalValue = 0;

      await Promise.all(
        positions.map(async (p) => {
          const code = (p.currency as Record<string, unknown>)?.code as string;
          if (!code) return;
          const quote = (await cryptoApi.getCryptoQuote(code).catch(() => null)) as Record<string, unknown> | null;
          const price = parseFloat((quote?.mark_price as string) ?? "0");
          const qty = parseFloat(p.quantity as string);
          const value = price * qty;
          totalValue += value;
          assets.push({
            symbol: code,
            quantity: qty,
            price: +price.toFixed(4),
            value: +value.toFixed(2),
            cost_bases: p.cost_bases,
          });
        }),
      );

      assets.sort((a, b) => (b.value as number) - (a.value as number));

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              { total_crypto_value: +totalValue.toFixed(2), assets },
              null,
              2,
            ),
          },
        ],
      };
    },
  );
}
