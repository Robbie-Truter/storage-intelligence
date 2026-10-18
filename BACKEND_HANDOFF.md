# Backend Handoff

Context for the next workstream: building `backend/`. No code here — background and direction only.

## What we did

- Converted the repo into a monorepo. Command runner / git root: `storage-intelligence/`.
- Moved the existing Python MCP project into `mcp-server/` as a self-contained `uv` project (its own `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, `tests/`, `.venv`, `Makefile`, `README.md`).
- Left the package name and all imports unchanged (`storage_intelligence`); this was a pure move, not a rename.
- Added placeholder `backend/` and `frontend/` directories.
- Kept shared tooling at the root: `.opencode/` (agents, commands, skills), `.github/workflows/ci.yml`, `AGENTS.md`, root `README.md`.
- Added root-level editor config: `pyrightconfig.json` (points Pyright/Pylance at `mcp-server/.venv` and `mcp-server/src`) and `.vscode/settings.json` (interpreter → `mcp-server/.venv/bin/python`).
- Verified `mcp-server/` from inside it: ruff, ruff format, pyright, 119 pytest tests, `uv build`, and server import all pass.

## Why we did it

- Separate the MCP server, backend, and frontend into independent projects under one repo.
- Keep each package's dependencies, virtualenv, and tool config isolated (no shared venv).
- Give shared agent guidance and CI a single home at the root.

## Git branching strategy

- `main` is the stable branch. Do not merge into it until both backend and frontend are complete, integrated,
  and verified, and the user explicitly approves the merge.
- `refactor/monorepo` is the integration branch for the current monorepo development.
- `feature/backend` is created from `refactor/monorepo`. Backend work is developed and verified there, then
  merged back into `refactor/monorepo` through a pull request.
- `feature/frontend` is created from the updated `refactor/monorepo` when frontend development begins.
  Frontend work is merged back through a pull request.
- Feature branches may be committed to, pushed, and reviewed independently.
- Never merge into `main` or initiate a PR targeting `main` without explicit user approval.

## Key constraint learned

The current tooling is scoped to `mcp-server/`. Root `pyrightconfig.json` and `.vscode/settings.json` point only at that package, and ruff config lives in `mcp-server/pyproject.toml`. A new package does **not** inherit this — it needs its own setup (see below).

## Next steps: backend (FastAPI + LangChain)

Goal: a `backend/` service (FastAPI) that uses LangChain to talk to the `mcp-server` over MCP, likely exposing HTTP endpoints and/or streaming to the `frontend/`.

- Scaffold `backend/` as its own `uv` project: `pyproject.toml`, `uv.lock`, `.python-version`, `.venv`, `src/`, `tests/`, `README.md`.
- Add tool config in `backend/pyproject.toml`: `[tool.ruff]`, `[tool.pyright]`, pytest settings.
- Keep root `pyrightconfig.json` unchanged (it points at `mcp-server/.venv`) and add a separate `backend/pyrightconfig.json` (points at `backend/.venv`). Pyright's virtual-environment selection is global rather than per execution environment, so one root config cannot correctly serve two venvs.
- Extend `.github/workflows/ci.yml` to run the same lint/format/type/test steps per package (e.g. a matrix over `[mcp-server, backend]`), since the current job hard-codes `working-directory: mcp-server`.
- Decide how the backend reaches the MCP server: launch it as a subprocess over stdio, or connect to a running/SSE instance. Note the local launch form is `uv run --directory mcp-server storage-intelligence`.
- Wire in FastAPI app + LangChain + an MCP client, with tests (FastAPI `TestClient`/`httpx`, async test mode).
- Later: define the contract the `frontend/` consumes.

## Backend decisions (confirmed)

- **Integration:** use `langchain[mcp]` → `MCPAdapter` (built on FastMCP 4.x / `mcp` 2.x), not the standalone
  `langchain-mcp-adapters`. Chosen because it matches the server's FastMCP stack; it is **beta**, so it must be
  wrapped behind a thin interface.
- **Model:** provider-agnostic `init_chat_model` string from env (default `openai:gpt-4.1`). Provider API keys
  live on the backend only and are never exposed to the React frontend.
- **Deterministic vs agent:** normal disk usage / scan endpoints call MCP directly (no LLM). Agent endpoints
  use an LLM over an **explicit allowlist** of read-only tools only — all 10 read-only tools (everything except
  `trash_path`), not annotations alone.
- **Destructive safety:** keep `trash_path` in the MCP server and reuse its existing dry-run/execution logic.
  The agent may use allowlisted read-only tools; the backend may call `trash_path` with `confirm=False` to
  build a preview. `confirm=True` is **never** exposed to the agent and is only issued server-side after
  explicit frontend user confirmation, bound to the exact reviewed paths and revalidated before execution.
  Do not duplicate deletion logic in FastAPI.

## Verified package versions & API facts

Checked against PyPI / installed packages (2026):

- `langchain` 1.4.4 — `langchain[mcp]>=1.4.0` pulls `langchain-core` 1.6.9, `langgraph` 1.2.x,
  `fastmcp>=4.0.11`, `mcp` 2.x.
- `langchain.mcp.MCPAdapter` is a beta replacement for `langchain-mcp-adapters` (0.3.2 pins `mcp<2.0.0`).
- `fastapi` 0.143.0, `uvicorn` 0.54.0; lifespan is the supported startup/shutdown hook.
- Server stack: `fastmcp` 4.0.3, `mcp` 2.2.0, Python 3.13 — same major as the backend, so protocol era
  negotiation should align.
- `fastmcp.Client(transport)` is a **reentrant** async context manager with `keep_alive=True`, so one
  subprocess can back many calls.
- `UvStdioTransport(command, args, project_directory=Path("mcp-server"))` launches
  `uv run ... storage-intelligence`.
- `client.call_tool_mcp(name, args)` returns the raw `CallToolResult` (`isError`, `structuredContent`)
  **without raising** — ideal for deterministic endpoints.
- `MCPAdapter` accepts a prebuilt `fastmcp.Client` "for full control over transport", and `list_tools()`
  returns reentrant LangChain tools that reuse an already-open connection.

## Proposed backend layout

```
backend/
├── pyproject.toml            # uv project, ruff/pyright/pytest config (mirrors mcp-server)
├── pyrightconfig.json        # backend-only; points at backend/.venv
├── uv.lock
├── .python-version           # 3.13
├── .env.example              # documented; real .env gitignored
├── README.md
├── src/storage_intelligence_backend/
│   ├── main.py               # create_app() + lifespan, mounts routers
│   ├── config.py             # pydantic-settings Settings
│   ├── deps.py               # FastAPI dependencies (get_mcp_manager)
│   ├── schemas.py            # Pydantic request/response models
│   ├── mcp/
│   │   ├── manager.py        # StorageMCPClient: owns Client + MCPAdapter + allowlisted tool map
│   │   └── errors.py         # MCPUnavailable, MCPToolError
│   ├── agents/
│   │   └── storage_agent.py  # build_agent(model, tools) + run_readonly_analysis(...)
│   ├── cleanup/
│   │   └── preview_store.py  # in-memory, path-bound preview/confirmation records
│   └── routers/
│       ├── health.py
│       ├── disk.py           # deterministic; no LLM
│       ├── agent.py          # LLM-driven; read-only tools
│       └── cleanup.py        # preview + confirmed execute
└── tests/
    ├── conftest.py               # shared ``client`` fixture (no lifespan)
    ├── test_health.py
    ├── test_disk.py              # mocked MCP manager
    ├── test_agent.py             # fake chat model, no creds
    ├── test_cleanup_safety.py    # preview binding, confirmation gate
    └── test_mcp_integration.py   # real subprocess, marked `integration`
```

## MCP lifecycle (FastAPI lifespan)

- Build one `fastmcp.Client(UvStdioTransport(...))` and enter it inside the app `lifespan`; wrap it with
  `MCPAdapter` and call `list_tools()` once. Hold everything on `AsyncExitStack` for graceful shutdown
  (adapter → client → subprocess). No process per tool call.
- Store the client, the full tool map, and an **explicit allowlist** of agent-exposed tools on `app.state`.
  Gate the agent on that allowlist (a hardcoded set of approved read-only tool names — all 10 read-only tools),
  not on MCP annotations: annotations describe behaviour, they are not a security boundary. `trash_path` stays
  off the allowlist even though it supports a safe preview mode.
- Startup failure: catch and log, leave `app.state.mcp = None`; an `mcp_required` setting can opt into
  failing startup instead. Health endpoints report `ok`/`unavailable`.
- Disconnection: wrap calls; on connection errors attempt one reconnect, else raise `MCPUnavailable` → 503.
- Endpoints receive the manager through a FastAPI dependency.

## Endpoints

Complete set of routes the backend needs to reach every MCP tool. The MCP server
exposes 11 tools: 10 read-only (one deterministic route each) plus `trash_path`
(cleanup). `scan` is a backend-side fan-out, not an MCP tool.

### Health (no MCP dependency)

- `GET /health` — **liveness**: is the FastAPI process up? Always cheap.
- `GET /health/ready` — **readiness**: can the service fulfil requests that need MCP? Reports MCP status and
  tool count, and returns 503 when the MCP subprocess is unavailable. Keeps a temporarily dead MCP from
  looking like a dead backend.

### Deterministic disk reads (no LLM) — one route per read-only tool

Every route takes an optional `path` (the MCP tool's own default, the home directory, applies when omitted);
the other query parameters mirror the tool signature. Backed by `client.call_tool(...)`; map `isError` to an
HTTP error carrying the MCP message.

| Route | MCP tool | Parameters (beyond `path`) |
|---|---|---|
| `GET /api/disk/usage` | `disk_usage` | — |
| `GET /api/disk/directory` | `directory_disk_usage` | `top_n` (default 10) |
| `GET /api/disk/explore` | `explore_directory` | `pattern`, `search`, `kind`, `recursive`, `max_results` |
| `GET /api/disk/count` | `count_files` | — |
| `GET /api/disk/info` | `file_info` | — |
| `GET /api/disk/large-files` | `find_large_files` | `min_size_mb`, `max_results` |
| `GET /api/disk/duplicates` | `find_duplicate_files` | `min_size_bytes` |
| `GET /api/disk/stale` | `find_stale_files` | `days_unmodified`, `max_results` |
| `GET /api/disk/empty-directories` | `find_empty_directories` | `recursive` |
| `GET /api/disk/junk` | `find_junk_files` | — |

### Combined scan (no LLM)

- `GET /api/disk/scan` — dashboard fan-out: calls several read-only tools in one request and returns an
  aggregate (planned: `disk_usage` + `directory_disk_usage` + `find_large_files` + `find_duplicate_files` +
  `find_junk_files` + `find_empty_directories` + `find_stale_files`). Composed by the backend, not an MCP tool.

### Agent (LLM)

- `POST /api/agent/analyze` `{path, question?}` → runs the agent over an **explicit allowlist of all 10
  read-only tools** (everything except `trash_path`); returns `{summary, tool_calls}`.

### Cleanup (mutating)

- `POST /api/cleanup/preview` then `POST /api/cleanup/execute` → MCP `trash_path` (see below).

## Cleanup safety model

- `POST /api/cleanup/preview` `{path | paths}` → MCP `trash_path(confirm=False)`. Store a record keyed by a
  UUID: `{preview_id, reviewed_targets, created_at, expires_at, status}` using the **normalized `paths` the
  MCP preview returned** (deduped, deepest-first, existing) — not the raw request. Capture a fingerprint per
  target where practical: device + inode, target type (file vs directory), size, and mtime.
- `POST /api/cleanup/execute` `{preview_id, confirm: true}`:
  1. look up the record; reject unknown/expired/consumed;
  2. **revalidate** every stored target: it must still exist, and its identity/metadata must still match the
     fingerprint captured at preview time. If anything changed (replaced, resized, retyped, repointed), reject
     execution and require a fresh preview;
  3. call MCP `trash_path(paths=approved_paths, confirm=True)`;
  4. mark the record consumed.
- Existence alone is not enough: a path that still exists may now be a different file. Keep `send2trash`
  behaviour unchanged and never fall back to permanent deletion.
- **Residual race (TOCTOU):** fingerprint revalidation detects targets that changed between preview and
  execution, but it does not completely eliminate time-of-check/time-of-use filesystem races — a target could
  still change after revalidation and before `send2trash` runs. Fingerprints are a detection mechanism, not a
  guarantee. Keep confirmation server-controlled, reject changed targets, never fall back to permanent
  deletion, and test these failure cases explicitly. Do not claim metadata fingerprints guarantee protection
  against all filesystem races.
- The execute endpoint takes **only** a `preview_id` (+ explicit `confirm`), never paths — an LLM/client cannot
  smuggle deletion targets. `confirm=True` is constructed server-side from the user-reviewed set.
- In-memory store is single-process only; note it and move to a DB before multi-worker deployment.

## Config (backend-only)

`pydantic-settings` with an env prefix (e.g. `STORAGE_BACKEND_`): `mcp_server_dir`, `mcp_server_command`,
`mcp_server_args`, `mcp_required`, `agent_model`, `agent_temperature`, `agent_max_iterations`, `cors_origins`.
`langchain-openai` is the default provider; add `langchain-anthropic` / `langchain-ollama` as needed. `.env`
loaded automatically; `.env.example` committed and `.env` gitignored.

## Testing strategy

- Unit tests inject a fake MCP manager via `dependency_overrides[get_mcp_manager]`. The fake records
  `call_tool(name, args)` calls and returns canned structured content or raises `MCPToolError` /
  `MCPUnavailable`. The shared `client` fixture uses `fastapi.testclient.TestClient` without entering the
  lifespan, so no subprocess is spawned. Cover `/health` (liveness) and `/health/ready` (readiness, 503 when
  MCP is down) separately.
- Agent tests inject a fake chat model (e.g. `GenericFakeChatModel`) — no live LLM credentials required.
- Integration tests spawn the real server over stdio, marked `integration`; assert `disk_usage` /
  `explore_directory` structured output and that `trash_path(confirm=False)` previews (never execute real
  paths).
- Safety tests assert the agent tool map is limited to the explicit allowlist (no `trash_path`), that
  agent-driven requests cannot reach `confirm=True`, and that execute rejects unknown/expired previews and
  targets whose identity/metadata no longer match the preview fingerprint.

## CI & root tooling

- Convert `.github/workflows/ci.yml` to a matrix over `[mcp-server, backend]`, `working-directory:
${{ matrix.package }}`, `cache-dependency-glob: ${{ matrix.package }}/uv.lock`; backend also runs an import
  smoke test. Run each project's type checker from its own directory against its own venv.
- Keep root `pyrightconfig.json` unchanged; add `backend/pyrightconfig.json` pointing at `backend/.venv` and
  `backend/src`. Pyright's venv selection is global, so a single root config cannot serve both packages.
  `.vscode/settings.json` keeps the mcp-server interpreter as default (single-interpreter limitation).
- Add `.env` to root `.gitignore`.

## Implementation order

Status key: `[x]` done · `[~]` in progress · `[ ]` not started. Update this list as tasks finish. One row per
route; deterministic routes reuse the step-4 dependency and error mapping.

1. [x] Scaffold `backend/` as an independent `uv` project with dependencies, configuration, and test setup.
       (Pyright config lives in `backend/pyproject.toml` `[tool.pyright]` instead of a separate `pyrightconfig.json`.)
2. [x] Add backend linting, formatting, type-checking, and test commands. CI runs a `[mcp-server, backend]` matrix.
3. [x] Implement the MCP manager, FastAPI lifespan, `GET /health`, and `GET /health/ready`.
4. [x] Implement `GET /api/disk/usage` → `disk_usage` and verify the real MCP subprocess connection
       end-to-end (verified via `uvicorn` + `curl`: default path, explicit `path`, and bad-path → 400).
       Endpoint unit tests added in `backend/tests/test_disk.py` (fake manager: payload, path pass-through,
       tool error → 400, MCP down → 503).
5. [ ] Remaining deterministic disk routes (no LLM), one per read-only tool:
   - [x] `GET /api/disk/directory` → `directory_disk_usage` (handler named after the tool; unit tests in
         `backend/tests/test_disk.py`: payload, default `top_n`, path/`top_n` pass-through).
   - [x] `GET /api/disk/explore` → `explore_directory` (handler named after the tool; unit tests in
         `backend/tests/test_disk.py`: payload, default filters, path + `pattern`/`search`/`kind`/`recursive`/`max_results` pass-through).
   - [x] `GET /api/disk/count` → `count_files` (handler named after the tool; unit tests in
         `backend/tests/test_disk.py`: payload, no-path default, path pass-through).
   - [ ] `GET /api/disk/info` → `file_info`
   - [ ] `GET /api/disk/large-files` → `find_large_files`
   - [ ] `GET /api/disk/duplicates` → `find_duplicate_files`
   - [ ] `GET /api/disk/stale` → `find_stale_files`
   - [ ] `GET /api/disk/empty-directories` → `find_empty_directories`
   - [ ] `GET /api/disk/junk` → `find_junk_files`
6. [ ] `GET /api/disk/scan` — combined fan-out aggregate of the read-only tools.
7. [ ] Implement the read-only LangChain agent over the allowlist of all 10 read-only tools and
       `POST /api/agent/analyze`, with fake-model tests.
8. [ ] Implement cleanup preview and confirmed execution (`trash_path`) with path-bound confirmation, fingerprint
       revalidation, and safety tests.
9. [ ] Complete CI, documentation, and final package-level verification
       (`uv run ruff check --fix && uv run ruff format && uv run pyright && uv run pytest`, per package).

## Risks to verify during implementation

- `langchain.mcp` is beta (`LangChainBetaWarning`, API may change) and `MCPAdapter` sharing a prebuilt
  `fastmcp.Client` needs a spike; if the client is not reused, fall back to the raw `Client` for deterministic
  calls plus `langchain.mcp.as_langchain_tool` for the agent catalog. The `mcp/manager.py` wrapper isolates
  this either way.
- fastmcp era negotiation: backend `fastmcp>=4.0.11` vs server `4.0.3`; the step-4 integration test is the
  early compatibility check.
- Client-supplied paths are currently trusted (local-first tool); call out future allowlisting. Out of scope.

## References

- Monorepo changes and rationale: `MONOREPO_MIGRATION_PLAN.md`.
- Repo-wide rules and verification commands: `AGENTS.md`.
- Shared skills: `.opencode/skills/` (`python-quality`, `fastmcp-tool-dev`, `safe-cleanup-testing`).
- MCP server details: `mcp-server/README.md`.
