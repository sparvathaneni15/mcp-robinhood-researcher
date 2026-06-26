import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as portfolioApi from "../api/portfolio.js";
import * as accountApi from "../api/accounts.js";
import * as stockApi from "../api/stocks.js";

export function registerPortfolioTools(server: McpServer) {
  server.tool(
    "get_holdings_distribution",
    "Return a ranked holdings breakdown for an account: each position's weight %, unrealized P&L, cost basis, asset type, and a top-5 concentration summary. The primary PM view.",
    {
      account_number: z
        .string()
        .optional()
        .describe("Account number; omit for default account"),
    },
    async ({ account_number }) => {
      const [positions, portfolio, account] = await Promise.all([
        portfolioApi.getOpenPositions(account_number),
        accountApi.getPortfolioProfile(account_number),
        accountApi.getAccount(account_number),
      ]);

      const totalEquity = parseFloat(portfolio?.equity ?? "0");
      const cash =
        parseFloat(account?.cash ?? "0") +
        parseFloat(account?.uncleared_deposits ?? "0");
      const investedEquity = totalEquity - cash;

      // Batch fetch instruments then quotes/fundamentals
      const instruments = await Promise.all(
        positions.map((p: Record<string, unknown>) =>
          portfolioApi.getInstrumentByUrl(p.instrument as string).catch(() => null),
        ),
      );

      const symbols = instruments
        .map((i) => (i as Record<string, unknown> | null)?.symbol as string)
        .filter(Boolean);

      const [quotes, fundamentals] = await Promise.all([
        symbols.length ? stockApi.getQuotes(symbols) : Promise.resolve([]),
        symbols.length ? stockApi.getFundamentals(symbols) : Promise.resolve([]),
      ]);

      const quoteMap = Object.fromEntries(
        (quotes as Record<string, unknown>[]).map((q) => [q.symbol, q]),
      );
      const fundMap = Object.fromEntries(
        (fundamentals as Record<string, unknown>[]).map((f) => [f.symbol, f]),
      );

      const rows: Record<string, unknown>[] = [];
      const byType: Record<string, number> = {};

      positions.forEach((p: Record<string, unknown>, i: number) => {
        const inst = instruments[i] as Record<string, unknown> | null;
        if (!inst) return;
        const symbol = inst.symbol as string;
        const quote = quoteMap[symbol] as Record<string, unknown> | undefined;
        const fund = fundMap[symbol] as Record<string, unknown> | undefined;
        const price = parseFloat((quote?.last_trade_price as string) ?? "0");
        const qty = parseFloat(p.quantity as string);
        const avgBuy = parseFloat(p.average_buy_price as string);
        const equity = price * qty;
        const costBasis = avgBuy * qty;
        const unrealizedPnl = equity - costBasis;
        const unrealizedPct = costBasis ? (unrealizedPnl / costBasis) * 100 : 0;
        const weight = investedEquity ? (equity / investedEquity) * 100 : 0;
        const assetType = (inst.type as string) ?? "unknown";

        byType[assetType] = (byType[assetType] ?? 0) + equity;

        rows.push({
          symbol,
          name: inst.simple_name ?? inst.name,
          type: assetType,
          price,
          quantity: qty,
          avg_buy_price: avgBuy,
          equity: +equity.toFixed(2),
          weight_pct: +weight.toFixed(2),
          unrealized_pnl: +unrealizedPnl.toFixed(2),
          unrealized_pnl_pct: +unrealizedPct.toFixed(2),
          pe_ratio: fund?.pe_ratio ?? null,
        });
      });

      rows.sort((a, b) => (b.weight_pct as number) - (a.weight_pct as number));
      const top5Weight = rows.slice(0, 5).reduce((s, r) => s + (r.weight_pct as number), 0);

      const typeDistribution = Object.fromEntries(
        Object.entries(byType).map(([k, v]) => [
          k,
          +(investedEquity ? (v / investedEquity) * 100 : 0).toFixed(2),
        ]),
      );

      const result = {
        account_number: account?.account_number,
        total_equity: +totalEquity.toFixed(2),
        invested_equity: +investedEquity.toFixed(2),
        cash: +cash.toFixed(2),
        cash_weight_pct: +(totalEquity ? (cash / totalEquity) * 100 : 0).toFixed(2),
        position_count: rows.length,
        top5_concentration_pct: +top5Weight.toFixed(2),
        type_distribution: typeDistribution,
        positions: rows,
      };

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_portfolio_performance",
    "Return the historical equity curve for an account over a given time window.",
    {
      account_number: z.string().describe("Account number (required for historical lookup)"),
      interval: z
        .enum(["5minute", "10minute", "hour", "day", "week"])
        .default("day")
        .describe("Data point frequency"),
      span: z
        .enum(["day", "week", "month", "3month", "year", "5year", "all"])
        .default("3month")
        .describe("Total time window"),
      bounds: z
        .enum(["regular", "extended", "trading"])
        .default("regular"),
    },
    async ({ account_number, interval, span, bounds }) => {
      const result = await portfolioApi.getPortfolioHistoricals(
        account_number,
        interval,
        span,
        bounds,
      );
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_watchlists",
    "Return all watchlists with the symbols in each list.",
    {},
    async () => {
      const lists = await portfolioApi.getWatchlists();
      const result: Record<string, unknown[]> = {};
      await Promise.all(
        lists.map(async (l: Record<string, unknown>) => {
          const name = l.name as string;
          result[name] = await portfolioApi.getWatchlistByName(name);
        }),
      );
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );
}
