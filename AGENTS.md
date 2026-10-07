# Storage Intelligence - Agent Guidelines & Rules

## Core Principles

1. **Safety First**: Any destructive action or tool (e.g., file deletion, trashing, disk cleanup) must default to dry-run mode (`confirm=False`).
2. **Safe Deletion**: Always use `send2trash` for sending files to the system trash. Direct unlinking (`os.remove`, `os.rmdir`, `shutil.rmtree`) is strictly prohibited unless explicitly requested by the user.
3. **FastMCP Protocol**: Ensure all FastMCP tool functions in `src/storage_intelligence/tools/` accept `Context` for progress and error reporting (`await ctx.info(...)`, `await ctx.error(...)`).
4. **Structured Tool Outputs**: Return consistent dictionary payloads containing execution modes (`preview` vs `executed`), path counts, lists of deleted items, and failed items.

## Quality Standards & Tooling

- **Package Manager**: Use `uv` for environment and dependency management.
- **Linter & Formatter**: Code must adhere to Ruff standards (`py313` target, 88 line length).
- **Verification Commands**:
  - `uv run ruff check --fix`
  - `uv run ruff format`

## TODO - Review Fixes (storage.py / cleanup.py)

Work through these one for one. Check off by removing the `- [ ]` marker when fixed and verified.

For each todo item fixed, generate a commit message based on my commit message naming conventions , but do not commit it.

### Code validity

- [x] TypedDicts for the 8 bare-dict storage tools so FastMCP advertises output schemas: `count_files` (storage.py:150), `directory_disk_usage` (:197), `get_disk_usage` (:261), `file_info` (:300), `find_large_files` (:339), `find_duplicate_files` (:389), `find_stale_files` (:462), `find_junk_files` (:619). Only `find_empty_directories` and `trash_path` have them today (see utils.py:7-13 rationale).
- [x] `directory_disk_usage:241` - top-level file `stat()` not wrapped in `try/except OSError`, unlike `dir_size` (:225-228). One unreadable file aborts the whole ranking; sibling tools skip silently.
- [x] `file_info:323-324` - `created: stat.st_ctime` is inode change time on POSIX, not creation. macOS has `st_birthtime`; Linux has no birth time. Rename the field or fix the docstring.
- [x] Nondeterministic tie order in `count_files:186` and `find_junk_files:674` - sort by `(-count, name)` so ties don't follow filesystem order.
- [x] Result-shape drift - `get_disk_usage` and `find_junk_files` include `"path"`; `count_files` and `directory_disk_usage` don't. Align the storage tools on including it.
- [x] Broken-symlink edge in `directory_disk_usage:244-251` - non-file, non-dir children fall into the `else` branch, get size 0, and are labeled `"directory"`.
- [x] `find_junk_files` build-artifact gap - header line 30 and the plan promise `node_modules`, `__pycache__`, `dist`, `build`, `target`; code matches only extensions + `.DS_Store`. Implement directory-name matching or amend the header.

### Docstrings, arguments, comments

- [x] `find_junk_files:629` - docstring hardcodes "capped at 25" while code uses `SAMPLE_LIMIT`; reference the constant instead.
- [ ] `trash_path:32-39` - docstring silent on dedup (:48-51) and missing-path tolerance (:53-63); both are implemented, the model needs to know before batching.
- [ ] `find_stale_files:472-473` - "Results are uncapped in count but cut at `max_results`" is self-contradictory; means the scan is uncapped but output is cut.
- [ ] `explore_directory:92` - honest that `max_results` truncation is silent, but `str` return leaves no room for a `truncated` flag; consider a structured return like the other tools.
- [x] Header comment (storage.py:30) claims `find_junk_files` covers build artifacts - disagrees with docstring and code (resolve together with the validity item above).
