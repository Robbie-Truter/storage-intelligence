from pathlib import Path

from fastmcp import Context
from mcp.types import ToolAnnotations
from send2trash import send2trash

from storage_intelligence.core import mcp
from storage_intelligence.utils import (
    TrashPathResult,
    path_error,
    unexpected_error,
)

# ===============================================
# List of storage cleanup tools, in the order they are implemented:
# ===============================================
# 1. trash_path - delete a specific file or directory safely
# ===============================================

# Destructive annotation hint because cleanup tools modify or delete files
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)


# 1. trash_path - delete a specific file or directory safely
@mcp.tool(annotations=DESTRUCTIVE)
async def trash_path(
    ctx: Context, path: str | list[str], confirm: bool = False
) -> TrashPathResult:
    """Send one or more files or directories to the trash.

    Accepts a single path or a list. Directories are trashed whole. Targets are
    trashed deepest path first so nested path reporting stays accurate.

    Args:
        path: A single file/directory path string or a list of path strings.
        confirm: False (default) returns a dry-run preview. True executes deletion.
    """
    try:
        targets = [path] if isinstance(path, str) else list(path)

        if not targets:
            await ctx.error("trash_path failed: no paths given")
            return unexpected_error("trash_path", "", ValueError("no paths given"))

        # Deduplicate: the same path listed twice would trash once and then fail
        # as missing, which reads like an error but is just redundant input.
        seen: set[str] = set()
        unique = [t for t in targets if not (t in seen or seen.add(t))]

        existing = [p for p in unique if Path(p).exists()]
        missing = [p for p in unique if not Path(p).exists()]

        if missing and not existing:
            await ctx.error(f"trash_path failed: paths do not exist: {missing}")
            return path_error("trash_path", ", ".join(missing))

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
        return unexpected_error(
            "trash_path", path if isinstance(path, str) else ", ".join(path), exc
        )
