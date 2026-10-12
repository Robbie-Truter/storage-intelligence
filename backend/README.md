# Storage Intelligence Backend

FastAPI service that talks to the Storage Intelligence MCP server and exposes an
HTTP API for the frontend. It uses LangChain for the optional, read-only analysis
agent and keeps all provider API keys on the server side.

This is a scaffold: the project layout, tooling, configuration, and test setup are
in place. Endpoint and agent behaviour is added in later milestones.

---

## Layout

```
backend/
├── pyproject.toml            # uv project; ruff / pyright / pytest config
├── pyrightconfig.json        # backend-only; points at backend/.venv
├── .python-version           # 3.13
├── .env.example              # documented config; real .env is gitignored
├── Makefile
├── src/storage_intelligence_backend/
│   ├── main.py               # create_app() + lifespan, mounts routers
│   ├── config.py             # pydantic-settings Settings
│   ├── schemas.py            # Pydantic request/response models
│   ├── mcp/
│   │   ├── manager.py        # StorageMCPClient: owns Client + MCPAdapter
│   │   └── errors.py         # MCPUnavailable, MCPToolError
│   ├── agents/
│   │   └── storage_agent.py  # build_agent(...) + read-only analysis
│   ├── cleanup/
│   │   └── preview_store.py  # in-memory, path-bound preview records
│   └── routers/
│       ├── health.py         # liveness + readiness
│       ├── disk.py           # deterministic; no LLM
│       ├── agent.py          # LLM-driven; read-only tools
│       └── cleanup.py        # preview + confirmed execute
└── tests/
```

---

## Getting Started (Local Development)

### Prerequisites

- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# From the monorepo root, enter the backend project
cd backend

# Install dependencies
uv sync

# Copy and edit environment config
cp .env.example .env

# Run the API (http://127.0.0.1:8000)
uv run storage-intelligence-backend
```

### Quality checks

```bash
uv run ruff check --fix
uv run ruff format
uv run pyright
uv run pytest
```

See `BACKEND_HANDOFF.md` at the repository root for the full design and roadmap.
