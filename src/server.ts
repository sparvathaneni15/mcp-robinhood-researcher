import "dotenv/config";
import express from "express";
import { randomUUID } from "crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { login } from "./auth.js";
import { registerAllTools } from "./tools/index.js";

const API_KEY = process.env.MCP_API_KEY;
if (!API_KEY) {
  console.error("MCP_API_KEY is required");
  process.exit(1);
}

const PORT = parseInt(process.env.PORT ?? "3000", 10);

// session map: sessionId → { server, transport }
const sessions = new Map<
  string,
  { server: McpServer; transport: StreamableHTTPServerTransport }
>();

function createSession() {
  const server = new McpServer({ name: "robinhood-researcher", version: "1.0.0" });
  registerAllTools(server);
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: () => randomUUID(),
    onsessioninitialized: (id) => {
      sessions.set(id, { server, transport });
    },
  });
  transport.onclose = () => {
    const id = transport.sessionId;
    if (id) sessions.delete(id);
  };
  server.connect(transport);
  return { server, transport };
}

function auth(req: express.Request, res: express.Response): boolean {
  const bearer = req.headers.authorization?.replace("Bearer ", "");
  const key = bearer ?? (req.query.key as string | undefined);
  if (key !== API_KEY) {
    res.status(401).json({ error: "Unauthorized" });
    return false;
  }
  return true;
}

const app = express();
app.use(express.json());

app.post("/mcp", (req, res) => {
  if (!auth(req, res)) return;
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (sessionId && sessions.has(sessionId)) {
    sessions.get(sessionId)!.transport.handleRequest(req, res, req.body);
  } else {
    const { transport } = createSession();
    transport.handleRequest(req, res, req.body);
  }
});

app.get("/mcp", (req, res) => {
  if (!auth(req, res)) return;
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (!sessionId || !sessions.has(sessionId)) {
    res.status(404).json({ error: "Session not found" });
    return;
  }
  sessions.get(sessionId)!.transport.handleRequest(req, res);
});

app.delete("/mcp", (req, res) => {
  if (!auth(req, res)) return;
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (sessionId && sessions.has(sessionId)) {
    sessions.get(sessionId)!.transport.close();
  }
  res.status(200).end();
});

(async () => {
  await login();
  app.listen(PORT, () => console.log(`robinhood-researcher MCP running on port ${PORT}`));
})();
