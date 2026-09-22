import hashlib
import shutil
import time
from pathlib import Path

from fastmcp import Context

from mcp.types import ToolAnnotations

from storage_intelligence.core import mcp
from storage_intelligence.utils import path_error, unexpected_error

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
# ===============================================

# Read only annotation hint, because these tools do not modify the file system
READ_ONLY = ToolAnnotations(readOnlyHint=True)

# Home directory for the user
DEFAULT_PATH = str(Path.home())


# 1. list_directory - what's in this folder?
@mcp.tool(annotations=READ_ONLY)
async def list_directory(ctx: Context, path: str = DEFAULT_PATH) -> str:
    """List the contents of a directory with type indicators."""
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
    """Count files and directories in a directory, broken down by type."""
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
    """List file names in a directory, optionally filtered by extension (e.g. '.py')."""
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
    """List top-level items in a directory with their sizes in human-readable format."""
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
    """Search for files matching a glob pattern (e.g. '*.py', '**/*.txt')."""
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
    """Get metadata about a file: size, created/modified times, type."""
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
    """Show a recursive directory tree up to max_depth levels."""
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
    """Get total, used, and free disk space for the volume containing path."""
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
    """Calculate top items in path sorted by actual disk space consumed (bytes)."""
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
    """Find all files in path larger than min_size_mb."""
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
    """Find candidate duplicate files grouped by content hash."""
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
    """Find files that have not been modified for more than days_unmodified."""
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
