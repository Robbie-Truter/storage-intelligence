import shutil
from pathlib import Path
import hashlib

from fastmcp import Context

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
# ===============================================

# Home directory for the user
DEFAULT_PATH = str(Path.home())


# 1. list_directory - what's in this folder?
@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
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


