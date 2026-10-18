"""Deterministic disk endpoints (no LLM).

Backed directly by the MCP client via ``call_tool``; all endpoints are
read-only.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends

from ..deps import get_mcp_manager
from ..mcp.manager import StorageMCPClient
from ..schemas import (
    CountFilesResponse,
    DirectoryDiskUsageResponse,
    DiskUsageResponse,
    ExploreDirectoryResponse,
    FileInfoResponse,
)

router = APIRouter(prefix="/disk", tags=["disk"])


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
