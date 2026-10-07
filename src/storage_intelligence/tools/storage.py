import hashlib
import shutil
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from storage_intelligence.core import mcp
from storage_intelligence.utils import (
    CountFilesResult,
    DirectoryUsageEntry,
    DuplicateFileGroup,
    FileInfoResult,
    FindEmptyDirectoriesResult,
    FindJunkFilesResult,
    GetDiskUsageResult,
    LargeFileEntry,
    StaleFileEntry,
    path_error,
    unexpected_error,
)

# ===============================================
# List of storage analysis tools, in the order they are implemented:
# ===============================================
# 1. explore_directory - list_directory + file_names + search_files + tree
# 2. count_files - how many files of each type are in this folder?
# 3. directory_disk_usage - directory_sizes + directory_disk_usage
# 4. get_disk_usage - keep for now
# 5. file_info - keep for now
# 6. find_large_files - keep for now
# 7. find_duplicate_files - keep for now
# 8. find_stale_files - keep for now
# 9. find_empty_directories - keep for now
# 10. find_junk_files - temp, cache, .DS_Store, build artifacts
# ===============================================

# Read only annotation hint, because these tools do not modify the file system
READ_ONLY = ToolAnnotations(readOnlyHint=True)

# Home directory for the user
DEFAULT_PATH = str(Path.home())

# Cap the sample list so a broad scan cannot flood the model's context: a
# recursive search of the home directory can match tens of thousands of paths.
# The exact count is reported separately and is never truncated.
SAMPLE_LIMIT = 25

# Junk-file suffixes matched by find_junk_files, compared against Path.suffix
# in lowercased form. `.DS_Store` is handled separately by name check because
# a leading-dot filename has no suffix in pathlib.
JUNK_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".log",
        ".tmp",
        ".temp",
        ".cache",
        ".backup",
        ".bak",
        ".old",
        ".swp",
        ".swo",
        ".swn",
        ".o",
        ".obj",
        ".exe",
        ".dll",
        ".lib",
        ".a",
        ".so",
        ".out",
    }
)


# 1. explore_directory - list_directory + file_names + search_files + tree
@mcp.tool(annotations=READ_ONLY)
async def explore_directory(
    ctx: Context,
    path: str = DEFAULT_PATH,
    pattern: str = "",
    search: str = "",
    kind: Literal["all", "files", "dirs"] = "all",
    recursive: bool = False,
    max_results: int = 100,
) -> str:
    """List the contents of a directory, one entry per line.

    Each line is prefixed with a folder or file emoji. Non-recursive (default):
    shows only what sits directly inside `path` and names entries by their bare
    name. Recursive: walks every depth below `path` and names entries by their
    path relative to `path`, e.g. `src/storage_intelligence/core.py`. Returns
    "Directory is empty" when nothing matched the filters.

    `pattern` and `search` filter on the entry's own name, not on the relative
    path, so `*.py` still matches `core.py` at any depth. Output stops at
    `max_results` without saying so, so treat a capped list as an excerpt.

    Args:
        path: Absolute directory path to list. Defaults to the home directory.
        pattern: Glob pattern matched against each entry's name, e.g. '*.py'.
            Case sensitivity follows the platform. Empty matches every entry.
        search: Case-insensitive substring the entry's name must contain.
            Empty matches every entry.
        kind: 'all' (default) lists both files and directories, 'files' only
            files, 'dirs' only directories.
        recursive: False (default) lists immediate children only. True descends
            the whole tree below `path` and reports relative paths.
        max_results: Stop after this many matching entries. Default 100.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"explore_directory failed: {path} does not exist")
            return path_error("explore_directory", path)

        await ctx.info(f"Listing directory: {path}")

        entries = []

        path_contents = p.rglob("*") if recursive else p.iterdir()

        for child in path_contents:
            child_name = child.name

            if pattern and not fnmatch.fnmatch(child_name, pattern):
                continue

            if search and search.lower() not in child_name.lower():
                continue

            is_dir = child.is_dir()
            is_file = child.is_file()

            if kind == "files" and not is_file:
                continue
            if kind == "dirs" and not is_dir:
                continue

            prefix = "📁 " if is_dir else "📄 "
            entry_name = child.relative_to(p) if recursive else child.name
            entries.append(f"{prefix}{entry_name}")

            if len(entries) >= max_results:
                break

        return "\n".join(entries) if entries else "Directory is empty"
    except Exception as exc:
        await ctx.error(f"explore_directory failed: {type(exc).__name__}: {exc}")
        return unexpected_error("explore_directory", path, exc)


# 2. count_files - how many files of each type are in this folder?
@mcp.tool(annotations=READ_ONLY)
async def count_files(ctx: Context, path: str = DEFAULT_PATH) -> CountFilesResult:
    """Count files in a directory, grouped by file extension.

    Non-recursive: counts only files directly inside `path`. Directories and
    subdirectory contents are ignored, so this answers "what is in this folder"
    rather than "how much is under it". Extensions are lowercased, so `.PY` and
    `.py` group together; files without an extension are counted as
    "(no extension)". Groups are sorted by count, largest first.

    Args:
        path: Absolute directory path to inspect. Defaults to the home directory.
    """
    try:
        p = Path(path)

        if not p.exists():
            await ctx.error(f"count_files failed: {path} does not exist")
            return path_error("count_files", path)

        if not p.is_dir():
            await ctx.error(f"count_files failed: {path} is not a directory")
            return path_error("count_files", path)

        await ctx.info(f"Counting files in: {path}")

        total = 0
        by_extension: dict[str, int] = {}

        for child in p.iterdir():
            if child.is_file():
                total += 1
                ext = child.suffix.lower() or "(no extension)"
                by_extension[ext] = by_extension.get(ext, 0) + 1

        return {
            "total_files": total,
            "by_extension": dict(sorted(by_extension.items(), key=lambda x: -x[1])),
        }
    except Exception as exc:
        await ctx.error(f"count_files failed: {type(exc).__name__}: {exc}")
        return unexpected_error("count_files", path, exc)


# 3. directory_disk_usage - which subdirectories consume the most space?
@mcp.tool(annotations=READ_ONLY)
async def directory_disk_usage(
    ctx: Context, path: str = DEFAULT_PATH, top_n: int = 10
) -> list[DirectoryUsageEntry]:
    """Find the largest immediate children of a directory, in bytes.

    Ranks only the direct children of `path`, though each directory's size is
    measured recursively across everything beneath it. So the entry for a
    subdirectory reflects its whole subtree, but the set of candidates is just
    one level deep -- a directory buried three levels down is only reported if
    its parent is among the top results. Sorted largest first.

    Unreadable files are skipped silently rather than reported, so a single
    permissions problem or race cannot abort the ranking.

    Args:
        path: Absolute directory path whose children should be ranked.
        top_n: How many of the largest entries to return. Default 10.
    """
    try:
        p = Path(path)

        if not p.exists():
            await ctx.error(f"directory_disk_usage failed: {path} does not exist")
            return path_error("directory_disk_usage", path)

        if not p.is_dir():
            await ctx.error(f"directory_disk_usage failed: {path} is not a directory")
            return path_error("directory_disk_usage", path)

        def dir_size(d: Path) -> int:
            total = 0
            for child in d.rglob("*"):
                if child.is_file():
                    try:
                        total += child.stat().st_size
                    except OSError:
                        continue
            return total

        await ctx.info(f"Computing recursive disk usage in: {path} (top_n={top_n})")

        results = []

        for child in p.iterdir():
            if child.is_file():
                try:
                    size_bytes = child.stat().st_size
                except OSError:
                    continue
                results.append(
                    {
                        "name": child.name,
                        "type": "file",
                        "size_bytes": size_bytes,
                    }
                )
            else:
                results.append(
                    {
                        "name": child.name,
                        "type": "directory",
                        "size_bytes": dir_size(child),
                    }
                )
        results.sort(key=lambda x: x["size_bytes"], reverse=True)
        return results[:top_n]
    except Exception as exc:
        await ctx.error(f"directory_disk_usage failed: {type(exc).__name__}: {exc}")
        return unexpected_error("directory_disk_usage", path, exc)


# 4. get_disk_usage - how much space is left on this volume?
@mcp.tool(annotations=READ_ONLY)
async def get_disk_usage(ctx: Context, path: str = DEFAULT_PATH) -> GetDiskUsageResult:
    """Get total, used, and free space for the volume containing a path.

    Reports the whole filesystem or volume that `path` lives on, not just `path`
    itself. Used bytes count everything on that volume including unrelated
    system and application data, so a free-space reading here is not
    attributable to any one directory.

    Args:
        path: Any existing path on the volume to measure. Defaults to the home
            directory.
    """
    try:
        p = Path(path)

        if not p.exists():
            await ctx.error(f"get_disk_usage failed: {path} does not exist")
            return path_error("get_disk_usage", path)

        await ctx.info(f"Getting disk usage for: {path}")

        total, used, free = shutil.disk_usage(p)
        usage_percent = round(used / total * 100, 1) if total else 0.0

        return {
            "path": str(p),
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "usage_percent": usage_percent,
        }

    except Exception as exc:
        await ctx.error(f"get_disk_usage failed: {type(exc).__name__}: {exc}")
        return unexpected_error("get_disk_usage", path, exc)


# 5. file_info - when was this file last modified?
@mcp.tool(annotations=READ_ONLY)
async def file_info(ctx: Context, path: str = DEFAULT_PATH) -> FileInfoResult:
    """Get metadata about a single file or directory.

    Reports name, size, modification and creation times as Unix timestamps, and
    whether the path is a file or a directory. Directories have a small
    platform-dependent `size_bytes` that reflects the entry itself, not the
    space its contents occupy.

    Args:
        path: Absolute path to the file or directory to inspect.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"file_info failed: {path} does not exist")
            return path_error("file_info", path)
        await ctx.info(f"Getting metadata for: {path}")
        stat = p.stat()
        return {
            "name": p.name,
            "path": str(p),
            "type": "directory" if p.is_dir() else "file",
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "extension": p.suffix,
        }
    except Exception as exc:
        await ctx.error(f"file_info failed: {type(exc).__name__}: {exc}")
        return unexpected_error("file_info", path, exc)


# 6. find_large_files - which files are bigger than a threshold?
@mcp.tool(annotations=READ_ONLY)
async def find_large_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    min_size_mb: float = 100.0,
    max_results: int = 50,
) -> list[LargeFileEntry]:
    """Find large files anywhere under a directory, largest first.

    Recursive. Matches on apparent file size, so a sparse file or hard link
    reports the size its contents imply rather than the blocks it occupies.
    Unreadable entries are skipped silently rather than reported, so a
    permissions problem looks the same as "nothing matched" here.

    Args:
        path: Absolute directory path to search under.
        min_size_mb: Minimum size in megabytes; 100.0 (default) means 100 MB.
        max_results: Maximum number of files to return. Default 50.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"find_large_files failed: {path} does not exist")
            return path_error("find_large_files", path)
        await ctx.info(
            f"Searching for files > {min_size_mb} MB in: {path} "
            f"(max_results={max_results})"
        )
        min_bytes = min_size_mb * 1024 * 1024
        results = []
        for child in p.rglob("*"):
            if not child.is_file():
                continue
            try:
                size = child.stat().st_size
            except OSError:
                continue
            if size >= min_bytes:
                results.append(
                    {
                        "path": str(child),
                        "size_bytes": size,
                        "size_mb": round(size / (1024 * 1024), 1),
                    }
                )
        results.sort(key=lambda x: x["size_bytes"], reverse=True)
        return results[:max_results]
    except Exception as exc:
        await ctx.error(f"find_large_files failed: {type(exc).__name__}: {exc}")
        return unexpected_error("find_large_files", path, exc)


# 7. find_duplicate_files - are there identical files lurking around?
@mcp.tool(annotations=READ_ONLY)
async def find_duplicate_files(
    ctx: Context, path: str = DEFAULT_PATH, min_size_bytes: int = 1024
) -> list[DuplicateFileGroup]:
    """Find groups of files with identical content, grouped by SHA-256 hash.

    Recursive. Two-stage for speed: files are bucketed by size first, then only
    buckets with more than one member are hashed. That means small files are
    silently excluded by the default `min_size_bytes` -- two identical 500-byte
    config files are not reported, and the result gives no hint that the floor
    applied. Lower the threshold to search small files, at the cost of hashing
    far more of them.

    Every path in a group is byte-identical, but which copy to keep is a
    judgement call this tool cannot make: the oldest, the newest, or the one
    outside a synced folder are all reasonable choices.

    Args:
        path: Absolute directory path to search under.
        min_size_bytes: Skip files smaller than this. Default 1024 (1 KB).
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"find_duplicate_files failed: {path} does not exist")
            return path_error("find_duplicate_files", path)
        await ctx.info(
            f"Scanning for duplicates in: {path} (min_size_bytes={min_size_bytes})"
        )

        def file_hash(fp: Path, chunk_size: int = 65536) -> str:
            h = hashlib.sha256()
            with fp.open("rb") as f:
                while chunk := f.read(chunk_size):
                    h.update(chunk)
            return h.hexdigest()

        by_size: dict[int, list[Path]] = {}
        for child in p.rglob("*"):
            if not child.is_file():
                continue
            try:
                size = child.stat().st_size
            except OSError:
                continue
            if size >= min_size_bytes:
                by_size.setdefault(size, []).append(child)

        groups: dict[tuple[int, str], list[str]] = {}
        for size, files in by_size.items():
            if len(files) < 2:
                continue
            for fp in files:
                try:
                    digest = file_hash(fp)
                except OSError:
                    continue
                groups.setdefault((size, digest), []).append(str(fp))

        return [
            {"size_bytes": size, "files": paths}
            for (size, _digest), paths in sorted(groups.items(), key=lambda x: -x[0][0])
            if len(paths) > 1
        ]
    except Exception as exc:
        await ctx.error(f"find_duplicate_files failed: {type(exc).__name__}: {exc}")
        return unexpected_error("find_duplicate_files", path, exc)


# 8. find_stale_files - which files haven't been modified in a while?
@mcp.tool(annotations=READ_ONLY)
async def find_stale_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    days_unmodified: int = 90,
    max_results: int = 100,
) -> list[StaleFileEntry]:
    """Find files not modified for a while, least recently modified first.

    Recursive. Ages come from modification time (`st_mtime`), not access time --
    reading a file does not make it look fresher here. That is deliberate: most
    filesystems mount `noatime`, so access times are unreliable and would report
    nearly every file as stale. `days_unmodified` is age of the content, so a
    file edited recently but unchanged for years still qualifies as stale.

    Unreadable entries are skipped silently, so a permissions problem is
    indistinguishable from "nothing matched". Results are uncapped in count but
    cut at `max_results`; the oldest files come first, which is usually the
    useful end.

    Args:
        path: Absolute directory path to search under.
        days_unmodified: Age threshold in days. Default 90.
        max_results: Maximum number of files to return. Default 100.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"find_stale_files failed: {path} does not exist")
            return path_error("find_stale_files", path)
        await ctx.info(
            f"Scanning for stale files in: {path} (days_unmodified={days_unmodified})"
        )

        now = time.time()
        threshold_seconds = days_unmodified * 86400
        stale_files = []

        for child in p.rglob("*"):
            if not child.is_file():
                continue
            try:
                stat_result = child.stat()
                mtime = stat_result.st_mtime
                age_seconds = now - mtime
                if age_seconds > threshold_seconds:
                    stale_files.append(
                        {
                            "path": str(child),
                            "size_bytes": stat_result.st_size,
                            "days_unmodified": round(age_seconds / 86400, 1),
                        }
                    )
            except OSError:
                continue

        stale_files.sort(key=lambda x: x["days_unmodified"], reverse=True)
        return stale_files[:max_results]
    except Exception as exc:
        await ctx.error(f"find_stale_files failed: {type(exc).__name__}: {exc}")
        return unexpected_error("find_stale_files", path, exc)


# 9. find_empty_directories - which folders would be cleaned up?
@mcp.tool(annotations=READ_ONLY)
async def find_empty_directories(
    ctx: Context, path: str = DEFAULT_PATH, recursive: bool = True
) -> FindEmptyDirectoriesResult:
    """Find empty directories, including parents left empty by their children.

    Read-only: nothing is deleted here. The returned paths are what can be
    passed to `trash_path` to remove them.

    The cascade is simulated, not read off the filesystem. In a chain like
    `a/b/c`, only `c` is empty right now; `a/b` and `a` become empty once `c` is
    gone. A plain scan would report just `c`, so directories are walked deepest
    first and each candidate's already-matched children are filtered out of its
    listing. Paths come back deepest first, which is the order they must be
    deleted in.

    Directories that cannot be read (usually permissions) are counted in
    `skipped_directories` rather than treated as empty, so an unreadable folder
    is never proposed for deletion. Symlinks are followed when deciding whether
    a directory is empty, so a link to an empty folder is reported and trashing
    the link leaves the target alone.

    `path` itself is never reported, only what is below it.

    Args:
        path: Absolute directory path to search under. Must be a directory.
        recursive: True (default) searches at every depth. False checks only
            the immediate children, and so reports no cascade: a subdirectory
            still containing its own child is not empty at that point.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"find_empty_directories failed: {path} does not exist")
            return path_error("find_empty_directories", path)
        if not p.is_dir():
            await ctx.error(f"find_empty_directories failed: {path} is not a directory")
            return path_error("find_empty_directories", path)

        if recursive:
            subdirs = sorted(
                [d for d in p.rglob("*") if d.is_dir()],
                key=lambda d: len(d.parts),
                reverse=True,
            )
        else:
            subdirs = [d for d in p.iterdir() if d.is_dir()]

        await ctx.info(
            f"Scanning for empty directories in: {path} (recursive={recursive})"
        )

        # Directories that would be deleted. Read-only here: nothing is removed,
        # so this is a prediction of what a delete run would remove.
        virtual_deleted: set[Path] = set()
        skipped_dirs: list[str] = []

        for subdir in subdirs:
            try:
                contents = list(subdir.iterdir())
            except OSError as exc:
                skipped_dirs.append(str(subdir))
                await ctx.warning(
                    f"Skipped unreadable directory '{subdir}': "
                    f"{type(exc).__name__}: {exc}"
                )
                continue
            # A child already in the set still shows up in its parent's listing,
            # because nothing was actually removed. Filter those out before
            # judging emptiness, otherwise a parent that becomes empty only
            # because its children were deleted is never reported.
            remaining = [c for c in contents if c not in virtual_deleted]

            if not remaining:
                virtual_deleted.add(subdir)

        # Deepest first, and tie-break on the path so the order is stable across
        # runs. This is not cosmetic: it is the order the paths must be deleted
        # in. Trashing a parent first would succeed and carry its children away
        # with it, leaving every child to fail afterwards as "File not found".
        candidates = sorted(virtual_deleted, key=lambda d: (-len(d.parts), str(d)))
        total = len(candidates)

        return {
            "path": str(p),
            "recursive": recursive,
            "total_empty_directories": total,
            "sample": [str(d) for d in candidates[:SAMPLE_LIMIT]],
            "truncated": total > SAMPLE_LIMIT,
            "skipped_directories_count": len(skipped_dirs),
            "skipped_directories": skipped_dirs,
        }
    except Exception as exc:
        await ctx.error(f"find_empty_directories failed: {type(exc).__name__}: {exc}")
        return unexpected_error("find_empty_directories", path, exc)


# 10. find_junk_files - which junk files are cluttering this folder?
@mcp.tool(annotations=READ_ONLY)
async def find_junk_files(
    ctx: Context, path: str = DEFAULT_PATH
) -> FindJunkFilesResult:
    """Find junk files in a directory, grouped by file extension.

    Junk files are identified by suffix, comparing each file's lowercased
    suffix against a fixed list (see JUNK_EXTENSIONS): .log, .tmp, .temp,
    .cache, .backup, .bak, .old, .swp, .swo, .swn, .o, .obj, .exe, .dll, .lib,
    .a, .so, .out. The filename `.DS_Store` is also matched by name, since it
    has no suffix.

    Non-recursive: only files directly inside `path` are inspected. Returns
    counts plus a `sample` of matching paths capped at 25, so results can be
    passed straight to `trash_path`. `truncated` reports whether the sample is
    shorter than the total. Build-artifact directories such as `node_modules`,
    `__pycache__`, `dist`, `build` and `target` are not covered yet.

    Args:
        path: Absolute directory path to inspect. Defaults to the home directory.
    """
    try:
        p = Path(path)

        if not p.exists():
            await ctx.error(f"find_junk_files failed: {path} does not exist")
            return path_error("find_junk_files", path)

        if not p.is_dir():
            await ctx.error(f"find_junk_files failed: {path} is not a directory")
            return path_error("find_junk_files", path)

        await ctx.info(f"Counting junk files in: {path}")

        total = 0
        by_extension: dict[str, int] = {}
        sample: list[str] = []

        for child in p.iterdir():
            if not child.is_file():
                continue

            suffix = child.suffix.lower()
            if suffix in JUNK_EXTENSIONS:
                ext = suffix
            elif child.name == ".DS_Store":
                ext = ".ds_store"
            else:
                continue

            total += 1
            by_extension[ext] = by_extension.get(ext, 0) + 1
            if len(sample) < SAMPLE_LIMIT:
                sample.append(str(child))

        return {
            "path": str(p),
            "total_files": total,
            "by_extension": dict(sorted(by_extension.items(), key=lambda x: -x[1])),
            "sample": sample,
            "truncated": total > SAMPLE_LIMIT,
        }

    except Exception as exc:
        await ctx.error(f"find_junk_files failed: {type(exc).__name__}: {exc}")
        return unexpected_error("find_junk_files", path, exc)
