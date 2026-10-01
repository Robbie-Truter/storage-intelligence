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

    deleted_count = 0
    deleted_dirs = []
    skipped_count = 0
    skipped_dirs = []
    failed_count = 0
    failed_dirs = []

    async def deleteSubDir(directory: Path):
        nonlocal deleted_count, deleted_dirs, failed_count, failed_dirs
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
            return
        deleted_count += 1
        deleted_dirs.append(str(directory))

    async def build_preview_result(callback):
        import inspect

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
            if not contents:
                res = callback(subdir)

                if inspect.iscoroutine(res):
                    await res

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
            virtual_deleted = []

            await build_preview_result(
                lambda folder: virtual_deleted.append(str(folder))
            )

            return {
                "mode": "preview",
                "path": str(p),
                "recursive": recursive,
                "requires_confirmation": True,
                "deleted_directories_count": 0,
                "deleted_directories": [],
                "skipped_directories_count": 0,
                "skipped_directories": [],
                "failed_directories_count": 0,
                "failed_directories": [],
            }

        await build_preview_result(deleteSubDir)

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


# 3. clean_temp_files - remove temporary files (.tmp, .bak, ~*, etc.)
@mcp.tool(annotations=DESTRUCTIVE)
async def clean_temp_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    patterns: list[str] | None = None,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Search for and delete temporary files matching specified glob patterns."""
    # TODO: Implement pattern matching for temp files and safe deletion/dry-run options.
    pass


# 4. remove_duplicate_files - remove duplicate files keeping one original copy
@mcp.tool(annotations=DESTRUCTIVE)
async def remove_duplicate_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Identify duplicate files by hash and remove redundant copies."""
    # TODO: Implement hash comparison to detect duplicates and delete
    # redundant copies safely.
    pass


# 5. archive_stale_files - move or compress files unmodified for X days
@mcp.tool(annotations=DESTRUCTIVE)
async def archive_stale_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    days_unmodified: int = 90,
    destination_archive: str = "",
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Archive files that have not been modified within the specified threshold."""
    # TODO: Implement stale file scanning and moving/compressing logic to
    # an archive destination.
    pass


# 6. clean_cache_directories - clear cache directories (__pycache__, .cache, etc.)
@mcp.tool(annotations=DESTRUCTIVE)
async def clean_cache_directories(
    ctx: Context,
    path: str = DEFAULT_PATH,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Find and clear standard system/application cache directories."""
    # TODO: Implement directory pattern matching for known cache folders
    # and removal logic.
    pass
