# Storage Intelligence — Backend

A FastAPI service that talks to the Storage Intelligence **MCP server** over MCP
and exposes an HTTP API for the frontend, plus an optional read-only LLM
analysis agent.

Provider API keys live on the backend only and are never sent to the client.
The service runs locally: it launches the MCP server as a child process over
stdio and shares that one connection between the deterministic REST routes and
the agent.

This is the `backend/` package of the Storage Intelligence monorepo. The
project overview lives in the [root README](../README.md); the server this
service calls lives in [`mcp-server/`](../mcp-server/README.md).

---

## Contents

- [Architecture](#architecture)
- [Directory structure](#directory-structure)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Disk](#disk)
  - [Agent](#agent)
  - [Cleanup](#cleanup)
- [The read-only agent](#the-read-only-agent)
- [Cleanup safety model](#cleanup-safety-model)
- [Error mapping](#error-mapping)
- [Configuration](#configuration)
- [Getting started](#getting-started)
- [Postman collection](#postman-collection)
- [Quality checks](#quality-checks)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                Frontend (React dashboard) — placeholder          │
└───────────────────────────────┬──────────────────────────────────┘
                                │  HTTP / JSON
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│              Backend — FastAPI + LangChain                       │
│                                                                  │
│  routers/    health · disk · agent · cleanup                     │
│  mcp/        StorageMCPClient: stdio subprocess + MCPAdapter      │
│  agents/     read-only analysis agent                            │
└───────────────────────────────┬──────────────────────────────────┘
                                │  MCP over stdio
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│              Storage Intelligence — MCP Server                   │
└───────────────────────────────┬──────────────────────────────────┘
                                │  local file I/O
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Local File System                         │
└──────────────────────────────────────────────────────────────────┘
```

The backend owns a **single** MCP subprocess for its whole lifetime. The
`MCPAdapter` clones the client object but shares the transport, so the
deterministic `call_tool` path and the LangChain tools run against the same
subprocess.

---

## Directory structure

```
backend/
├── pyproject.toml            # uv project; ruff / pyright / pytest config
├── .python-version           # 3.13
├── .env.example              # documented config; the real .env is gitignored
├── Makefile                  # run · dev · test · lint · format · typecheck · check
├── src/storage_intelligence_backend/
│   ├── main.py               # create_app() + lifespan; mounts the routers
│   ├── config.py             # pydantic-settings Settings (STORAGE_BACKEND_ prefix)
│   ├── schemas.py            # Pydantic request/response models
│   ├── deps.py               # dependency provider for the MCP manager
│   ├── mcp/
│   │   ├── manager.py        # StorageMCPClient: client + adapter + allowlist
│   │   └── errors.py         # MCPError, MCPUnavailable, MCPToolError
│   ├── agents/
│   │   ├── models.py         # MODEL_CATALOG: the selectable models
│   │   └── storage_agent.py  # build_agent(...) + run_readonly_analysis(...)
│   ├── cleanup/
│   │   └── preview_store.py  # unused scaffolding; v1 has no preview store
│   └── routers/
│       ├── health.py         # liveness + readiness
│       ├── disk.py           # deterministic; no LLM
│       ├── agent.py          # LLM-driven; read-only tools
│       └── cleanup.py        # execute: submits paths to MCP trash_path
├── postman/                  # Postman collection, environment, workspace globals
└── tests/
```

---

## Endpoints

Interactive API docs are served at `http://127.0.0.1:8000/docs`.

| Method & route | MCP tool / behaviour | Notes |
| -------------- | -------------------- | ----- |
| `GET /health` | — | Liveness. Cheap, no MCP dependency |
| `GET /health/ready` | — | Readiness. 503 when MCP is down; reports `tool_count` |
| `GET /api/disk/usage` | `disk_usage` | `path` (optional) |
| `GET /api/disk/directory` | `directory_disk_usage` | `path` (optional), `top_n=10` |
| `GET /api/disk/explore` | `explore_directory` | `path` (optional), `pattern`, `search`, `kind`, `recursive`, `max_results` |
| `GET /api/disk/count` | `count_files` | `path` (optional) |
| `GET /api/disk/info` | `file_info` | `path` (optional) |
| `GET /api/agent/models` | — | The selectable models; no MCP or provider key needed |
| `POST /api/agent/analyze` | read-only agent | `{path?, question?}` → `{summary, tool_calls}` |
| `POST /api/cleanup/execute` | `trash_path(confirm=True)` | `{paths: [...]}` — the only mutating route |

`path` is optional on the disk routes: when it is omitted the request is
forwarded without a `path` argument, so the MCP tool applies its own default
(the home directory).

### Health

```jsonc
// GET /health
{ "status": "ok" }

// GET /health/ready  (200)
{ "status": "ok", "mcp": "ok", "tool_count": 12 }

// GET /health/ready  (503 — MCP not connected)
{ "status": "unavailable", "mcp": "unavailable", "detail": "MCP server is not connected" }
```

`/health/ready` returns 503 when the MCP connection is not up, so a
temporarily dead MCP server does not look like a dead backend.

### Disk

The five disk routes are deterministic — they call the MCP tool directly, with
no LLM in the loop. Each returns the tool's structured payload, validated
through a Pydantic response model.

```jsonc
// GET /api/disk/directory?path=/Users/me&top_n=5
{
  "path": "/Users/me",
  "entries": [
    { "name": "Downloads", "type": "directory", "size_bytes": 41234567 },
    { "name": "movie.mov", "type": "file", "size_bytes": 1048576 }
  ]
}
```

### Agent

```jsonc
// GET /api/agent/models
[
  {
    "id": "openai-gpt",
    "label": "OpenAI",
    "provider": "openai",
    "model_name": "gpt-4.1",
    "mode": "cloud"
  },
  {
    "id": "google-gemini",
    "label": "Google Gemini",
    "provider": "google_genai",
    "model_name": "gemini-2.5-flash",
    "mode": "cloud"
  },
  {
    "id": "ollama-llama",
    "label": "Llama 3.1 (Ollama)",
    "provider": "ollama",
    "model_name": "llama3.1",
    "mode": "local"
  }
]

// POST /api/agent/analyze
{ "path": "/Users/me/Downloads", "question": "What is taking the most space?" }

// 200
{
  "summary": "The agent's final answer ...",
  "tool_calls": [
    {
      "name": "directory_disk_usage",
      "args": { "path": "/Users/me/Downloads" },
      "status": "ok",
      "result": { "path": "...", "entries": [...] }
    }
  ]
}
```

`path` and `question` are both optional: without a path the agent starts from
the default location, and without a question it looks for what takes the most
space. A tool that reported an error is recorded with `status: "error"` — the
agent carried on and answered anyway.

### Cleanup

```jsonc
// POST /api/cleanup/execute
{ "paths": ["/Users/me/Downloads/old.zip", "/Users/me/Downloads/tmp"] }

// 200
{
  "mode": "executed",
  "paths": ["/Users/me/Downloads/old.zip", "/Users/me/Downloads/tmp"],
  "deleted": ["/Users/me/Downloads/old.zip", "/Users/me/Downloads/tmp"],
  "failed": [],
  "missing_paths": [],
  "total_valid_paths": 2
}
```

The request body is exactly `{"paths": [...]}` with at least one path. Extra
keys are rejected (`extra="forbid"`), so a client cannot smuggle a `confirm`
flag in.

---

## The read-only agent

`POST /api/agent/analyze` runs a LangChain agent over an **explicit tool
allowlist** — the ten read-only analysis tools plus the MCP server's
`preview_trash` tool (11 entries, `READONLY_TOOL_ALLOWLIST` in
`mcp/manager.py`). The raw `trash_path` tool is never on the list, so the
model cannot delete anything, no matter how the catalogue is built.

- The allowlist is applied in **one** place, `allowlisted_tools()`, on every
  read of the tool map, and a copy is returned so callers cannot mutate the
  boundary.
- The agent is built **per request** from the injected manager, so a missing
  provider key cannot stop the app from booting. A model that cannot be
  constructed turns into a 503 on that request only.
- `STORAGE_BACKEND_AGENT_MAX_ITERATIONS` (default 10) is applied as the
  LangGraph `recursion_limit`. It counts each model call *and* each tool call
  separately, so one round trip through a tool uses two steps. Hitting the cap
  raises `GraphRecursionError`, which the route turns into a 400.
- The model is provider-agnostic: `init_chat_model` with the
  `STORAGE_BACKEND_AGENT_MODEL` string (default `openai:gpt-4.1`) and
  `STORAGE_BACKEND_AGENT_TEMPERATURE` (default `0.0`). Three providers are
  installed and verified by `tests/test_provider_dependencies.py`:
  `openai:*` (`langchain-openai`), `ollama:*` (`langchain-ollama`), and
  `google_genai:*` (`langchain-google-genai`).

---

## Cleanup safety model

1. **Preview** — `preview_trash` reports the candidates and their metadata.
   It never deletes. The agent can call it; a human can too.
2. **Selection** — the frontend owns the selection state and submits only the
   paths the user picked.
3. **Execution** — `POST /api/cleanup/execute {paths: [...]}` is the *only*
   route that may call `trash_path(confirm=True)`. It forwards the submitted
   paths verbatim — no dedup, no re-ordering, no existence pre-check, and no
   extra validation — and relies on the MCP tool's own safeguards.

There is no preview store, no `preview_id`, no fingerprint revalidation, and no
client-supplied `confirm` in v1. `cleanup/preview_store.py` is unused
scaffolding kept for a possible v2.

The MCP tool deduplicates, orders its targets deepest path first, and reports
what it found, so the returned `paths` may differ in order from the submitted
list. A stale path inside a mixed batch is a warning on a 200, not an error;
only an all-missing batch is a 400.

---

## Error mapping

| Condition | Status | Body |
| --------- | ------ | ---- |
| MCP tool returned an error | 400 | `{"detail": {"tool": "trash_path", "message": "Path not found: ..."}}` |
| MCP server unavailable (connection or dependency) | 503 | `{"detail": "MCP server is not available"}` |
| Agent hit its step limit | 400 | `{"detail": "The agent reached its step limit of 10 steps before it could answer."}` |
| Agent model could not be built | 503 | `{"detail": "Agent model is not available: ..."}` |
| Request body invalid | 422 | FastAPI validation error |

---

## Configuration

Settings are read from the environment with the `STORAGE_BACKEND_` prefix and
from an optional `backend/.env` (gitignored; `backend/.env.example` is the
template). Because the `.env` path is relative, the service is expected to be
started from the `backend/` directory.

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `STORAGE_BACKEND_MCP_SERVER_DIR` | `<repo root>/mcp-server` | Project directory of the MCP server. An absolute path avoids depending on the launch directory |
| `STORAGE_BACKEND_MCP_SERVER_COMMAND` | `storage-intelligence` | Console script launched via `uv run --directory <dir>` |
| `STORAGE_BACKEND_MCP_SERVER_ARGS` | `[]` | Extra arguments for the command |
| `STORAGE_BACKEND_MCP_REQUIRED` | `false` | When true, a failed MCP connection aborts startup instead of degrading |
| `STORAGE_BACKEND_AGENT_MODEL` | `openai:gpt-4.1` | Provider-agnostic `init_chat_model` string |
| `STORAGE_BACKEND_AGENT_TEMPERATURE` | `0.0` | Sampling temperature |
| `STORAGE_BACKEND_AGENT_MAX_ITERATIONS` | `10` | Agent step limit (LangGraph `recursion_limit`) |
| `STORAGE_BACKEND_CORS_ORIGINS` | `[]` | JSON array of allowed origins, e.g. `["http://localhost:5173"]` |

Provider API keys are **not** modelled in `Settings`: LangChain reads them from
the environment directly and they never reach the frontend. Use
`OPENAI_API_KEY` for `openai:*`, `GOOGLE_API_KEY` for `google_genai:*`, and
`OLLAMA_BASE_URL` (default `http://localhost:11434`) for `ollama:*`; Ollama
needs no key.

On startup the lifespan opens the MCP connection. If it fails, the app starts
in **degraded mode** (readiness reports it) unless `STORAGE_BACKEND_MCP_REQUIRED`
is set, in which case startup fails.

---

## Getting started

### Prerequisites

- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv)
- A provider API key for the agent (only needed for `/api/agent/analyze`)

### Setup

```bash
cd backend

uv sync                                # install dependencies
cp .env.example .env                   # then edit .env

uv run storage-intelligence-backend    # http://127.0.0.1:8000
```

`make dev` runs the same app under `uvicorn --reload`.

---

## Postman collection

`backend/postman/` holds a git-native v3 collection **Storage Intelligence
Backend** with folders for Health, Disk, Agent, and Cleanup, the environment
**Storage Intelligence - Local**, and the workspace globals. `backend/.postman/resources.yaml`
binds the folder to a Postman workspace.

---

## Quality checks

Run from this directory:

```bash
uv run ruff check --fix
uv run ruff format
uv run pyright
uv run pytest
uv build
```

58 tests cover the health routes, the disk routes, the agent endpoints (model
catalogue and analysis) and the tool boundary, the storage agent, and the
cleanup execution path. The suite
runs with `asyncio_mode = "auto"` and carries an `integration` marker for
tests that spawn the real MCP server over stdio.

The same checks run in CI for this package (see
[`../.github/workflows/ci.yml`](../.github/workflows/ci.yml)).

---

## Further reading

- [`BACKEND_HANDOFF.md`](../BACKEND_HANDOFF.md) — the backend design
  decisions and the roadmap behind them.
- [`../mcp-server/README.md`](../mcp-server/README.md) — the MCP tools this
  service calls.
