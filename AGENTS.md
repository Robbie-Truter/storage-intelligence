# Storage Intelligence - Agent Guidelines & Rules

## Repository Layout

This repository is a monorepo. The root holds:

- `mcp-server/` — the Python FastMCP server (its own `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, and `tests/`).
- `backend/` — application backend (FastAPI + LangChain; its own `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, and `tests/`).
- `frontend/` — planned React + Vite frontend (TypeScript strict, Tailwind v4, shadcn/ui, React Router, TanStack Query, Axios, Framer Motion, Biome); not scaffolded yet. The approved build snapshot is `frontend/FRONTEND_HANDOFF.md` and the ordered implementation checklist is `frontend/frontend-todo.md`.
- `.opencode/` — opencode configuration (backend and frontend subagents, slash commands, skills), and `.github/` — shared CI workflows.

All Python commands below run from the package directory you are working in (`mcp-server/` or `backend/`). Each Python package is a self-contained `uv` project with its own `.venv` and tool config — do not run one package's commands from another's directory. Frontend commands run from `frontend/` and use npm.

The root `README.md` is the project overview. Each package documents itself in its own README
(`mcp-server/README.md`, `backend/README.md`, and `frontend/README.md` once the frontend app exists) — the
package READMEs are the detailed reference, the root README is the shared context, and the two never duplicate
the same content. `AGENTS.md` (this file) holds the repo-wide rules; `BACKEND_HANDOFF.md` holds the backend
design decisions and roadmap. For the frontend, `frontend/FRONTEND_HANDOFF.md` is the approved build snapshot
and `frontend/frontend-todo.md` is the ordered implementation checklist.

## Git branching and merge policy

Intended workflow:

```text
master
└── refactor/monorepo-structure
    ├── feature/backend
    └── feature/frontend
```

This diagram represents the intended workflow, not permanent Git ancestry. Each feature branch is created from
the latest integration branch and merged back through a pull request.

- The stable branch is `master` (the repository default). There is no `main` branch — do not create or target one.
- Use `refactor/monorepo-structure` as the integration branch during the current monorepo development phase.
- Create `feature/backend` from `refactor/monorepo-structure` for backend work.
- Create `feature/frontend` from the updated `refactor/monorepo-structure` for frontend work.
- The backend API contract is authoritative for frontend work; do not add MSW or invent endpoints, params, or response fields.
- Target `refactor/monorepo-structure` for feature pull requests.
- Do not merge into `master` until backend and frontend are complete, integrated, and verified, and the user
  explicitly approves the merge.
- Never merge into `master` or initiate a PR targeting `master` without explicit user approval.
- Feature-branch commits and pushes are permitted. Do not rewrite shared branch history or force-push without
  explicit authorization.
- Check `git status` and the current branch before switching branches or making changes. Preserve uncommitted
  user work.
- Prefer one branch per major workstream rather than a separate branch for every small task.
- Pull requests should run relevant CI checks.
- After the monorepo work is complete, return to the normal workflow of creating feature branches from `master`,
  unless the user specifies otherwise.

## CI

`.github/workflows/ci.yml` runs a `[mcp-server, backend]` matrix. Per package it syncs dependencies, then runs
`ruff check`, `ruff format --check`, `pyright`, `pytest`, `uv build`, and a package-specific import smoke test.

- Triggers: push and pull request against `master`, `refactor/monorepo-structure`, and `refactor/monorepo`.
- Pushes to a feature branch alone do **not** trigger CI — open a PR to the integration branch to get checks.
- There is no frontend CI job yet. Run `npm run check`, `npm run typecheck`, and `npm run build` from `frontend/`
  locally; add a frontend job when the app lands.
- The final integration into `master` must verify the complete project.

## Frontend Workflow

`frontend/frontend-todo.md` is the ordered checklist, and frontend work proceeds one phase at a time:

- `/build-frontend-next` runs the read-only `frontend-todo-reader` to brief the next unfinished phase, then
  `frontend-builder` to implement it, run the frontend checks, and tick the completed tasks.
- Pass a phase explicitly with `/build-frontend-next 2` when needed.
- Do not use the backend `todo-reader`/`builder` pair for frontend work.
- Keep changes inside `frontend/`; do not modify backend, MCP, CI, or Postman files.

## Core Principles

1. **Safety First**: Any destructive action or tool (e.g., file deletion, trashing, disk cleanup) must default to dry-run mode (`confirm=False`).
2. **Safe Deletion**: Always use `send2trash` for sending files to the system trash. Direct unlinking (`os.remove`, `os.rmdir`, `shutil.rmtree`) is strictly prohibited unless explicitly requested by the user.
3. **FastMCP Protocol**: Ensure all FastMCP tool functions in `mcp-server/src/storage_intelligence_mcp/tools/` accept `Context` for progress and error reporting (`await ctx.info(...)`, `await ctx.error(...)`).
4. **Structured Tool Outputs**: Return consistent dictionary payloads containing execution modes (`preview` vs `executed`), path counts, lists of deleted items, and failed items.
5. **Agent Tool Boundary**: The backend's LLM agent may only ever receive tools on `READONLY_TOOL_ALLOWLIST` (`backend/src/storage_intelligence_backend/mcp/manager.py`) — the ten read-only analysis tools plus the MCP server's `preview_trash`. The raw `trash_path` tool is never exposed to the model. `POST /api/cleanup/execute` is the only route permitted to call `trash_path(confirm=True)`, and the frontend owns the selection state that feeds it.
6. **Documentation Placement**: The root `README.md` holds the project overview (architecture, HTTP API, CI, shared workflow). Each package holds its own README for its own detail (tools and prompts for `mcp-server/`, endpoints and settings for `backend/`, setup and routes for `frontend/`). Put a fact in exactly one place — do not copy the same content into the root README and a package README.
7. **Frontend Safety**: Provider API keys live in React memory only — never in `localStorage`, `sessionStorage`, cookies, IndexedDB, URLs, logs, or error messages. Never use `dangerouslySetInnerHTML` for model output. Cleanup never runs automatically; a human selects and confirms exact paths. The only mutating request is `POST /api/cleanup/execute` with exactly `{ paths }`; never expose `trash_path` to the browser. Do not invent endpoints or response fields.

## Quality Standards & Tooling

These standards apply across the monorepo. The Python packages (`mcp-server/`, `backend/`) share Ruff,
Pyright, and Pytest; the frontend uses Biome, TypeScript, and Vite. Each Python package has its own
`pyproject.toml` with `[tool.ruff]` and `[tool.pyright]` configured to the same standards, and its own
`.venv`.

### Python packages

- **Package Manager**: Use `uv` for environment and dependency management.
- **Linter & Formatter**: Code must adhere to Ruff standards (`py313` target, 88 line length).
- **Type Checker**: Use Pyright (`basic` mode, configured in each package's `pyproject.toml` under `[tool.pyright]`). All code must pass type checking.
- **Testing**: Use Pytest for tests (run with `uv run pytest` from the package directory); all existing tests must keep passing.
- **Verification Commands** (run all from the package directory — `mcp-server/` or `backend/` — before considering a task complete):
  - `uv run ruff check --fix`
  - `uv run ruff format`
  - `uv run pyright --project pyproject.toml`
  - `uv run pytest`

> A repo-root `pyrightconfig.json` exists only so editors can type-check the whole workspace. `--project pyproject.toml`
> is required for CLI runs; otherwise Pyright discovers the root config and checks both packages with one virtualenv.

### Frontend

The frontend is a Vite + React + TypeScript app managed with npm.

- **Package Manager**: npm; commit the lockfile.
- **Stack**: React + Vite + TypeScript (strict), Tailwind CSS v4, shadcn/ui, React Router, TanStack Query, Axios, Framer Motion, lucide-react, and Biome.
- **Lint & format**: `npm run check` (Biome check, covers lint and format). Use `npm run format` or `npm run check:write` to apply fixes.
- **Type Checking**: `npm run typecheck`. It must actually check `src`; Vite's solution-style `tsconfig` can make `tsc --noEmit` a no-op, so use `tsc -b` when needed.
- **Build**: `npm run build`.
- **Testing**: Vitest/RTL are deferred for v1. Rely on Biome check, typecheck, build, and the manual verification matrix in `frontend/FRONTEND_HANDOFF.md`.
- **Scope discipline**: Do not add Zustand/Redux/Jotai, chart libraries, a heavy UI kit, Vitest/RTL, or MSW without approval. Biome owns lint and format; do not add ESLint or Prettier.
- **Verification Commands** (run from `frontend/` before considering a task complete):
  - `npm run check`
  - `npm run typecheck`
  - `npm run build`

## MCP Servers

This environment has MCP servers enabled (use them when relevant):

- `docs-langchain` — Docs by LangChain search/retrieval. Use for LangChain/LangGraph questions; prefer server results over prior knowledge and cite sources. Read-only, scoped to published docs.
- `reference-langchain` — LangChain API reference search/get_symbol. Use to look up classes/functions/symbols and get signatures/parameters/examples.
- `postman` — Postman API/workspace operations. Follow its instructions resource for usage.
