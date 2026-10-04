import hashlib
import shutil
import time
from pathlib import Path

from fastmcp import Context
from mcp.types import ToolAnnotations

from storage_intelligence.core import mcp
from storage_intelligence.utils import (
    FindEmptyDirectoriesResult,
    path_error,
    unexpected_error,
)

# ===============================================
# List of storage analysis tools, in the order they are implemented:
# ===============================================
# 1. list_directory - what's in this folder?
# 2. count_files - how many files of each type are in this folder?
# 3. file_names - show me all .txt files here
# 4. directory_sizes - what's taking up space?
# 5. search_files - find all files matching a pattern
# 6. file_info - when was this file last modified?
# 7. tree - show me the project structure
# 8. get_disk_usage - how much space is left on this volume?
# 9. directory_disk_usage - which subdirectories consume the most space?
# 10. find_large_files - which files are bigger than a threshold?
# 11. find_duplicate_files - are there identical files lurking around?
# 12. find_stale_files - which files haven't been accessed in a while?
# 13. find_empty_directories - which folders would be cleaned up?
# ===============================================

# Read only annotation hint, because these tools do not modify the file system
READ_ONLY = ToolAnnotations(readOnlyHint=True)

# Home directory for the user
DEFAULT_PATH = str(Path.home())

# Cap the sample list so a broad scan cannot flood the model's context: a
# recursive search of the home directory can match tens of thousands of paths.
# The exact count is reported separately and is never truncated.
SAMPLE_LIMIT = 25


# 1. list_directory - what's in this folder?
@mcp.tool(annotations=READ_ONLY)
async def list_directory(ctx: Context, path: str = DEFAULT_PATH) -> str:
    """List the immediate contents of a directory, one entry per line.

    Non-recursive: shows only what sits directly inside `path`. Each line is
    prefixed with a folder or file emoji. Returns "Directory is empty" when
    there is nothing to list.

    Args:
        path: Absolute directory path to list. Defaults to the home directory.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"list_directory failed: {path} does not exist")
            return path_error("list_directory", path)
        await ctx.info(f"Listing directory: {path}")
        entries = []
        for child in sorted(p.iterdir()):
            prefix = "📁 " if child.is_dir() else "📄 "
            entries.append(f"{prefix}{child.name}")
        return "\n".join(entries) if entries else "Directory is empty"
    except Exception as exc:
        await ctx.error(f"list_directory failed: {type(exc).__name__}: {exc}")
        return unexpected_error("list_directory", path, exc)


# 2. count_files - how many files of each type are in this folder?
@mcp.tool(annotations=READ_ONLY)
async def count_files(ctx: Context, path: str = DEFAULT_PATH) -> dict:
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


# 3. file_names - show me all files with a given extension here
@mcp.tool(annotations=READ_ONLY)
async def file_names(
    ctx: Context, path: str = DEFAULT_PATH, extension: str = ""
) -> list[str]:
    """List file names in a directory, optionally filtered by extension.

    Non-recursive: returns bare names for files directly inside `path`, not
    full paths. Directories are excluded. With no `extension`, every file is
    returned; with one, only files whose suffix matches, compared
    case-insensitively.

    Args:
        path: Absolute directory path to inspect. Defaults to the home directory.
        extension: Extension to filter by, including the dot (e.g. '.py').
            Empty or omitted returns every file name.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"file_names failed: {path} does not exist")
            return path_error("file_names", path)
        await ctx.info(
            f"Listing file names in: {path}"
            + (f" (extension={extension})" if extension else "")
        )
        if extension:
            return [
                f.name
                for f in p.iterdir()
                if f.is_file() and f.suffix.lower() == extension.lower()
            ]
        return [f.name for f in p.iterdir() if f.is_file()]
    except Exception as exc:
        await ctx.error(f"file_names failed: {type(exc).__name__}: {exc}")
        return unexpected_error("file_names", path, exc)


# 4. directory_sizes - what's taking up space?
@mcp.tool(annotations=READ_ONLY)
async def directory_sizes(ctx: Context, path: str = DEFAULT_PATH) -> list[dict]:
    """List the immediate contents of a directory with a size per entry.

    Reports files by size in human-readable form and directories by *file count*,
    not bytes -- a directory entry is `{"files": N}`. For actual byte sizes per
    subdirectory, use `directory_disk_usage`. Because a count ignores file size,
    a folder of many tiny files can outrank a folder holding one large video;
    it measures population, not weight.

    Args:
        path: Absolute directory path to inspect. Defaults to the home directory.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"directory_sizes failed: {path} does not exist")
            return path_error("directory_sizes", path)

        def human_size(nbytes: int) -> str:
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if abs(nbytes) < 1024:
                    return f"{nbytes:.1f} {unit}"
                nbytes /= 1024
            return f"{nbytes:.1f} PB"

        await ctx.info(f"Computing directory sizes in: {path}")
        results = []
        for child in sorted(p.iterdir()):
            if child.is_file():
                results.append(
                    {
                        "name": child.name,
                        "type": "file",
                        "size": human_size(child.stat().st_size),
                    }
                )
            else:
                file_count = sum(1 for _ in child.rglob("*") if _.is_file())
                results.append(
                    {"name": child.name, "type": "directory", "files": file_count}
                )
        return results
    except Exception as exc:
        await ctx.error(f"directory_sizes failed: {type(exc).__name__}: {exc}")
        return unexpected_error("directory_sizes", path, exc)


# 5. search_files - find all files matching a glob pattern
@mcp.tool(annotations=READ_ONLY)
async def search_files(
    ctx: Context, path: str = DEFAULT_PATH, pattern: str = "*"
) -> list[str]:
    """Find entries in a directory matching a glob pattern.

    Depth is controlled entirely by `pattern`, since glob matching is used
    directly: `*.py` matches only in `path` itself, while `**/*.py` also
    matches at every depth below it. Returns both files and directories that
    match. Results are not capped, so a broad pattern over a large tree can
    return a very long list.

    Args:
        path: Absolute directory path to search under.
        pattern: Glob pattern relative to `path` (e.g. '*.py', '**/*.txt').
            Defaults to '*', every entry directly inside `path`.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"search_files failed: {path} does not exist")
            return path_error("search_files", path)
        await ctx.info(f"Searching for '{pattern}' in: {path}")
        return sorted(str(f) for f in p.glob(pattern))
    except Exception as exc:
        await ctx.error(f"search_files failed: {type(exc).__name__}: {exc}")
        return unexpected_error("search_files", path, exc)


# 6. file_info - when was this file last modified?
@mcp.tool(annotations=READ_ONLY)
async def file_info(ctx: Context, path: str = DEFAULT_PATH) -> dict:
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


# 7. tree - show me the project structure
@mcp.tool(annotations=READ_ONLY)
async def tree(ctx: Context, path: str = DEFAULT_PATH, max_depth: int = 3) -> str:
    """Show a directory tree, one entry per line with folder/file markers.

    Recursion stops at `max_depth`. Output is untruncated and unbounded in
    length, so keep `max_depth` small over a large tree -- it is a display
    helper, not a summary. For an idea of how much space something occupies, use
    `directory_disk_usage` instead.

    Args:
        path: Absolute directory path to render.
        max_depth: Levels below `path` to descend. 3 (default) shows children,
            grandchildren, and great-grandchildren.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"tree failed: {path} does not exist")
            return path_error("tree", path)

        await ctx.info(f"Building directory tree for: {path} (max_depth={max_depth})")
        lines: list[str] = []

        def _walk(dir_path: Path, prefix: str, depth: int) -> None:
            if depth >= max_depth:
                return
            children = sorted(dir_path.iterdir())
            for i, child in enumerate(children):
                connector = "└── " if i == len(children) - 1 else "├── "
                icon = "📁 " if child.is_dir() else "📄 "
                lines.append(f"{prefix}{connector}{icon}{child.name}")
                if child.is_dir():
                    extension = "    " if i == len(children) - 1 else "│   "
                    _walk(child, prefix + extension, depth + 1)

        lines.append(f"📁 {p.name}/")
        _walk(p, "", 0)
        return "\n".join(lines)
    except Exception as exc:
        await ctx.error(f"tree failed: {type(exc).__name__}: {exc}")
        return unexpected_error("tree", path, exc)


# 8. get_disk_usage - how much space is left on this volume?
@mcp.tool(annotations=READ_ONLY)
async def get_disk_usage(ctx: Context, path: str = DEFAULT_PATH) -> dict:
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


# 9. directory_disk_usage - which subdirectories consume the most space?
@mcp.tool(annotations=READ_ONLY)
async def directory_disk_usage(
    ctx: Context, path: str = DEFAULT_PATH, top_n: int = 10
) -> list[dict]:
    """Find the largest immediate children of a directory, in bytes.

    Ranks only the direct children of `path`, though each directory's size is
    measured recursively across everything beneath it. So the entry for a
    subdirectory reflects its whole subtree, but the set of candidates is just
    one level deep -- a directory buried three levels down is only reported if
    its parent is among the top results. Sorted largest first.

    Args:
        path: Absolute directory path whose children should be ranked.
        top_n: How many of the largest entries to return. Default 10.
    """
    try:
        p = Path(path)
        if not p.exists():
            await ctx.error(f"directory_disk_usage failed: {path} does not exist")
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
        for child in sorted(p.iterdir()):
            if child.is_file():
                results.append(
                    {
                        "name": child.name,
                        "type": "file",
                        "size_bytes": child.stat().st_size,
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


# 10. find_large_files - which files are bigger than a threshold?
@mcp.tool(annotations=READ_ONLY)
async def find_large_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    min_size_mb: float = 100.0,
    max_results: int = 50,
) -> list[dict]:
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


# 11. find_duplicate_files - are there identical files lurking around?
@mcp.tool(annotations=READ_ONLY)
async def find_duplicate_files(
    ctx: Context, path: str = DEFAULT_PATH, min_size_bytes: int = 1024
) -> list[dict]:
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


# 12. find_stale_files - which files haven't been modified in a while?
@mcp.tool(annotations=READ_ONLY)
async def find_stale_files(
    ctx: Context,
    path: str = DEFAULT_PATH,
    days_unmodified: int = 90,
    max_results: int = 100,
) -> list[dict]:
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


# 13. find_empty_directories - which folders would be cleaned up?
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
