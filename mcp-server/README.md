# Storage Intelligence — MCP Server

A local-first [FastMCP](https://gofastmcp.com) server for storage analysis,
disk usage profiling, duplicate and junk detection, and **recoverable** cleanup.

It exposes structured tools, one resource, and nine prompts over the Model
Context Protocol. Everything runs on the local machine: file paths and metadata
never leave it.

This is the `mcp-server/` package of the Storage Intelligence monorepo. The
project overview lives in the [root README](../README.md); the HTTP service
built on top of this server lives in [`backend/`](../backend/README.md).

---

## Contents

- [Architecture](#architecture)
- [Directory structure](#directory-structure)
- [Tools](#tools)
  - [Analysis tools](#analysis-tools)
  - [Cleanup tools](#cleanup-tools)
- [Resource](#resource)
- [Prompts](#prompts)
- [Safety model](#safety-model)
- [Result and error contract](#result-and-error-contract)
- [Getting started](#getting-started)
- [Client configuration](#client-configuration)
- [Make targets](#make-targets)
- [Quality checks](#quality-checks)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                MCP client (Claude Desktop, Cursor, …)            │
└───────────────────────────────┬──────────────────────────────────┘
                                │  Model Context Protocol (stdio)
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│              Storage Intelligence — MCP Server                   │
│                                                                  │
│  core.py      FastMCP instance + server instructions            │
│  server.py    entry point; imports register every primitive      │
│                                                                  │
│  tools/       storage.py (10 analysis) · cleanup.py (2 trash)   │
│  resources/   info://server                                      │
│  prompts/     storage.py (6 analysis) · cleanup.py (3 cleanup)   │
└───────────────────────────────┬──────────────────────────────────┘
                                │  local file I/O
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Local File System                         │
└──────────────────────────────────────────────────────────────────┘
```

The server is started by the `storage-intelligence` console script
(`storage_intelligence_mcp.server:main`) and speaks MCP over stdio. It never
uses elicitation, sampling, or roots.

---

## Directory structure

```
src/storage_intelligence_mcp/
├── __init__.py         # package marker
├── core.py             # FastMCP instance + server instructions
├── server.py           # entry point; imports register the primitives
├── utils.py            # response TypedDicts + path error helpers
├── tools/
│   ├── storage.py      # 10 read-only analysis tools
│   └── cleanup.py      # preview_trash + trash_path (send2trash)
├── resources/
│   └── example.py      # info://server
└── prompts/
    ├── storage.py      # 6 analysis prompts
    └── cleanup.py      # 3 cleanup prompts
```

---

## Tools

Twelve tools in total: ten read-only analysis tools, one read-only preview
tool, and one mutating tool.

Every tool takes an optional `path` and falls back to the **home directory**
when it is omitted. Analysis tools are annotated `read_only_hint=True`;
`trash_path` is annotated `read_only_hint=False, destructive_hint=True`.

### Analysis tools

All ten live in `tools/storage.py` and never modify the filesystem.

| Tool | Parameters (defaults) | Returns |
| ---- | --------------------- | ------- |
| `explore_directory` | `path`, `pattern=""`, `search=""`, `kind="all"`, `recursive=False`, `max_results=100` | `path`, `entries[]`, `truncated` |
| `count_files` | `path` | `path`, `total_files`, `by_extension` |
| `directory_disk_usage` | `path`, `top_n=10` | `path`, `entries[]` |
| `disk_usage` | `path` | `path`, `total_bytes`, `used_bytes`, `free_bytes`, `usage_percent` |
| `file_info` | `path` | `name`, `path`, `type`, `size_bytes`, `modified`, `created`, `extension` |
| `find_large_files` | `path`, `min_size_mb=100.0`, `max_results=50` | `[{path, size_bytes, size_mb}]` |
| `find_duplicate_files` | `path`, `min_size_bytes=1024` | `[{size_bytes, files[]}]` |
| `find_stale_files` | `path`, `days_unmodified=90`, `max_results=100` | `[{path, size_bytes, days_unmodified}]` |
| `find_empty_directories` | `path`, `recursive=True` | `path`, `recursive`, `total_empty_directories`, `sample[]`, `truncated`, `skipped_directories_count`, `skipped_directories[]` |
| `find_junk_files` | `path` | `path`, `total_files`, `by_extension`, `directories[]`, `sample[]`, `truncated` |

Behaviour worth knowing:

- **`explore_directory`** filters on the entry's *own name* (`pattern` is a glob,
  `search` is a case-insensitive substring), not on its path — `*.py` still
  matches `core.py` at any depth. Non-recursive it lists immediate children;
  recursive it walks the whole tree and reports full paths. Each entry carries
  its bare `name`, its full `path`, and a `type` label (`"directory "` or
  `"file "`). `truncated` says whether more matches existed beyond
  `max_results`.
- **`count_files`** and **`find_junk_files`** are non-recursive: they look at
  direct children only. Extensions are lowercased, so `.PY` and `.py` group
  together; files without an extension group under `"(no extension)"`.
- **`directory_disk_usage`** ranks only the direct children, but a directory's
  size covers its whole subtree. Unreadable files are skipped silently.
- **`disk_usage`** reports the whole **volume** containing `path`, not `path`
  itself — used bytes include unrelated system data.
- **`file_info`** reports `st_mtime` as `modified` and prefers the platform
  birth time (`st_birthtime` on macOS) for `created`, falling back to
  `st_ctime`.
- **`find_large_files`** matches on apparent size, so sparse files report the
  size their contents imply.
- **`find_duplicate_files`** is two-stage: files are bucketed by size first,
  and only buckets with more than one member are SHA-256 hashed. Files below
  `min_size_bytes` (1 KB by default) are silently skipped.
- **`find_stale_files`** ages by modification time, not access time — most
  filesystems mount `noatime`, so access times are unreliable. The scan is
  uncapped; the returned list is cut at `max_results`, oldest first.
- **`find_empty_directories`** *simulates* the cascade: in a chain `a/b/c`,
  `c` is empty now, and `a/b` and `a` become empty once `c` is gone. Results
  come back **deepest first** — that is the order they must be deleted in.
  Unreadable directories are counted in `skipped_directories`, never proposed
  for deletion. `path` itself is never reported.
- **`find_junk_files`** matches files by suffix — `.log`, `.tmp`, `.temp`,
  `.cache`, `.backup`, `.bak`, `.old`, `.swp`, `.swo`, `.swn`, `.o`, `.obj`,
  `.exe`, `.dll`, `.lib`, `.a`, `.so`, `.out` — plus `.DS_Store` by name, and
  top-level directories named `node_modules`, `__pycache__`, `dist`, `build`,
  or `target` (reported in `directories`).

### Cleanup tools

Both live in `tools/cleanup.py`. Targets arrive through two optional inputs
rather than one union-typed parameter: `path` takes a single path, `paths`
takes a list. Give one or the other, or both — they are combined and then
deduplicated. At least one target is required.

| Tool | Parameters (defaults) | Mutating |
| ---- | --------------------- | -------- |
| `preview_trash` | `path=""`, `paths=[]` | No — `read_only_hint=True` |
| `trash_path` | `path=""`, `paths=[]`, `confirm=False` | Yes — `destructive_hint=True` |

`preview_trash` returns a `preview` payload and never deletes anything.
`trash_path` is a **dry run unless `confirm=True`**; with `confirm=True` it
sends each target to the system trash through `send2trash` and returns an
`executed` payload.

```jsonc
// preview_trash — or trash_path without confirm=True, whose message reads
// "Dry run: ..." instead of "Preview only: ..."
{
  "mode": "preview",
  "requires_confirmation": true,
  "paths": ["/abs/deepest/path", "/abs/other/path"],
  "missing_paths": ["/abs/gone"],
  "total_valid_paths": 2,
  "message": "Preview only: Call trash_path with confirm=True to send items to trash."
}

// trash_path with confirm=True
{
  "mode": "executed",
  "requires_confirmation": false,
  "paths": ["/abs/deepest/path", "/abs/other/path"],
  "missing_paths": [],
  "total_valid_paths": 2,
  "deleted": ["/abs/deepest/path", "/abs/other/path"],
  "failed": [{ "path": "/abs/other/path", "error": "OSError: ..." }]
}
```

---

## Resource

| URI | Payload |
| --- | ------- |
| `info://server` | `{"name": "storage-intelligence", "version": "0.1.0"}` |

---

## Prompts

Nine prompts: six analysis (`prompts/storage.py`) and three cleanup
(`prompts/cleanup.py`). Each returns plain instructions that steer the model
through a workflow; the tools themselves supply the home directory when `path`
is omitted.

| Prompt | Parameters | Purpose |
| ------ | ---------- | ------- |
| `analyze_storage` | `path` | Disk usage for a directory and its volume |
| `analyze_home_storage` | — | Disk usage of the home directory |
| `find_old_files` | `path`, `days_unmodified=90` | Files not modified for a while |
| `find_duplicates` | `path` | Byte-identical copies wasting space |
| `clean_junk` | `path` | Inventory of junk files and empty directories |
| `free_up_space` | `path` | Ranked plan for reclaiming disk space |
| `prepare_cleanup` | `path` | Review junk, duplicates, stale files, empty dirs |
| `remove_junk` | `path` | Clean up junk files and build artifacts, after preview |
| `remove_empty_dirs` | `path` | Trash empty directories, after preview |

The six analysis prompts are read-only passes: they end with "do not delete or
modify anything". The three cleanup prompts are two-phase — the model must
call `trash_path` with `confirm=False`, show the preview, and only re-call it
with `confirm=True` after an explicit yes from the user.

---

## Safety model

- **Dry run by default.** `trash_path` without `confirm=True` returns a
  preview. The confirmation is the tool's own parameter, so it works in every
  MCP client.
- **Recoverable deletion.** `send2trash` moves targets to the system trash /
  Recycle Bin. Permanent unlinking (`os.remove`, `shutil.rmtree`) is never
  used.
- **Deduplicated, deepest-first.** Duplicate targets collapse into one, and
  targets are ordered deepest path first so nested reporting stays accurate
  and a parent is never trashed before its children.
- **Partial batches survive.** A missing path inside a mixed batch is reported
  in `missing_paths` and logged as a warning; only an all-missing batch fails,
  as a not-found error.
- **Bounded samples.** `find_junk_files` and `find_empty_directories` cap
  their path samples at 25 entries (`SAMPLE_LIMIT`) so a broad scan cannot
  flood the model's context. The exact count is reported separately and is
  never truncated.
- **Server instructions.** `core.py` ships workflow and safety instructions
  with the server, so a client sees them at connect time.

---

## Result and error contract

- Success payloads are `TypedDict`s (`utils.py`). FastMCP derives the
  advertised output schema from the return annotation, so the annotation only
  has to describe the success path.
- Errors are raised as `ToolError`. FastMCP turns them into a result with
  `is_error=True` and **no** `structured_content`. That asymmetry is
  deliberate: strict clients validate `structured_content` whenever it is
  present and ignore `isError`, so a structured error payload would be
  rejected as a schema mismatch and mask the real message.
- Every tool catches its own failures, logs them with `ctx.error(...)`, and
  re-raises. A re-raised `ToolError` stays an `FastMCPError` and is never
  masked by `mask_error_details`.
- `path_error()` reports a missing path; `not_a_directory_error()` reports a
  path that exists but is not a directory.

---

## Getting started

### Prerequisites

- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv)

### Run it

```bash
cd mcp-server

uv sync                                # install dependencies
uv run storage-intelligence            # run the server over stdio
```

`MCP_DEBUG=1` attaches a `debugpy` listener on `127.0.0.1:5678` before the
server starts.

---

## Client configuration

Point an MCP client at the console script. `uv run --directory <dir>` makes
the launch independent of the client's working directory:

```json
{
  "mcpServers": {
    "storage-intelligence": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/storage-intelligence/mcp-server",
        "storage-intelligence"
      ]
    }
  }
}
```

The backend uses exactly this launch shape — see
[`backend/.env.example`](../backend/.env.example) and
`StorageMCPClient` in `../backend/src/storage_intelligence_backend/mcp/manager.py`.

---

## Make targets

| Target | Does |
| ------ | ---- |
| `make run` | `uv run storage-intelligence` |
| `make inspect` | MCP Inspector against the server, with `MCP_DEBUG=1` |
| `make inspect-tools` | Inspector CLI: `tools/list` |
| `make inspect-prompts` | Inspector CLI: `prompts/list` |
| `make test` | `uv run pytest tests/storage -vv` — the storage suite only |

For the **full** suite (119 tests, including the cleanup tests) run
`uv run pytest`.

---

## Quality checks

Run from this directory:

```bash
uv run ruff check --fix
uv run ruff format
uv run pyright --project pyproject.toml
uv run pytest
uv build
```

The same checks run in CI for this package (see
[`../.github/workflows/ci.yml`](../.github/workflows/ci.yml)).
