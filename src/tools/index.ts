import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerAccountTools } from "./accounts.js";
import { registerPortfolioTools } from "./portfolio.js";
import { registerResearchTools } from "./research.js";
import { registerMarketTools } from "./market.js";
import { registerReportTools } from "./reports.js";
import { registerCryptoTools } from "./crypto.js";

export function registerAllTools(server: McpServer): void {
  registerAccountTools(server);
  registerPortfolioTools(server);
  registerResearchTools(server);
  registerMarketTools(server);
  registerReportTools(server);
  registerCryptoTools(server);
}
