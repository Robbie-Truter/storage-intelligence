# Storage Intelligence

**Storage Intelligence** is a local-first monorepo for storage analysis, disk
usage profiling, duplicate and junk detection, and safe cleanup workflows.

It is made of two Python packages and a planned React frontend that has not been
scaffolded yet:

- **`mcp-server/`** — a [FastMCP](https://gofastmcp.com) server exposing
  structured tools, a resource, and prompts for local storage analysis and
  safe cleanup.
- **`backend/`** — a FastAPI + LangChain service that talks to the MCP server
  over MCP and exposes an HTTP API, including an optional read-only LLM agent.
- **`frontend/`** — the planned React + Vite dashboard: storage overview,
  read-only AI assistant, settings, and a shared cleanup review. The build
  contract is [`frontend/FRONTEND_HANDOFF.md`](frontend/FRONTEND_HANDOFF.md);
  the work is tracked in [`frontend-todo.md`](frontend-todo.md).

> **Documentation map.** This README is the **project overview**: architecture,
> the HTTP API, CI, and the shared workflow. Each package carries its own
> README with the detailed reference —
> [`mcp-server/README.md`](mcp-server/README.md) (every tool, prompt, and
> result shape) and [`backend/README.md`](backend/README.md) (every endpoint,
> setting, and test suite). The frontend uses
> [`frontend/FRONTEND_HANDOFF.md`](frontend/FRONTEND_HANDOFF.md) as its approved
> build snapshot and [`frontend-todo.md`](frontend-todo.md) as its ordered
> checklist; a durable `frontend/README.md` is added in the final frontend
> phase. The other tracked documents are
> [`AGENTS.md`](AGENTS.md) (repo-wide rules for coding agents) and
> [`BACKEND_HANDOFF.md`](BACKEND_HANDOFF.md) (backend design decisions and
> roadmap).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                Frontend — React + Vite (planned)                 │
│           Home · Assistant · Settings · Cleanup review           │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTP / JSON
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│        Backend — FastAPI + LangChain  (backend/)                 │
│                                                                  │
│   routers/     health · disk · agent · cleanup                   │
│   mcp/         StorageMCPClient: one stdio subprocess + adapter  │
│   agents/      read-only analysis agent (LangChain)              │
└───────────────────────────────┬──────────────────────────────────┘
                                │ MCP over stdio
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│      MCP Server — FastMCP  (mcp-server/)                         │
│                                                                  │
│   12 tools · 1 resource · 9 prompts                             │
└───────────────────────────────┬──────────────────────────────────┘
                                │ local file I/O
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Local File System                         │
└──────────────────────────────────────────────────────────────────┘
```

The backend owns a **single** MCP subprocess for its whole lifetime: the
deterministic REST routes and the agent's LangChain tools share that one
connection.

---

## Repository Layout

```
storage-intelligence/
├── mcp-server/            # FastMCP server (own pyproject, uv.lock, .venv)
│   ├── README.md          # tool, prompt, and result reference
│   ├── src/storage_intelligence_mcp/
│   │   ├── core.py        # FastMCP instance
│   │   ├── server.py      # entry point; registers tools/resources/prompts
│   │   ├── utils.py       # formatting, hashing, OS traversal helpers
│   │   ├── tools/         # storage.py (analysis) · cleanup.py (trash)
│   │   ├── resources/     # info://server
│   │   └── prompts/       # ready-made analysis / cleanup workflows
│   └── tests/
├── backend/               # FastAPI + LangChain service (own pyproject, uv.lock, .venv)
│   ├── README.md          # endpoint, configuration, and test reference
│   ├── src/storage_intelligence_backend/
│   │   ├── main.py        # create_app() + lifespan, mounts routers
│   │   ├── config.py      # pydantic-settings (STORAGE_BACKEND_ prefix)
│   │   ├── schemas.py     # Pydantic request/response models
│   │   ├── deps.py        # dependency provider for the MCP manager
│   │   ├── mcp/           # manager.py (client + adapter + allowlist), errors.py
│   │   ├── agents/        # storage_agent.py (build_agent, run_readonly_analysis)
│   │   ├── cleanup/       # preview_store.py (unused scaffolding in v1)
│   │   └── routers/       # health.py · disk.py · agent.py · cleanup.py
│   ├── postman/           # Postman collection, environment, and specs
│   └── tests/
├── frontend/              # React + Vite dashboard (planned; not scaffolded yet)
│   ├── FRONTEND_HANDOFF.md  # approved frontend build snapshot
│   └── README.md          # durable setup/run docs (added in the final phase)
├── frontend-todo.md       # ordered frontend implementation checklist
├── .opencode/             # opencode agents, commands, and skills
├── .github/workflows/     # CI (mcp-server + backend matrix; frontend job pending)
├── AGENTS.md              # repo-wide rules for coding agents
└── BACKEND_HANDOFF.md     # backend design decisions and roadmap
```

Each Python package is a self-contained [`uv`](https://github.com/astral-sh/uv)
project with its own `pyproject.toml`, `uv.lock`, `.venv`, and tool config.
**Run every command from the package directory you are working in** — tooling is
not inherited across packages.

---

## MCP Server (`mcp-server/`)

FastMCP server for local storage analysis and safe cleanup. It runs locally
over stdio and never sends file paths or metadata off the machine.

### Tools (12)

Ten read-only analysis tools, one preview tool, and one mutating tool:

| Tool | Purpose |
| ---- | ------- |
| `disk_usage` | Space used / free on the volume containing a path |
| `directory_disk_usage` | Immediate children of a directory ranked by size |
| `explore_directory` | Structured listing of a directory (filter, recurse, cap) |
| `count_files` | File count for a directory, grouped by extension |
| `file_info` | Metadata for a single file or directory |
| `find_large_files` | Largest files under a path |
| `find_duplicate_files` | Files sharing the same content hash |
| `find_stale_files` | Files not modified for a given number of days |
| `find_empty_directories` | Directories with no entries |
| `find_junk_files` | Known junk by category (caches, build artifacts, …) |
| `preview_trash` | **Read-only.** Reports what *would* be trashed — no deletion |
| `trash_path` | **Mutating.** Sends paths to the system trash |

`preview_trash` and `trash_path` accept either a single `path` or a list of
`paths`; the two are combined and deduplicated. Targets are ordered deepest
path first so nested reporting stays accurate.

### Resource and prompts

- Resource `info://server` — server metadata.
- Nine prompts: `analyze_storage`, `analyze_home_storage`, `find_old_files`,
  `find_duplicates`, `clean_junk`, `free_up_space`, `prepare_cleanup`,
  `remove_junk`, `remove_empty_dirs`.

### Safety

- Every tool defaults to **dry-run** (`confirm=False`) where it acts.
- Deletion goes through **`send2trash`** (system trash / Recycle Bin).
  Permanent unlinking (`os.remove`, `shutil.rmtree`) is never used.
- Paths are deduplicated and processed deepest-first.
- The MCP server never uses elicitation, sampling, or roots.

### Run it

```bash
cd mcp-server
uv sync
uv run storage-intelligence      # stdio transport
```

---

## Backend (`backend/`)

FastAPI service that speaks MCP to the server above and exposes HTTP for the
frontend. The client supplies the provider API key with each agent request; the
backend uses it for that request and never stores it.

### Endpoints

| Method & route | MCP tool / behaviour | Notes |
| -------------- | -------------------- | ----- |
| `GET /health` | — | Liveness. Cheap, no MCP dependency |
| `GET /health/ready` | — | Readiness. 503 when MCP is down; reports `tool_count` |
| `GET /api/disk/usage` | `disk_usage` | `path` (defaults to the MCP tool default) |
| `GET /api/disk/directory` | `directory_disk_usage` | `path`, `top_n` (default 10) |
| `GET /api/disk/explore` | `explore_directory` | `path`, `pattern`, `search`, `kind`, `recursive`, `max_results` |
| `GET /api/disk/count` | `count_files` | `path` |
| `GET /api/disk/info` | `file_info` | `path` |
| `POST /api/agent/analyze` | read-only agent | `{model, api_key?, path?, question?}` → `{summary, tool_calls}` |
| `POST /api/cleanup/execute` | `trash_path(confirm=True)` | `{paths: [...]}` — the only mutating route |

Interactive API docs are served at `http://127.0.0.1:8000/docs`.

Error mapping: an MCP tool error becomes **400** with the MCP message, an
unavailable MCP server becomes **503**, an agent that hits its step cap becomes
**400**, and an unknown model or a cloud model without an `api_key` becomes
**422**.

### Read-only agent

`POST /api/agent/analyze` runs a LangChain agent over an **explicit tool
allowlist** — the ten read-only analysis tools plus the MCP `preview_trash`
tool. `trash_path` is not on the list, so the model cannot delete anything, no
matter how the catalogue is built. The allowlist lives in one place
(`mcp/manager.py`) and is applied on every read of the tool map.

The agent is built **per request** from the injected manager, so a missing or
invalid provider key only fails that request. Cloud models require the client
to send `api_key`; Ollama does not. Each `tool_calls` entry carries
`{name, args, status, result}`.

### Cleanup safety model

1. **Preview** — `preview_trash` reports the candidates and their metadata.
   It never deletes.
2. **Selection** — the frontend owns the selection state and submits only the
   paths the user picked.
3. **Execution** — `POST /api/cleanup/execute {paths: [...]}` is the *only*
   route that may call `trash_path(confirm=True)`. It forwards the submitted
   paths verbatim — no dedup, no re-ordering, no extra validation — and relies
   on the MCP tool's existing safeguards. A stale path in a mixed batch is
   reported in `missing_paths`; a batch where every path is missing is a
   **400**.

There is no preview store, no `preview_id`, and no approval infrastructure in
v1.

### Configuration

Settings are read from the environment with the `STORAGE_BACKEND_` prefix and
from an optional `backend/.env` (gitignored; `backend/.env.example` is the
template).

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `STORAGE_BACKEND_MCP_SERVER_DIR` | `<repo root>/mcp-server` | Directory of the MCP server project |
| `STORAGE_BACKEND_MCP_SERVER_COMMAND` | `storage-intelligence` | Console script launched over stdio |
| `STORAGE_BACKEND_MCP_SERVER_ARGS` | `[]` | Extra arguments for the server |
| `STORAGE_BACKEND_MCP_REQUIRED` | `false` | Fail startup when MCP is unreachable (otherwise degraded mode) |
| `STORAGE_BACKEND_AGENT_TEMPERATURE` | `0.0` | Sampling temperature |
| `STORAGE_BACKEND_AGENT_MAX_ITERATIONS` | `10` | Agent step cap (a cap hit is a 400) |
| `STORAGE_BACKEND_CORS_ORIGINS` | `[]` | Allowed origins for the frontend |

The model is picked per request from `GET /api/agent/models`; provider keys are
sent by the client in the analyze body and are not backend settings.

### Run it

```bash
cd backend
uv sync
cp .env.example .env        # optional local overrides
uv run storage-intelligence-backend    # http://127.0.0.1:8000
```

---

## Frontend (`frontend/`)

The frontend is a planned React dashboard; the app has not been scaffolded yet.
[`frontend/FRONTEND_HANDOFF.md`](frontend/FRONTEND_HANDOFF.md) is the approved
build snapshot, and [`frontend-todo.md`](frontend-todo.md) is the ordered
implementation checklist.

### Stack

React + Vite + TypeScript (strict), Tailwind CSS v4 via `@tailwindcss/vite`,
shadcn/ui (New York style, CSS variables), React Router, TanStack Query, Axios,
Framer Motion, and lucide-react. Biome handles linting and formatting; npm is
the package manager.

### Routes

| Route | Page | Purpose |
| ----- | ---- | ------- |
| `/` | Home | Read-only disk overview: readiness, path context, volume usage, largest immediate children, extension counts, and selected-entry metadata |
| `/assistant` | AI Assistant | One-shot analysis over the read-only agent, with a complete tool-call timeline |
| `/settings` | Settings | Theme, model selection, in-memory provider keys, and privacy copy |
| `*` | Not Found | Fallback page |

Cleanup is a shared review dialog reachable from Home and the Assistant, not a
route. It is the only mutating UI path and submits exactly `{ paths }` to
`POST /api/cleanup/execute`.

### Structure

```text
frontend/src/
├── lib/api/          # Axios clients, error mapping, types, query keys
├── lib/format.ts     # bytes, percent, Unix timestamps, counts
├── components/       # ui (shadcn), layout, and common states
├── providers/        # QueryClient, theme, and in-memory settings
├── features/         # health, disk, assistant, cleanup, settings
└── pages/            # Home, Assistant, Settings, and NotFound
```

Frontend tooling is configured in `frontend/biome.json`; `biome check` covers
linting and formatting.

Feature folders own their API calls, hooks, query keys, and components;
presentational components do not call Axios directly.

### Configuration and safety

- `VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`.
- The backend must allow the Vite origin, normally
  `http://localhost:5173`, via `STORAGE_BACKEND_CORS_ORIGINS` (or a dev proxy).
- Provider API keys live in React memory only; they are never written to
  storage, URLs, logs, or error messages.
- Model output is rendered as plain text; there is no
  `dangerouslySetInnerHTML`.
- Cleanup never runs automatically and requires an explicit acknowledgement
  before moving exact paths to the system trash.

### Run it

Once the scaffold lands:

```bash
cd frontend
npm install
cp .env.example .env.local   # optional; the default backend URL works
npm run dev                  # http://localhost:5173
```

---

## Getting Started

```bash
git clone https://github.com/Robbie-Truter/storage-intelligence.git
cd storage-intelligence

# MCP server
cd mcp-server && uv sync && uv run storage-intelligence

# Backend (separate shell)
cd backend && uv sync && cp .env.example .env && uv run storage-intelligence-backend

# Frontend (separate shell; after the initial scaffold lands)
cd frontend && npm install && npm run dev
```

---

## Quality Checks

Every package carries its own tooling; run the checks **from the package
directory**.

### Python packages

```bash
uv run ruff check --fix
uv run ruff format
uv run pyright --project pyproject.toml
uv run pytest
```

Shared conventions: Ruff (`py313` target, 88 columns), Pyright in `basic` mode
configured in each package's `pyproject.toml`, and Pytest.

### Frontend

```bash
npm run check
npm run typecheck
npm run build
```

The frontend uses Biome (`biome check`) for linting and formatting, an effective
`tsc` check, and a Vite production build. Typecheck must actually cover `src`;
if the solution-style `tsconfig` makes `tsc --noEmit` a no-op, use `tsc -b`.
Component/unit tests are deferred in v1.

---

## CI

`.github/workflows/ci.yml` runs a `[mcp-server, backend]` matrix. For each
package it syncs dependencies, then runs Ruff lint, Ruff format check,
Pyright, Pytest, `uv build`, and a package-specific import smoke test.

Triggers: pushes and pull requests targeting `master`,
`refactor/monorepo-structure`, or `refactor/monorepo`.

There is no frontend CI job yet. Run the frontend checks locally until one is
added.

---

## Branching

```text
master
└── refactor/monorepo-structure     # integration branch for the monorepo work
    ├── feature/backend
    └── feature/frontend
```

Feature branches are created from the integration branch and merged back
through a pull request. `master` is the stable branch and is not merged into
until the backend and frontend are complete, integrated, and verified — with
explicit user approval. See [`AGENTS.md`](AGENTS.md) for the full policy.

---

## Postman Workspace

`backend/postman/` holds a Postman collection for the backend API, a local
environment, and API specs, for exploring and testing the endpoints without
the frontend.

---

## Roadmap

- Frontend dashboard (up next): storage overview, read-only AI assistant,
  settings, and a shared cleanup review flow with user-owned selection.
- Frontend CI job covering Biome check, typecheck, and build.
- Background indexing and caching for instant duplicate and large-file queries.
- Stronger cleanup hardening (protected system paths, backup-before-delete).
- Containerized deployment for local NAS and home-server setups.
