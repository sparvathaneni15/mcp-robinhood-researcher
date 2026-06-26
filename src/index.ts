import "dotenv/config";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { login } from "./auth.js";
import { registerAllTools } from "./tools/index.js";

const server = new McpServer({ name: "robinhood-researcher", version: "1.0.0" });
registerAllTools(server);

await login();
const transport = new StdioServerTransport();
await server.connect(transport);
