"""Deterministic disk endpoints (no LLM).

Backed directly by the MCP client via ``call_tool``; all endpoints are
read-only.
"""

from fastapi import APIRouter, Depends

from ..deps import get_mcp_manager
from ..mcp.manager import StorageMCPClient
from ..schemas import DiskUsageResponse

router = APIRouter(prefix="/disk", tags=["disk"])


@router.get("/usage", response_model=DiskUsageResponse)
async def get_disk_usage(
    manager: StorageMCPClient = Depends(get_mcp_manager),
    path: str | None = None,
) -> DiskUsageResponse:
    """Report space for the whole volume containing ``path``.

    Omits the argument when no path is given so the MCP tool applies its own
    default (home directory).
    """
    arguments = {} if path is None else {"path": path}
    result = await manager.call_tool("get_disk_usage", arguments)
    return DiskUsageResponse(**result)


@router.get("/directory")
async def get_directory_usage() -> str:
    return "not yet implemented"


@router.get("/explore")
async def explore_directory() -> str:
    return "not yet implemented"


@router.get("/scan")
async def scan_disk() -> str:
    return "not yet implemented"
