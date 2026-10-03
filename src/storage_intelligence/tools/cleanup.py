from pathlib import Path

from fastmcp import Context
from mcp.types import ToolAnnotations
from send2trash import send2trash

from storage_intelligence.core import mcp
from storage_intelligence.utils import (
    EmptyDirectoriesResult,
    path_error,
    unexpected_error,
)

# ===============================================
# List of storage cleanup tools, in the order they are implemented:
# ===============================================
# 1. delete_file - delete a specific file safely
# 2. delete_empty_directories - find and remove empty folders in a path
# 3. clean_temp_files - remove temporary files (.tmp, .bak, ~*, etc.)
# 4. remove_duplicate_files - remove duplicate files keeping one original copy
# 5. archive_stale_files - move or compress files unmodified for X days
# 6. clean_cache_directories - clear cache directories (__pycache__, .cache, etc.)
# ===============================================

# Destructive annotation hint because cleanup tools modify or delete files
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)

# Home directory for the user
DEFAULT_PATH = str(Path.home())


# 1. delete_file - delete a specific file safely
@mcp.tool(annotations=DESTRUCTIVE)
async def delete_file(
    ctx: Context, path: str, dry_run: bool = True, confirm: bool = False
) -> str | dict:
    """Delete a single file at the specified path."""
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"list_directory failed: {path} does not exist")
            return path_error("list_directory", path)
        if dry_run:
            return f"Dry run: Would delete '{path}'"
        if not confirm:
            return f"Dry run: Would delete '{path}'. Use confirm=True to delete."
        send2trash(str(p))
        await ctx.info(f"Deleted file: {path}")
        return f"Deleted file: {path}"
    except Exception as exc:
        await ctx.error(f"delete_file failed: {type(exc).__name__}: {exc}")
        return unexpected_error("delete_file", path, exc)


# 2. delete_empty_directories - find and remove empty folders in a path
@mcp.tool(annotations=DESTRUCTIVE)
async def delete_empty_directories(
    ctx: Context,
    path: str = DEFAULT_PATH,
    recursive: bool = True,
    confirm: bool = False,
) -> EmptyDirectoriesResult:
    """Recursively search for and remove empty directories within a path.

    With confirm=False (the default) nothing is deleted: the same scan runs
    and a preview is returned, so call it first to see what would go. Re-run
    with confirm=True to perform the deletion.
    """

    # Cap the preview list so a broad scan cannot flood the model's context
    PREVIEW_SAMPLE_LIMIT = 25

    virtual_deleted: set[Path] = set()
    deleted_count = 0
    deleted_dirs = []
    skipped_count = 0
    skipped_dirs = []
    failed_count = 0
    failed_dirs = []

    async def deleteSubDir(directory: Path) -> bool:
        """Trash one empty directory. Returns True only if it is really gone.

        The caller uses that to decide whether a parent directory is now empty:
        a failed send2trash leaves the child in place, so counting it as
        deleted would make the parent look deletable when it is not.
        """
        nonlocal deleted_count, failed_count
        await ctx.info(f"Deleting empty directory: {directory}")
        try:
            send2trash(str(directory))
        except OSError as exc:
            failed_count += 1
            failed_dirs.append(str(directory))
            await ctx.warning(
                f"Failed to delete empty directory '{directory}': "
                f"{type(exc).__name__}: {exc}"
            )
            return False
        deleted_count += 1
        deleted_dirs.append(str(directory))
        return True

    async def build_preview_result():
        nonlocal skipped_count, skipped_dirs

        if recursive:
            subdirs = sorted(
                [d for d in p.rglob("*") if d.is_dir()],
                key=lambda p: len(p.parts),
                reverse=True,
            )

        else:
            subdirs = [d for d in p.iterdir() if d.is_dir()]

        for subdir in subdirs:
            try:
                contents = list(subdir.iterdir())
            except OSError as exc:
                skipped_count += 1
                skipped_dirs.append(str(subdir))
                await ctx.warning(
                    f"Skipped unreadable directory '{subdir}': "
                    f"{type(exc).__name__}: {exc}"
                )
                continue
            # A child that has been trashed (or claimed by the preview) still
            # shows up in its parent's listing, so filter those out before
            # judging emptiness. Without this, a parent that becomes empty
            # because its children were removed is never detected, and preview
            # under-reports the cascade that execution performs.
            remaining = [c for c in contents if c not in virtual_deleted]

            if not remaining:
                if confirm:
                    if await deleteSubDir(subdir):
                        virtual_deleted.add(subdir)
                else:
                    virtual_deleted.add(subdir)

    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"delete_empty_directories failed: {path} does not exist")
            return path_error("delete_empty_directories", path)

        if not p.is_dir():
            await ctx.error(
                f"delete_empty_directories failed: {path} is not a directory"
            )
            return path_error("delete_empty_directories", path)

        if not confirm:
            await build_preview_result()

            candidates = sorted(str(d) for d in virtual_deleted)
            total = len(candidates)

            return {
                "mode": "preview",
                "path": str(p),
                "recursive": recursive,
                "requires_confirmation": True,
                "total_empty_directories": total,
                "sample": candidates[:PREVIEW_SAMPLE_LIMIT],
                "truncated": total > PREVIEW_SAMPLE_LIMIT,
                "deleted_directories_count": 0,
                "deleted_directories": [],
                "skipped_directories_count": skipped_count,
                "skipped_directories": skipped_dirs,
                "failed_directories_count": failed_count,
                "failed_directories": failed_dirs,
            }

        await build_preview_result()

        return {
            "mode": "executed",
            "path": str(p),
            "recursive": recursive,
            "requires_confirmation": False,
            "deleted_directories_count": deleted_count,
            "deleted_directories": deleted_dirs,
            "skipped_directories_count": skipped_count,
            "skipped_directories": skipped_dirs,
            "failed_directories_count": failed_count,
            "failed_directories": failed_dirs,
        }

    except Exception as exc:
        await ctx.error(f"delete_empty_directories failed: {type(exc).__name__}: {exc}")
        return unexpected_error("delete_empty_directories", path, exc)


# ========================================================
# ========ONLY WRITE CODE BELOW THIS COMMENT, LEAVE CODE ABOVE FOR NOW================
# ========================================================
# 3. trash_path - delete a specific file safely
@mcp.tool(annotations=DESTRUCTIVE)
async def trash_path(
    ctx: Context, path: str | list[str], confirm: bool = False
) -> str | dict:
    """Delete a single file or directory at the specified path."""
    try:
        targets = [path] if isinstance(path, str) else path

        existing = [p for p in targets if Path(p).exists()]
        missing = [p for p in targets if not Path(p).exists()]

        if missing and not existing:
            await ctx.error(f"trash_path failed: paths do not exist: {missing}")
            return path_error("trash_path", str(missing))

        if not confirm:
            return {
                "mode": "preview",
                "requires_confirmation": True,
                "total_valid_paths": len(existing),
                "paths": existing,
                "missing_paths": missing,
                "message": "Dry run: Call trash_path with confirm=True to send items to"
                " trash.",
            }

        deleted = []
        failed = []
        for p in existing:
            try:
                send2trash(p)
                await ctx.info(f"Deleted file: {p}")
                deleted.append(p)
            except Exception as exc:
                failed.append({"path": p, "error": str(exc)})
                await ctx.error(f"trash_path failed: {type(exc).__name__}: {exc}")

        return {
            "mode": "executed",
            "deleted_count": len(deleted),
            "failed_count": len(failed),
            "deleted": deleted,
            "failed": failed,
            "missing_paths": missing,
        }

    except Exception as exc:
        return unexpected_error("trash_path", path, exc)
