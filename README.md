# Storage Intelligence

**Storage Intelligence** is a monorepo for intelligent local storage analysis,
disk usage profiling, duplicate file detection, and automated safe cleanup
workflows.

## Repository Layout

```
storage-intelligence/
├── mcp-server/   # Python FastMCP server (tools, resources, prompts)
├── backend/      # Application backend (placeholder)
├── frontend/     # Application frontend (placeholder)
├── .opencode/    # opencode agents, commands, and skills
└── .github/      # Shared CI workflows
```

- **`mcp-server/`** — the local-first Model Context Protocol (MCP) server built
  with [FastMCP](https://gofastmcp.com). See
  [`mcp-server/README.md`](mcp-server/README.md) for features, architecture, and
  development instructions.
- **`backend/`** — placeholder for the application backend.
- **`frontend/`** — placeholder for the React dashboard UI.
- **`.opencode/`** — opencode configuration: subagents (`agents/`), slash commands
  (`command/`), and shared skills (`skills/`).

## Getting Started

The MCP server is a self-contained Python project under `mcp-server/`.

```bash
cd mcp-server
uv sync
uv run storage-intelligence
```

See [`mcp-server/README.md`](mcp-server/README.md) for full details.
