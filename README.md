# Storage Intelligence

MCP server for storage analysis using [FastMCP](https://gofastmcp.com).

> Docker deployment is planned — setup is managed via the deployment config at that time.

## Structure

```
src/storage_intelligence/
├── __init__.py         # Package marker
├── core.py             # FastMCP instance
├── server.py           # Entry point (main) + wires up tools, resources, prompts
├── tools/              # MCP tools (storage scanning)
├── resources/          # MCP resources (read-only data)
└── prompts/            # MCP prompts (message templates)
```