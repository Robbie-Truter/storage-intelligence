"""Deterministic disk endpoints (no LLM).

Backed directly by the MCP client via ``call_tool``; all endpoints are
read-only.
"""

from typing import Any

from fastapi import APIRouter, Depends

from ..deps import get_mcp_manager
from ..mcp.manager import StorageMCPClient
from ..schemas import DirectoryDiskUsageResponse, DiskUsageResponse

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


@router.get("/explore")
async def explore_directory() -> str:
    return "not yet implemented"


@router.get("/scan")
async def scan_disk() -> str:
    return "not yet implemented"
