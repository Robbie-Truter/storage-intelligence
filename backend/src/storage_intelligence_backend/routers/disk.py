"""Deterministic disk endpoints (no LLM).

Backed directly by the MCP client via ``call_tool``; all endpoints are
read-only.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from ..deps import get_mcp_manager
from ..mcp.manager import StorageMCPClient
from ..schemas import (
    CountFilesResponse,
    DirectoryDiskUsageResponse,
    DiskUsageResponse,
    ExploreDirectoryResponse,
    FileInfoResponse,
    ReclaimableCategory,
    ReclaimableStorageResponse,
)

router = APIRouter(prefix="/disk", tags=["disk"])
SAMPLE_LIMIT = 5


@router.get("/usage", response_model=DiskUsageResponse)
async def disk_usage(
    manager: StorageMCPClient = Depends(get_mcp_manager),
    path: str | None = None,
) -> DiskUsageResponse:
    """Report space for the whole volume containing ``path``.

    Omits the argument when no path is given so the MCP tool applies its own
    default (home directory).
    """
    arguments = {} if path is None else {"path": path}
    result = await manager.call_tool("disk_usage", arguments)
    return DiskUsageResponse(**result)


@router.get("/directory", response_model=DirectoryDiskUsageResponse)
async def directory_disk_usage(
    manager: StorageMCPClient = Depends(get_mcp_manager),
    path: str | None = None,
    top_n: int = 10,
) -> DirectoryDiskUsageResponse:
    """Rank the immediate children of ``path`` by size, largest first.

    A directory's size covers its whole subtree, but only direct children are
    candidates. Omits the argument when no path is given so the MCP tool
    applies its own default (home directory).
    """
    arguments: dict[str, Any] = {"top_n": top_n}
    if path is not None:
        arguments["path"] = path
    result = await manager.call_tool("directory_disk_usage", arguments)
    return DirectoryDiskUsageResponse(**result)


@router.get("/explore", response_model=ExploreDirectoryResponse)
async def explore_directory(
    manager: StorageMCPClient = Depends(get_mcp_manager),
    path: str | None = None,
    pattern: str = "",
    search: str = "",
    kind: Literal["all", "files", "dirs"] = "all",
    recursive: bool = False,
    max_results: int = 100,
) -> ExploreDirectoryResponse:
    """List the entries inside ``path``, one structured record each.

    Non-recursive (default) lists only direct children; ``recursive`` walks the
    whole tree below ``path``. ``pattern`` and ``search`` filter on each entry's
    own name, ``kind`` narrows to files or directories, and ``max_results`` caps
    the list with ``truncated`` reporting whether more matches existed. Omits the
    argument when no path is given so the MCP tool applies its own default (home
    directory).
    """
    arguments: dict[str, Any] = {
        "pattern": pattern,
        "search": search,
        "kind": kind,
        "recursive": recursive,
        "max_results": max_results,
    }
    if path is not None:
        arguments["path"] = path

    result = await manager.call_tool("explore_directory", arguments)
    return ExploreDirectoryResponse(**result)


@router.get("/count", response_model=CountFilesResponse)
async def count_files(
    manager: StorageMCPClient = Depends(get_mcp_manager),
    path: str | None = None,
) -> CountFilesResponse:
    """Count the files directly inside ``path``, grouped by extension.

    Non-recursive: only files immediately inside ``path`` are counted and
    subdirectory contents are ignored. Extensions are lowercased, so ``.PY`` and
    ``.py`` group together, and files without an extension group under
    ``"(no extension)"``. Omits the argument when no path is given so the MCP
    tool applies its own default (home directory).
    """
    arguments = {} if path is None else {"path": path}
    result = await manager.call_tool("count_files", arguments)
    return CountFilesResponse(**result)


@router.get("/info", response_model=FileInfoResponse)
async def file_info(
    manager: StorageMCPClient = Depends(get_mcp_manager),
    path: str | None = None,
) -> FileInfoResponse:
    """Report the disk info for the whole volume containing ``path``.

    Omits the argument when no path is given so the MCP tool applies its own
    default (home directory).
    """
    arguments = {} if path is None else {"path": path}
    result = await manager.call_tool("file_info", arguments)
    return FileInfoResponse(**result)


@router.get("/reclaimable", response_model=ReclaimableStorageResponse)
async def reclaimable_storage(
    manager: StorageMCPClient = Depends(get_mcp_manager),
    path: str | None = None,
    min_duplicate_bytes: int = Query(1024, ge=1),
    stale_days: int = Query(365, ge=1),
    max_stale_results: int = Query(100, ge=1, le=500),
) -> ReclaimableStorageResponse:
    """Aggregate heuristic cleanup candidates for ``path``.

    Four read-only MCP scans are combined: duplicate files, junk files,
    top-level empty directories, and stale files as the "other" category.
    Byte figures are upper-bound estimates; categories can overlap and no
    files are changed. Omits ``path`` when not given so every tool applies
    its own home-directory default.
    """
    arguments: dict[str, Any] = {} if path is None else {"path": path}

    duplicate_groups = await manager.call_tool(
        "find_duplicate_files",
        {**arguments, "min_size_bytes": min_duplicate_bytes},
    )
    junk = await manager.call_tool("find_junk_files", arguments)
    empty = await manager.call_tool(
        "find_empty_directories", {**arguments, "recursive": False}
    )
    stale = await manager.call_tool(
        "find_stale_files",
        {
            **arguments,
            "days_unmodified": stale_days,
            "max_results": max_stale_results,
        },
    )

    duplicate_paths = [file_path for group in duplicate_groups for file_path in group["files"]]
    duplicate_copies = sum(len(group["files"]) - 1 for group in duplicate_groups)
    duplicate_bytes = sum(
        group["size_bytes"] * (len(group["files"]) - 1) for group in duplicate_groups
    )
    junk_paths = [*junk["sample"], *junk["directories"]]
    stale_paths = [entry["path"] for entry in stale]

    categories = [
        ReclaimableCategory(
            category="duplicates",
            label="Duplicate files",
            estimated_bytes=duplicate_bytes,
            item_count=duplicate_copies,
            group_count=len(duplicate_groups),
            sample_paths=duplicate_paths[:SAMPLE_LIMIT],
            truncated=len(duplicate_paths) > SAMPLE_LIMIT,
            note="Keeps one copy per group; identical files are not automatically safe.",
        ),
        ReclaimableCategory(
            category="junk",
            label="Junk files",
            estimated_bytes=int(junk.get("total_bytes", 0)),
            item_count=int(junk["total_files"]),
            group_count=len(junk["directories"]),
            sample_paths=junk_paths[:SAMPLE_LIMIT],
            truncated=bool(junk["truncated"]) or len(junk_paths) > SAMPLE_LIMIT,
            note="Junk suffixes and build folders; build folder contents are not measured.",
        ),
        ReclaimableCategory(
            category="empty_directories",
            label="Empty directories",
            estimated_bytes=0,
            item_count=int(empty["total_empty_directories"]),
            group_count=0,
            sample_paths=empty["sample"][:SAMPLE_LIMIT],
            truncated=bool(empty["truncated"]),
            note="Top-level empty folders free directory entries, not meaningful bytes.",
        ),
        ReclaimableCategory(
            category="other",
            label=f"Stale files ({stale_days}+ days)",
            estimated_bytes=sum(int(entry["size_bytes"]) for entry in stale),
            item_count=len(stale),
            group_count=0,
            sample_paths=stale_paths[:SAMPLE_LIMIT],
            truncated=len(stale) >= max_stale_results,
            note="Files unmodified for the threshold period; review before removal.",
        ),
    ]

    return ReclaimableStorageResponse(
        path=str(junk["path"]),
        categories=categories,
        total_estimated_bytes=sum(category.estimated_bytes for category in categories),
        message="Heuristic estimates only; categories can overlap. No files were changed.",
    )
