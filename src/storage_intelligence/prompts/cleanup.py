from pathlib import Path

from storage_intelligence.core import mcp

# ===============================================
# List of storage cleanup prompts, in the order they are implemented:
# ===============================================
# 1. prepare_cleanup - what could be cleaned up in this folder?
# 2. remove_junk - can I get rid of these junk files and build artifacts?
# 3. remove_empty_dirs - can I trash these empty folders?
# ===============================================

# Prompts for the cleanup tools. Every destructive step is two-phase: the
# model must call trash_path with confirm=False first, show the preview to
# the user, and only re-call it with confirm=True after an explicit yes.

HOME_PATH = str(Path.home())


@mcp.prompt()
def prepare_cleanup(path: str = HOME_PATH) -> str:
    """Review junk, duplicates, stale files and empty directories."""
    return (
        f"Review `{path}` for things that could be cleaned up, grouped by "
        "type and size, and propose a cleanup plan for my approval.\n\n"
        "Steps:\n"
        f"1. Call `find_junk_files` with path `{path}` to inventory temporary "
        "files and build-artifact directories (node_modules, __pycache__, "
        "dist, build, target).\n"
        f"2. Call `find_duplicate_files` with path `{path}` to group "
        "byte-identical files.\n"
        f"3. Call `find_stale_files` with path `{path}` and "
        "days_unmodified=365 to surface files untouched for over a year.\n"
        f"4. Call `find_empty_directories` with path `{path}` to find folders "
        "with nothing left in them.\n"
        "5. Group the candidates by type (junk, duplicates, stale, empty "
        "directories) and within each type by size, largest first. Use "
        "`directory_disk_usage` on artifact directories when you need their "
        "footprint.\n\n"
        "Finish with a proposed cleanup table: type, candidate count, "
        "estimated reclaimable space, and risk level, then ask me which "
        "category I want to clean up. Do not delete anything."
    )


@mcp.prompt()
def remove_junk(path: str = HOME_PATH) -> str:
    """Get rid of junk files and build artifacts, after preview."""
    return (
        f"Clean up the junk files and build artifacts in `{path}`.\n\n"
        "Steps:\n"
        f"1. Call `find_junk_files` with path `{path}` to list temporary "
        "files and build-artifact directories.\n"
        "2. Call `directory_disk_usage` on any reported build-artifact "
        "directories so I know how much space each one holds.\n"
        "3. Show me the candidates grouped by type (files by extension, "
        "then artifact directories) with counts and sizes.\n"
        "4. Call `trash_path` with the candidate paths and confirm=False to "
        "get a dry-run preview, and show me that preview.\n"
        "5. Ask me explicitly whether to proceed. Only if I say yes, call "
        "`trash_path` again with the same paths and confirm=True. If I "
        "change the list, restart from step 4 with the new list.\n\n"
        "Never call trash_path with confirm=True before I have confirmed. "
        "Report what was trashed and what failed afterwards."
    )


@mcp.prompt()
def remove_empty_dirs(path: str = HOME_PATH) -> str:
    """Trash empty directories, after preview."""
    return (
        f"Trash the empty directories under `{path}`.\n\n"
        "Steps:\n"
        f"1. Call `find_empty_directories` with path `{path}` to get the "
        "empty folders, deepest first.\n"
        "2. Show me the list with a count and note anything that looks "
        "suspicious, e.g. paths from skipped or unreadable directories.\n"
        "3. Call `trash_path` with the paths and confirm=False to get a "
        "dry-run preview, and show me that preview. Keep the deepest-first "
        "order from the tool.\n"
        "4. Ask me explicitly whether to proceed. Only if I say yes, call "
        "`trash_path` again with the same paths and confirm=True. If I "
        "change the list, restart from step 3 with the new list.\n\n"
        "Never call trash_path with confirm=True before I have confirmed. "
        "Report what was trashed and what failed afterwards."
    )
