from collections.abc import Sequence
from pathlib import Path

from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from send2trash import send2trash

from storage_intelligence.core import mcp
from storage_intelligence.utils import (
    TrashPathResult,
    path_error,
)

# ===============================================
# List of storage cleanup tools, in the order they are implemented:
# ===============================================
# 1. trash_path - delete a specific file or directory safely
# ===============================================

# Destructive annotation hint because cleanup tools modify or delete files
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True)


# 1. trash_path - delete a specific file or directory safely
@mcp.tool(annotations=DESTRUCTIVE)
async def trash_path(
    ctx: Context,
    path: str = "",
    paths: Sequence[str] = (),
    confirm: bool = False,
) -> TrashPathResult:
    """Send one or more files or directories to the trash.

    Targets arrive through two optional inputs rather than one union-typed
    parameter: `path` takes a single path, `paths` takes a list. Give one or
    the other, or both -- they are combined and then deduplicated. At least
    one target is required. Directories are trashed whole. Targets are
    trashed deepest path first so nested path reporting stays accurate.

    Batching does not need pre-validation. Duplicate entries are collapsed, so
    the same path listed twice trashes once instead of failing the second
    attempt. Missing paths are tolerated in a mixed batch: each is reported in
    `missing_paths` and logged as a warning while the rest proceed; only an
    all-missing batch fails, as a not-found error.

    Args:
        path: A single file/directory path string. Empty means "no single
            target" and is ignored when `paths` is also given.
        paths: A list of file/directory path strings. Empty means "no batch".
        confirm: False (default) returns a dry-run preview. True executes deletion.
    """
    try:
        targets = ([path] if path else []) + list(paths)

        if not targets:
            raise ToolError("No paths given")

        # Deduplicate: the same path listed twice would trash once and then fail
        # as missing, which reads like an error but is just redundant input.
        seen: set[str] = set()
        unique = [t for t in targets if not (t in seen or seen.add(t))]

        existing = [p for p in unique if Path(p).exists()]
        missing = [p for p in unique if not Path(p).exists()]

        if missing and not existing:
            raise path_error(", ".join(missing))

        if missing:
            await ctx.warning(
                f"Ignoring {len(missing)} path(s) that do not exist: {missing}"
            )

        ordered = sorted(existing, key=lambda t: (-len(Path(t).parts), t))

        if not confirm:
            return {
                "mode": "preview",
                "requires_confirmation": True,
                "paths": ordered,
                "missing_paths": missing,
                "total_valid_paths": len(ordered),
                "message": "Dry run: Call trash_path with confirm=True to send items "
                "to trash.",
            }

        deleted = []
        failed = []
        for p in ordered:
            try:
                send2trash(p)
                await ctx.info(f"Trashed: {p}")
                deleted.append(p)
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                failed.append({"path": p, "error": reason})
                await ctx.error(f"trash_path failed on '{p}': {reason}")

        return {
            "mode": "executed",
            "requires_confirmation": False,
            "paths": ordered,
            "missing_paths": missing,
            "total_valid_paths": len(ordered),
            "deleted": deleted,
            "failed": failed,
        }

    except Exception as exc:
        await ctx.error(f"trash_path failed: {type(exc).__name__}: {exc}")
        raise
