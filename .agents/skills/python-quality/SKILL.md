---
name: python-quality
description: Runbook for linting, formatting, and running tests in storage-intelligence using uv and ruff.
---

# Python Code Quality Runbook

This skill outlines quality checks and commands for `storage-intelligence`.

## Environment Setup & Tooling

The project relies on `uv` for dependency management and `ruff` for linting/formatting.

### 1. Formatting & Linting
Run Ruff to fix lint issues and format files:
```bash
uv run ruff check --fix
uv run ruff format
```

### 2. Modern Python 3.13 Syntax
Target Python version is set to `py313` in `pyproject.toml`.
- Use modern type annotations (`list[str]`, `dict[str, Any]`, `str | None`).
- Use Python 3.13 features where applicable (e.g. `type` statement for type aliases).

### 3. Pre-Commit Checklist
Before finalizing changes or opening PRs:
1. Verify no unused imports or variables exist (`ruff check`).
2. Verify code adheres to 88-character line limits (`ruff format`).
3. Ensure all FastMCP tool functions have proper docstrings and context logging.
