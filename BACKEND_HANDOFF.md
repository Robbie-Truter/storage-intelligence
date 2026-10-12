# Backend Handoff

Context for the next workstream: building `backend/`. No code here — background and direction only.

## What we did

- Converted the repo into a monorepo. Command runner / git root: `storage-intelligence/`.
- Moved the existing Python MCP project into `mcp-server/` as a self-contained `uv` project (its own `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, `tests/`, `.venv`, `Makefile`, `README.md`).
- Left the package name and all imports unchanged (`storage_intelligence`); this was a pure move, not a rename.
- Added placeholder `backend/` and `frontend/` directories.
- Kept shared tooling at the root: `.agents/` skills, `.github/workflows/ci.yml`, `AGENTS.md`, root `README.md`.
- Added root-level editor config: `pyrightconfig.json` (points Pyright/Pylance at `mcp-server/.venv` and `mcp-server/src`) and `.vscode/settings.json` (interpreter → `mcp-server/.venv/bin/python`).
- Verified `mcp-server/` from inside it: ruff, ruff format, pyright, 119 pytest tests, `uv build`, and server import all pass.

## Why we did it

- Separate the MCP server, backend, and frontend into independent projects under one repo.
- Keep each package's dependencies, virtualenv, and tool config isolated (no shared venv).
- Give shared agent guidance and CI a single home at the root.

## Key constraint learned

The current tooling is scoped to `mcp-server/`. Root `pyrightconfig.json` and `.vscode/settings.json` point only at that package, and ruff config lives in `mcp-server/pyproject.toml`. A new package does **not** inherit this — it needs its own setup (see below).

## Next steps: backend (FastAPI + LangChain)

Goal: a `backend/` service (FastAPI) that uses LangChain to talk to the `mcp-server` over MCP, likely exposing HTTP endpoints and/or streaming to the `frontend/`.

- Scaffold `backend/` as its own `uv` project: `pyproject.toml`, `uv.lock`, `.python-version`, `.venv`, `src/`, `tests/`, `README.md`.
- Add tool config in `backend/pyproject.toml`: `[tool.ruff]`, `[tool.pyright]`, pytest settings.
- Update root `pyrightconfig.json` to cover both packages — either `executionEnvironments` for `mcp-server` and `backend`, or add a `backend/pyrightconfig.json`.
- Extend `.github/workflows/ci.yml` to run the same lint/format/type/test steps per package (e.g. a matrix over `[mcp-server, backend]`), since the current job hard-codes `working-directory: mcp-server`.
- Decide how the backend reaches the MCP server: launch it as a subprocess over stdio, or connect to a running/SSE instance. Note the local launch form is `uv run --directory mcp-server storage-intelligence`.
- Wire in FastAPI app + LangChain + an MCP client, with tests (FastAPI `TestClient`/`httpx`, async test mode).
- Later: define the contract the `frontend/` consumes.

## References

- Monorepo changes and rationale: `MONOREPO_MIGRATION_PLAN.md`.
- Repo-wide rules and verification commands: `AGENTS.md`.
- Shared skills: `.agents/skills/` (`python-quality`, `fastmcp-tool-dev`, `safe-cleanup-testing`).
- MCP server details: `mcp-server/README.md`.
