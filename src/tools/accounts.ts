import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as api from "../api/accounts.js";

export function registerAccountTools(server: McpServer) {
  server.tool(
    "get_account_summary",
    "Return a full snapshot of one account: equity, extended-hours equity, cash, buying power, margin details, and day-trade count. Pass account_number to target a specific account.",
    { account_number: z.string().optional().describe("Account number; omit for default account") },
    async ({ account_number }) => {
      const [account, portfolio] = await Promise.all([
        api.getAccount(account_number),
        api.getPortfolioProfile(account_number),
      ]);
      const result = {
        account_number: account?.account_number,
        account_type: account?.type,
        equity: portfolio?.equity,
        extended_hours_equity: portfolio?.extended_hours_equity,
        last_core_equity: portfolio?.last_core_equity,
        cash: account?.cash,
        uncleared_deposits: account?.uncleared_deposits,
        buying_power: account?.buying_power,
        unsettled_funds: account?.unsettled_funds,
        sma: account?.sma,
        day_trade_count: account?.day_trade_count,
        only_position_closing_trades: account?.only_position_closing_trades,
      };
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "list_accounts",
    "List all Robinhood accounts on file with account numbers, types, and equity. Use this first to discover account_numbers to pass into other tools.",
    {},
    async () => {
      const accounts = (await api.getAccounts()) as Record<string, unknown>[];
      const portfolios = await Promise.all(
        accounts.map((a) =>
          api.getPortfolioProfile(a.account_number as string).catch(() => null),
        ),
      );
      const result = accounts.map((a, i) => ({
        account_number: a.account_number,
        type: a.type,
        equity: portfolios[i]?.equity,
        buying_power: a.buying_power,
        cash: a.cash,
      }));
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_day_trades",
    "Return recent day trades for an account. Use to monitor PDT rule proximity (3 day trades in 5 days triggers PDT).",
    { account_number: z.string().describe("Account number (required)") },
    async ({ account_number }) => {
      const result = await api.getDayTrades(account_number);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.tool(
    "get_transfer_history",
    "Return ACH bank transfer history. Optionally filter by direction.",
    {
      direction: z
        .enum(["deposit", "withdraw"])
        .optional()
        .describe("Filter to deposits or withdrawals; omit for all"),
    },
    async ({ direction }) => {
      const result = await api.getBankTransfers(direction);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );
}
