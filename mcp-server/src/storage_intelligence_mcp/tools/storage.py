import fnmatch
import hashlib
import shutil
import time
from pathlib import Path
from typing import Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from storage_intelligence_mcp.core import mcp
from storage_intelligence_mcp.utils import (
    CountFilesResult,
    DirectoryDiskUsageResult,
    DuplicateFileGroup,
    ExploreDirectoryEntry,
    ExploreDirectoryResult,
    FileInfoResult,
    FindEmptyDirectoriesResult,
    FindJunkFilesResult,
    GetDiskUsageResult,
    LargeFileEntry,
    StaleFileEntry,
    not_a_directory_error,
    path_error,
)

# ===============================================
# List of storage analysis tools, in the order they are implemented:
# ===============================================
# 1. explore_directory - what is in this directory?
# 2. count_files - how many files of each type are in this folder?
# 3. directory_disk_usage - which immediate children consume the most space?
# 4. disk_usage - how much space is left on this volume?
# 5. file_info - metadata for a single file or directory
# 6. find_large_files - which files are bigger than a threshold?
# 7. find_duplicate_files - are there identical files lurking around?
# 8. find_stale_files - which files haven't been modified in a while?
# 9. find_empty_directories - which folders would be cleaned up?
# 10. find_junk_files - which junk files and build artifacts clutter this folder?
# ===============================================

# Read only annotation hint, because these tools do not modify the file system
READ_ONLY = ToolAnnotations(read_only_hint=True)

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

# Build-artifact directory names matched by find_junk_files. Compared
# case-sensitively against top-level entry names: these are conventional
# spellings, and a lowercase "Dist" directory is not one of them.
JUNK_DIRECTORIES: frozenset[str] = frozenset(
    {"node_modules", "__pycache__", "dist", "build", "target"}
)


# 1. explore_directory - what is in this directory?
@mcp.tool(annotations=READ_ONLY)
async def explore_directory(
    ctx: Context,
    path: str = DEFAULT_PATH,
    pattern: str = "",
    search: str = "",
    kind: Literal["all", "files", "dirs"] = "all",
    recursive: bool = False,
    max_results: int = 100,
) -> ExploreDirectoryResult:
    """List the entries in a directory by name.

    Use when: the user asks what a directory contains, or wants to find
    entries whose names match a glob (`pattern`) or contain a substring
    (`search`). When both filters are set, an entry must satisfy both.

    Not for: file counts or disk usage; use `count_files` and
    `directory_disk_usage`. This tool reports neither sizes nor counts.

    Scope: immediate children by default. `recursive=True` walks every depth
    below `path`. Filters match the entry's own name, not its path, so `*.py`
    matches `core.py` at any depth.

    Output: `entries` in scan order (not sorted), each with a bare `name`, a
    full `path`, and a `type` of "file" or "directory". Scanning stops at
    `max_results`; `truncated` is true when more matches existed, so a capped
    list is known to be an excerpt. Empty `entries` with `truncated` false
    means nothing matched: an empty directory and filters that exclude
    everything are indistinguishable.

    Limits: does not calculate disk usage, count files, inspect file contents,
    or recurse unless asked. Do not list a directory again just to total its
    size or count its files; prior `directory_disk_usage` or `count_files`
    results already cover that. Once the listing answers the question, answer
    instead of gathering extra context.

    Args:
        path: Absolute directory path to list. Defaults to the home directory.
        pattern: Glob pattern matched against each entry's name, e.g. '*.py'.
            Case sensitivity follows the platform. Empty matches every entry.
        search: Case-insensitive substring the entry's name must contain.
            Empty matches every entry.
        kind: 'all' (default) lists both files and directories, 'files' only
            files, 'dirs' only directories.
        recursive: False (default) lists immediate children only. True descends
            the whole tree below `path` and reports entries at any depth.
        max_results: Stop after this many matching entries. Default 100.
    """
    args = {
        "path": path,
        "pattern": pattern,
        "search": search,
        "kind": kind,
        "recursive": recursive,
        "max_results": max_results,
    }
    await ctx.info(f"Tool called: explore_directory with arguments {args}")
    try:
        p = Path(path)
        if not p.exists():
            raise path_error(path)

        if not p.is_dir():
            raise not_a_directory_error(path)

        await ctx.info(f"Listing directory: {path}")

        entries: list[ExploreDirectoryEntry] = []
        truncated = False

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

            # Checked before appending: reaching the cap only proves
            # truncation when one more match actually exists, so an exact
            # fit stays truncated=False.
            if len(entries) >= max_results:
                truncated = True
                break

            prefix = "directory" if is_dir else "file"
            entry_name = child.relative_to(p) if recursive else child.name
            entries.append(
                {
                    "name": child.name,
                    "path": str(p / entry_name),
                    "type": prefix,
                }
            )

        return {"path": str(p), "entries": entries, "truncated": truncated}
    except Exception as exc:
        await ctx.error(f"explore_directory failed: {type(exc).__name__}: {exc}")
        raise


# 2. count_files - how many files of each type are in this folder?
@mcp.tool(annotations=READ_ONLY)
async def count_files(ctx: Context, path: str = DEFAULT_PATH) -> CountFilesResult:
    """Count the files directly inside a directory, grouped by extension.

    Use when: the user asks how many files a folder holds, or what file types
    it contains.

    Not for: a recursive total. This tool returns no names or paths and
    computes no sizes. Use `explore_directory` to see or filter entries, and
    `directory_disk_usage` for space. Do not recurse separately to obtain a
    total that another tool's result already provides.

    Scope: non-recursive. Subdirectories and everything beneath them are
    ignored.

    Output: `total_files`, and `by_extension` with lowercased extensions (so
    `.PY` and `.py` merge), files without an extension grouped under
    "(no extension)", sorted by count (largest first), then name.

    Limits: counts files, not bytes; each file counts once regardless of size.
    It does not inspect subdirectories or file contents.

    Args:
        path: Absolute directory path to inspect. Defaults to the home directory.
    """
    args = {"path": path}
    await ctx.info(f"Tool called: count_files with arguments {args}")
    try:
        p = Path(path)

        if not p.exists():
            raise path_error(path)

        if not p.is_dir():
            raise not_a_directory_error(path)

        await ctx.info(f"Counting files in: {path}")

        total = 0
        by_extension: dict[str, int] = {}

        for child in p.iterdir():
            if child.is_file():
                total += 1
                ext = child.suffix.lower() or "(no extension)"
                by_extension[ext] = by_extension.get(ext, 0) + 1

        return {
            "path": str(p),
            "total_files": total,
            "by_extension": dict(
                sorted(by_extension.items(), key=lambda x: (-x[1], x[0]))
            ),
        }
    except Exception as exc:
        await ctx.error(f"count_files failed: {type(exc).__name__}: {exc}")
        raise


# 3. directory_disk_usage - which immediate children consume the most space?
@mcp.tool(annotations=READ_ONLY)
async def directory_disk_usage(
    ctx: Context, path: str = DEFAULT_PATH, top_n: int = 10
) -> DirectoryDiskUsageResult:
    """Rank the immediate children of a directory by total size in bytes.

    Use when: the user asks which folders or files inside a directory consume
    the most space. This is the size answer: a directory entry is measured
    recursively, so its `size_bytes` already includes every nested file and
    subdirectory.

    Not for: recomputing the same totals with `explore_directory`,
    `count_files`, or another size scan. To drill into a specific child, call
    this tool again with `path` set to that child and a new, narrower question.

    Scope: candidates are direct children only, but directory sizes cover
    their whole subtrees. A directory several levels down appears only if its
    parent is among the returned entries. Top-level files report their own
    size.

    Output: the largest `top_n` entries, largest first, each with a bare
    `name`, a `type` of "file" or "directory", and `size_bytes`. There is no
    total and no `truncated` flag, so entries beyond `top_n` are omitted
    silently.

    Limits: apparent size (`st_size`), not allocated blocks. Unreadable files,
    broken symlinks, sockets and FIFOs are skipped silently, so a permissions
    problem can look like missing data.

    Args:
        path: Absolute directory path whose children should be ranked.
        top_n: How many of the largest entries to return. Default 10.
    """
    args = {"path": path, "top_n": top_n}
    await ctx.info(f"Tool called: directory_disk_usage with arguments {args}")
    try:
        p = Path(path)

        if not p.exists():
            raise path_error(path)

        if not p.is_dir():
            raise not_a_directory_error(path)

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
            elif child.is_dir():
                results.append(
                    {
                        "name": child.name,
                        "type": "directory",
                        "size_bytes": dir_size(child),
                    }
                )
            else:
                continue
        results.sort(key=lambda x: x["size_bytes"], reverse=True)

        return {"path": str(p), "entries": results[:top_n]}

    except Exception as exc:
        await ctx.error(f"directory_disk_usage failed: {type(exc).__name__}: {exc}")
        raise


# 4. disk_usage - how much space is left on this volume?
@mcp.tool(annotations=READ_ONLY)
async def disk_usage(ctx: Context, path: str = DEFAULT_PATH) -> GetDiskUsageResult:
    """Report total, used, and free space for the volume containing `path`.

    Use when: the user asks how full a volume is or how much free space
    remains.

    Not for: measuring a directory's size; use `directory_disk_usage` for
    immediate children or `file_info` for a single entry. This describes the
    whole volume, not `path` itself.

    Scope: the filesystem or volume containing any existing path, file or
    directory. `used_bytes` includes unrelated system and application data,
    so it cannot be attributed to one directory.

    Output: `total_bytes`, `used_bytes`, `free_bytes`, and `usage_percent`
    (used divided by total, one decimal, or 0.0 for a zero-size volume).

    Limits: no breakdown by folder and no per-directory totals. A free-space
    reading here does not answer "what is taking space inside this folder".

    Args:
        path: Any existing path on the volume to measure. Defaults to the home
            directory.
    """
    args = {"path": path}
    await ctx.info(f"Tool called: disk_usage with arguments {args}")
    try:
        p = Path(path)

        if not p.exists():
            raise path_error(path)

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
        await ctx.error(f"disk_usage failed: {type(exc).__name__}: {exc}")
        raise


# 5. file_info - metadata for a single file or directory
@mcp.tool(annotations=READ_ONLY)
async def file_info(ctx: Context, path: str = DEFAULT_PATH) -> FileInfoResult:
    """Return metadata for one file or directory.

    Use when: the user asks about a specific path's size, type, extension, or
    modified or created time.

    Not for: comparing multiple entries or measuring a directory's contents;
    use `directory_disk_usage` for that, or `explore_directory` to list a
    directory.

    Scope: exactly one path, file or directory. It does not list a directory's
    children or recurse.

    Output: `name`, `path`, `type` ("file" or "directory"), `size_bytes`,
    `modified` and `created` as Unix timestamps, and `extension` (including
    the dot, or "" when there is none).

    Limits: a directory's `size_bytes` is the small platform-dependent inode
    entry size, not the total of its contents. `created` prefers the
    platform's birth time (macOS `st_birthtime`); where none exists it falls
    back to `st_ctime`, which is creation time on Windows but last
    metadata-change time on Linux. Does not report permissions, ownership, or
    contents.

    Args:
        path: Absolute path to the file or directory to inspect.
    """
    args = {"path": path}
    await ctx.info(f"Tool called: file_info with arguments {args}")
    try:
        p = Path(path)
        if not p.exists():
            raise path_error(path)

        await ctx.info(f"Getting metadata for: {path}")

        stat = p.stat()

        return {
            "name": p.name,
            "path": str(p),
            "type": "directory" if p.is_dir() else "file",
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
            "created": getattr(stat, "st_birthtime", stat.st_ctime),
            "extension": p.suffix,
        }

    except Exception as exc:
        await ctx.error(f"file_info failed: {type(exc).__name__}: {exc}")
        raise


# 6. find_large_files - which files are bigger than a threshold?
@mcp.tool(annotations=READ_ONLY)
async def find_large_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    min_size_mb: float = 100.0,
    max_results: int = 50,
) -> list[LargeFileEntry]:
    """Find individual files at or above a size threshold under a directory.

    Use when: the user asks for the largest files, files over N MB, or which
    single files are consuming space. This tool reports individual files, not
    just the largest folders.

    Not for: ranking directories; use `directory_disk_usage`, whose entries
    already include all nested content, instead of repeating this scan to
    reconstruct a directory total.

    Scope: recursive. Every file below `path` is tested. Matches are returned
    largest first and capped at `max_results`.

    Output: entries with `path`, `size_bytes`, and `size_mb`.

    Limits: compares apparent size (`st_size`), so sparse files and hard links
    report the size their contents imply rather than the blocks they occupy.
    Unreadable entries are skipped silently, so a permissions problem looks
    like "nothing matched". There is no total-match count or `truncated` flag,
    so a result that fills `max_results` may omit smaller matches. A large
    file is not necessarily unused or safe to delete.

    Args:
        path: Absolute directory path to search under.
        min_size_mb: Minimum size in megabytes; 100.0 (default) means 100 MB.
        max_results: Maximum number of files to return. Default 50.
    """
    args = {"path": path, "min_size_mb": min_size_mb, "max_results": max_results}
    await ctx.info(f"Tool called: find_large_files with arguments {args}")
    try:
        p = Path(path)
        if not p.exists():
            raise path_error(path)
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
        raise


# 7. find_duplicate_files - are there identical files lurking around?
@mcp.tool(annotations=READ_ONLY)
async def find_duplicate_files(
    ctx: Context, path: str = DEFAULT_PATH, min_size_bytes: int = 1024
) -> list[DuplicateFileGroup]:
    """Find groups of files with identical content using SHA-256.

    Use when: the user asks for duplicate files or space wasted on copies.
    Equal size alone is not evidence of duplication.

    Not for: inferring duplicates from size alone; equal size is not evidence
    of equal content, and this tool may read file contents to hash them.

    Scope: recursive. Files are bucketed by size first, then only same-size
    buckets with at least two members are hashed. Returns groups of two or
    more byte-identical files, sorted by shared file size, largest first.
    Unique files produce no group.

    Output: each group has the shared `size_bytes` and the `files` paths of
    its identical copies.

    Limits: `min_size_bytes` (default 1024) silently excludes smaller files,
    and the result does not indicate that the floor applied -- identical
    500-byte configs are not reported. Lower it to include small files, at the
    cost of hashing far more of them. Hashing large trees can be slow.
    Unreadable files are skipped silently. Byte-identical does not mean
    disposable: keeping the oldest, the newest, or the copy outside a synced
    folder are all reasonable choices, but none is automatically safe to
    delete.

    Args:
        path: Absolute directory path to search under.
        min_size_bytes: Skip files smaller than this. Default 1024 (1 KB).
    """
    args = {"path": path, "min_size_bytes": min_size_bytes}
    await ctx.info(f"Tool called: find_duplicate_files with arguments {args}")
    try:
        p = Path(path)
        if not p.exists():
            raise path_error(path)
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
        raise


# 8. find_stale_files - which files haven't been modified in a while?
@mcp.tool(annotations=READ_ONLY)
async def find_stale_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    days_unmodified: int = 90,
    max_results: int = 100,
) -> list[StaleFileEntry]:
    """Find files not modified within a number of days, oldest first.

    Use when: the user asks which files have not been touched recently, or for
    old files in a directory.

    Not for: junk, duplicates, empty directories, or size. Use
    `find_junk_files`, `find_duplicate_files`, `find_empty_directories`, or
    `find_large_files` for those questions. This tool answers age only.

    Scope: recursive. Age comes from modification time (`st_mtime`), not
    access time, so reading a file does not make it look fresher. That is
    deliberate: many filesystems mount `noatime`, making access times
    unreliable and liable to mark nearly every file as stale.

    Output: `path`, `size_bytes`, and `days_unmodified`, oldest first, capped
    at `max_results`.

    Limits: the scan is uncapped but the returned list is cut at `max_results`
    with no `truncated` flag or total count. Unreadable entries are skipped
    silently, so a permissions problem is indistinguishable from "nothing
    matched". Old is not the same as unnecessary or safe to delete; confirm
    with the user and inspect the file before proposing removal.

    Args:
        path: Absolute directory path to search under.
        days_unmodified: Age threshold in days. Default 90.
        max_results: Maximum number of files to return. Default 100.
    """
    args = {
        "path": path,
        "days_unmodified": days_unmodified,
        "max_results": max_results,
    }
    await ctx.info(f"Tool called: find_stale_files with arguments {args}")
    try:
        p = Path(path)
        if not p.exists():
            raise path_error(path)

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
        raise


# 9. find_empty_directories - which folders would be cleaned up?
@mcp.tool(annotations=READ_ONLY)
async def find_empty_directories(
    ctx: Context, path: str = DEFAULT_PATH, recursive: bool = True
) -> FindEmptyDirectoriesResult:
    """Find empty directories, including parents that empty out in a cascade.

    Use when: the user asks which folders are empty, or what cleanup would
    remove.

    Not for: file age, junk, duplicates, or size; use `find_stale_files`,
    `find_junk_files`, `find_duplicate_files`, or `directory_disk_usage`.
    This tool is read-only; returned paths are potential cleanup candidates,
    not deletion instructions.

    Scope: `recursive=True` (default) walks every depth and simulates the
    cascade. In `a/b/c`, only `c` is empty now, but `a/b` and `a` become empty
    once `c` is gone, so all are reported. It walks deepest first and filters
    already-matched children out of each parent's listing. Results are deepest
    first -- the order they must be removed in. `recursive=False` checks
    immediate children only and reports no cascade.

    Output: `path`, `recursive`, the exact `total_empty_directories`, a
    `sample` of at most 25 paths (deepest first) with `truncated` when the
    sample is shorter than the total, and `skipped_directories` /
    `skipped_directories_count` for directories that could not be read. `path`
    itself is never reported.

    Limits: unreadable directories (usually permissions) are counted as
    skipped, never proposed as empty, so an unreadable folder is never a
    deletion candidate. Symlinks are followed when judging emptiness, so a
    link to an empty folder can be reported; trashing the link leaves its
    target alone. Empty does not mean safe to remove -- confirm with the user.
    Do not rescan to count them; the result already has the count.

    Args:
        path: Absolute directory path to search under. Must be a directory.
        recursive: True (default) searches at every depth. False checks only
            the immediate children, and so reports no cascade: a subdirectory
            still containing its own child is not empty at that point.
    """
    args = {"path": path, "recursive": recursive}
    await ctx.info(f"Tool called: find_empty_directories with arguments {args}")
    try:
        p = Path(path)
        if not p.exists():
            raise path_error(path)
        if not p.is_dir():
            raise not_a_directory_error(path)

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
        raise


# 10. find_junk_files - which junk files and build artifacts clutter this folder?
@mcp.tool(annotations=READ_ONLY)
async def find_junk_files(
    ctx: Context, path: str = DEFAULT_PATH
) -> FindJunkFilesResult:
    """Find junk files and build-artifact directories inside a directory.

    Use when: the user asks about temporary files, logs, caches, or build
    output in one folder, or how many such items it contains.

    Not for: age, duplicates, large files, or general cleanup. Use
    `find_stale_files`, `find_duplicate_files`, `find_large_files`, or
    `directory_disk_usage` for those questions. This tool matches fixed names
    and extensions only.

    Scope: non-recursive. Only immediate children of `path` are inspected; a
    nested `node_modules` under a child folder is not found unless this tool
    is called on that folder.

    Files match by lowercased suffix from a fixed list (`.log`, `.tmp`,
    `.temp`, `.cache`, `.backup`, `.bak`, `.old`, `.swp`, `.swo`, `.swn`,
    `.o`, `.obj`, `.exe`, `.dll`, `.lib`, `.a`, `.so`, `.out`); `.DS_Store`
    matches by name. Directories match by exact name: `node_modules`,
    `__pycache__`, `dist`, `build`, `target`.

    Output: `total_files`, `by_extension` (with `.ds_store` for `.DS_Store`),
    the uncapped `directories` list, and a `sample` of file paths capped at 25,
    with `truncated` when the sample is shorter than `total_files`.
    `directories` is not included in the counts. Both `sample` and
    `directories` are potential cleanup candidates, not deletion instructions.

    Limits: a name or extension match does not mean the file is unnecessary or
    safe to delete -- confirm with the user and inspect before removing. It
    does not measure sizes, ages, or contents, and it does not recurse.

    Args:
        path: Absolute directory path to inspect. Defaults to the home directory.
    """
    args = {"path": path}
    await ctx.info(f"Tool called: find_junk_files with arguments {args}")
    try:
        p = Path(path)

        if not p.exists():
            raise path_error(path)

        if not p.is_dir():
            raise not_a_directory_error(path)

        await ctx.info(f"Counting junk files and build directories in: {path}")

        total = 0
        by_extension: dict[str, int] = {}
        directories: list[str] = []
        sample: list[str] = []

        for child in p.iterdir():
            if child.is_dir():
                if child.name in JUNK_DIRECTORIES:
                    directories.append(str(child))
                continue

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
            "by_extension": dict(
                sorted(by_extension.items(), key=lambda x: (-x[1], x[0]))
            ),
            "directories": sorted(directories),
            "sample": sample,
            "truncated": total > SAMPLE_LIMIT,
        }

    except Exception as exc:
        await ctx.error(f"find_junk_files failed: {type(exc).__name__}: {exc}")
        raise
