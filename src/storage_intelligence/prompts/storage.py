from pathlib import Path

from storage_intelligence.core import mcp

# ===============================================
# List of storage analysis prompts, in the order they are implemented:
# ===============================================
# 1. analyze_storage - what is taking up space in this directory?
# 2. analyze_home_storage - what is taking up space on my internal drive?
# 3. find_old_files - which files haven't been modified in a while?
# 4. find_duplicates - am I wasting space on identical copies?
# 5. clean_junk - which junk files and build artifacts clutter this folder?
# 6. free_up_space - where are the biggest wins for reclaiming disk space?
# ===============================================

# Prompts for the read-only storage analysis tools. Each returns plain
# instructions that steer the model through the most common workflows; the
# tools themselves supply the home directory when `path` is omitted.

HOME_PATH = str(Path.home())


@mcp.prompt()
def analyze_storage(path: str = HOME_PATH) -> str:
    """Analyze disk usage for a directory and its volume."""
    return (
        f"Analyze the storage at `{path}` and explain what is taking up space.\n\n"
        "Steps:\n"
        f"1. Call `get_disk_usage` with path `{path}` to report the volume's "
        "total, used, and free space plus usage percent.\n"
        f"2. Call `directory_disk_usage` with path `{path}` (top_n=10) to rank "
        "the immediate children by size.\n"
        "3. For anything unexpectedly large, repeat `directory_disk_usage` on "
        "that child to see what sits inside it.\n"
        "4. Use `count_files` or `explore_directory` to characterise the "
        "contents when a size number alone is not self-explanatory.\n\n"
        "Finish with the top 3 space consumers, their sizes in human-readable "
        "form, what each one actually is, and whether it looks safe to review "
        "later. This is an analysis pass only: do not delete or modify "
        "anything."
    )


@mcp.prompt()
def analyze_home_storage() -> str:
    """Analyze disk usage of the home directory (tools default to home)."""
    return (
        "Analyze my storage and explain what is taking up space on my "
        "internal drive.\n\n"
        "Steps:\n"
        "1. Call `get_disk_usage` with no path argument to report total, "
        "used, and free space for the volume holding my home directory.\n"
        "2. Call `directory_disk_usage` with no path argument (top_n=10) to "
        "rank the immediate children of my home directory by size.\n"
        "3. For anything unexpectedly large, repeat `directory_disk_usage` on "
        "that child to see what sits inside it.\n"
        "4. Use `count_files` or `explore_directory` to characterise the "
        "contents when a size number alone is not self-explanatory.\n\n"
        "Finish with the top 3 space consumers, their sizes in human-readable "
        "form, what each one actually is, and whether it looks safe to review "
        "later. This is an analysis pass only: do not delete or modify "
        "anything."
    )


@mcp.prompt()
def find_old_files(path: str = HOME_PATH, days_unmodified: int = 90) -> str:
    """Find files that have not been modified in a while."""
    return (
        f"Find the old files under `{path}` that I have not touched in "
        f"{days_unmodified} days and help me decide what is worth reviewing.\n\n"
        "Steps:\n"
        f"1. Call `find_stale_files` with path `{path}` and "
        f"days_unmodified={days_unmodified} (max_results=50) to get the least "
        "recently modified files first.\n"
        "2. Group the results by parent folder so patterns are visible, e.g. "
        "old downloads, forgotten archives, abandoned project directories.\n"
        "3. Call `file_info` on the few largest or most suspicious paths to "
        "confirm size and creation time before drawing conclusions.\n\n"
        "Finish with a shortlist of the most reclaimable candidates, grouped "
        "by folder, with age and size for each. Remind me that modification "
        "time reflects content changes, not when I last opened a file. This "
        "is an analysis pass only: do not delete or modify anything."
    )


@mcp.prompt()
def find_duplicates(path: str = HOME_PATH) -> str:
    """Look for byte-identical files wasting space."""
    return (
        f"Check whether `{path}` contains duplicate files that are wasting "
        "space.\n\n"
        "Steps:\n"
        f"1. Call `find_duplicate_files` with path `{path}` (default "
        "min_size_bytes=1024) to get groups of byte-identical files, largest "
        "group size first.\n"
        "2. Estimate the reclaimable space as (copies - 1) x size for each "
        "group and total it up.\n"
        "3. If the scan reports nothing, note that files below 1 KB are "
        "skipped by default before concluding there are no duplicates.\n\n"
        "Finish with the duplicate groups, where each copy lives, how much "
        "space could be reclaimed, and the trade-offs of keeping the oldest "
        "versus the newest copy. This is an analysis pass only: do not delete "
        "or modify anything."
    )


@mcp.prompt()
def clean_junk(path: str = HOME_PATH) -> str:
    """Inventory junk files and empty directories in a folder."""
    return (
        f"Inventory the junk files and dead weight in `{path}` so I know what "
        "could be cleaned.\n\n"
        "Steps:\n"
        f"1. Call `find_junk_files` with path `{path}` to count temporary "
        "files (.log, .tmp, .bak, .old, .swp, object files, ...) and "
        "build-artifact directories (node_modules, __pycache__, dist, build, "
        "target).\n"
        f"2. Call `find_empty_directories` with path `{path}` to find folders "
        "with nothing left in them.\n"
        "3. Use `directory_disk_usage` on the reported build-artifact "
        "directories to quantify how much space they occupy.\n\n"
        "Finish with a cleanup report: junk counts by extension, the space "
        "held by build artifacts, and the number of empty directories, each "
        "clearly labelled as a candidate for review. This is an inventory "
        "pass only: do not delete or modify anything."
    )


@mcp.prompt()
def free_up_space(path: str = HOME_PATH) -> str:
    """Produce a ranked plan for reclaiming disk space."""
    return (
        f"I want to free up disk space starting from `{path}`. Build me a "
        "ranked list of the biggest wins, biggest and safest first.\n\n"
        "Steps:\n"
        f"1. Call `get_disk_usage` with path `{path}` to establish how much "
        "space is free on the volume.\n"
        f"2. Call `directory_disk_usage` with path `{path}` (top_n=10) to "
        "find which immediate children dominate.\n"
        f"3. Call `find_large_files` with path `{path}` (min_size_mb=500) for "
        "the individual heavyweight files.\n"
        f"4. Call `find_junk_files` and `find_duplicate_files` on `{path}` "
        "for reclaimable clutter and identical copies.\n"
        f"5. Call `find_stale_files` with path `{path}` and "
        "days_unmodified=365 to surface content nobody has changed in a year.\n\n"
        "Finish with a ranked table of opportunities: category, estimated "
        "reclaimable space, risk level, and what I should look at first. "
        "Every row must be something I can review before acting. This is an "
        "analysis pass only: do not delete or modify anything."
    )
