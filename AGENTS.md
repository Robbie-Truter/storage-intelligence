# Storage Intelligence - Agent Guidelines & Rules

## Repository Layout

This repository is a monorepo. The root holds:

- `mcp-server/` — the Python FastMCP server (its own `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, and `tests/`).
- `backend/` — application backend (FastAPI + LangChain; its own `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, and `tests/`).
- `frontend/` — application frontend (placeholder).
- `.opencode/` — opencode configuration (subagents, slash commands, skills), and `.github/` — shared CI workflows.

All Python commands below run from the package directory you are working in (`mcp-server/` or `backend/`). Each package is a self-contained `uv` project with its own `.venv` and tool config — do not run one package's commands from another's directory.

The root `README.md` is the project overview. Each package documents itself in its own README
(`mcp-server/README.md`, `backend/README.md`) — the package READMEs are the detailed reference, the root README
is the shared context, and the two never duplicate the same content. `AGENTS.md` (this file) holds the repo-wide
rules; `BACKEND_HANDOFF.md` holds the backend design decisions and roadmap.

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
- Frontend development may use mocked API responses while the backend API contract is being developed.
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
- Frontend checks are added when the frontend project is ready.
- The final integration into `master` must verify the complete project.

## Core Principles

1. **Safety First**: Any destructive action or tool (e.g., file deletion, trashing, disk cleanup) must default to dry-run mode (`confirm=False`).
2. **Safe Deletion**: Always use `send2trash` for sending files to the system trash. Direct unlinking (`os.remove`, `os.rmdir`, `shutil.rmtree`) is strictly prohibited unless explicitly requested by the user.
3. **FastMCP Protocol**: Ensure all FastMCP tool functions in `mcp-server/src/storage_intelligence_mcp/tools/` accept `Context` for progress and error reporting (`await ctx.info(...)`, `await ctx.error(...)`).
4. **Structured Tool Outputs**: Return consistent dictionary payloads containing execution modes (`preview` vs `executed`), path counts, lists of deleted items, and failed items.
5. **Agent Tool Boundary**: The backend's LLM agent may only ever receive tools on `READONLY_TOOL_ALLOWLIST` (`backend/src/storage_intelligence_backend/mcp/manager.py`) — the ten read-only analysis tools plus the MCP server's `preview_trash`. The raw `trash_path` tool is never exposed to the model. `POST /api/cleanup/execute` is the only route permitted to call `trash_path(confirm=True)`, and the frontend owns the selection state that feeds it.
6. **Documentation Placement**: The root `README.md` holds the project overview (architecture, HTTP API, CI, shared workflow). Each package holds its own README for its own detail (tools and prompts for `mcp-server/`, endpoints and settings for `backend/`). Put a fact in exactly one place — do not copy the same content into the root README and a package README.

## Quality Standards & Tooling

These standards apply to every Python package in the monorepo (`mcp-server/`, `backend/`). Each package has
its own `pyproject.toml` with `[tool.ruff]` and `[tool.pyright]` configured to the same standards, and its
own `.venv`.

- **Package Manager**: Use `uv` for environment and dependency management.
- **Linter & Formatter**: Code must adhere to Ruff standards (`py313` target, 88 line length).
- **Type Checker**: Use Pyright (`basic` mode, configured in each package's `pyproject.toml` under `[tool.pyright]`). All code must pass type checking.
- **Testing**: Use Pytest for tests (run with `uv run pytest` from the package directory); all existing tests must keep passing.
- **Verification Commands** (run all from the package directory — `mcp-server/` or `backend/` — before considering a task complete):
  - `uv run ruff check --fix`
  - `uv run ruff format`
  - `uv run pyright`
  - `uv run pytest`

## MCP Servers

This environment has MCP servers enabled (use them when relevant):

- `docs-langchain` — Docs by LangChain search/retrieval. Use for LangChain/LangGraph questions; prefer server results over prior knowledge and cite sources. Read-only, scoped to published docs.
- `reference-langchain` — LangChain API reference search/get_symbol. Use to look up classes/functions/symbols and get signatures/parameters/examples.
- `postman` — Postman API/workspace operations. Follow its instructions resource for usage.
