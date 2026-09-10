from storage_intelligence.core import mcp
from pathlib import Path

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
# ===============================================

# list_directory - what's in this folder?
@mcp.tool()
def list_directory(path: str) -> str:
    """List the contents of a directory with type indicators."""
    p = Path(path)
    if not p.exists():
        return f"Error: {path} does not exist"
    entries = []
    for child in sorted(p.iterdir()):
        prefix = "📁 " if child.is_dir() else "📄 "
        entries.append(f"{prefix}{child.name}")
    return "\n".join(entries) if entries else "Directory is empty"

# count_files - how many files of each type are in this folder?
@mcp.tool()
def count_files(path: str) -> dict:
    """Count files and directories in a directory, broken down by type."""
    p = Path(path)
    if not p.exists():
        return {"error": f"{path} does not exist"}
    total = 0
    by_extension: dict[str, int] = {}
    for child in p.iterdir():
        if child.is_file():
            total += 1
            ext = child.suffix.lower() or "(no extension)"
            by_extension[ext] = by_extension.get(ext, 0) + 1
    return {"total_files": total, "by_extension": dict(sorted(by_extension.items(), key=lambda x: -x[1]))}


# file_names - show me all files with a given extension here
@mcp.tool()
def file_names(path: str, extension: str = "") -> list[str]:
    """List file names in a directory, optionally filtered by extension (e.g. '.py')."""
    p = Path(path)
    if not p.exists():
        return [f"Error: {path} does not exist"]
    if extension:
        return [f.name for f in p.iterdir() if f.is_file() and f.suffix.lower() == extension.lower()]
    return [f.name for f in p.iterdir() if f.is_file()]


# directory_sizes - what's taking up space?
@mcp.tool()
def directory_sizes(path: str) -> list[dict]:
    """List top-level items in a directory with their sizes in human-readable format."""
    p = Path(path)
    if not p.exists():
        return [{"error": f"{path} does not exist"}]

    def human_size(nbytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(nbytes) < 1024:
                return f"{nbytes:.1f} {unit}"
            nbytes /= 1024
        return f"{nbytes:.1f} PB"

    results = []
    for child in sorted(p.iterdir()):
        if child.is_file():
            results.append({"name": child.name, "type": "file", "size": human_size(child.stat().st_size)})
        else:
            file_count = sum(1 for _ in child.rglob("*") if _.is_file())
            results.append({"name": child.name, "type": "directory", "files": file_count})
    return results


# search_files - find all files matching a glob pattern
@mcp.tool()
def search_files(path: str, pattern: str) -> list[str]:
    """Search for files matching a glob pattern (e.g. '*.py', '**/*.txt')."""
    p = Path(path)
    if not p.exists():
        return [f"Error: {path} does not exist"]
    return sorted(str(f) for f in p.glob(pattern))


# file_info - when was this file last modified?
@mcp.tool()
def file_info(path: str) -> dict:
    """Get metadata about a file: size, created/modified times, type."""
    p = Path(path)
    if not p.exists():
        return {"error": f"{path} does not exist"}
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


# tree - show me the project structure
@mcp.tool()
def tree(path: str, max_depth: int = 3) -> str:
    """Show a recursive directory tree up to max_depth levels."""
    p = Path(path)
    if not p.exists():
        return f"Error: {path} does not exist"

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
