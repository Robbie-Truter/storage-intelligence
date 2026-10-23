"""Cleanup execution endpoint - the only mutating route.

The frontend owns the selection: it submits the paths the user picked, and this
endpoint forwards them to the MCP ``trash_path`` tool with ``confirm=True``,
unchanged, relying on the safeguards the MCP tool already has. There is no
preview store, no ``preview_id``, no fingerprint revalidation, and no
client-supplied ``confirm`` in v1 - the request body carries the paths and
nothing else.

Preview is not an HTTP concern in v1: it happens through the MCP server's
``preview_trash`` tool, reached by the agent.
"""

from fastapi import APIRouter, Depends

from ..deps import get_mcp_manager
from ..mcp.manager import StorageMCPClient
from ..schemas import CleanupExecuteRequest, CleanupExecuteResponse

router = APIRouter(prefix="/cleanup", tags=["cleanup"])


@router.post("/execute", response_model=CleanupExecuteResponse)
async def execute_cleanup(
    request: CleanupExecuteRequest,
    manager: StorageMCPClient = Depends(get_mcp_manager),
) -> CleanupExecuteResponse:
    """Send the selected paths to the trash via the MCP ``trash_path`` tool.

    The submitted paths are forwarded verbatim: no re-ordering, no dedup, no
    existence pre-check, and no extra validation. The MCP tool deduplicates,
    orders its targets deepest path first, and reports what it found, so the
    returned ``paths`` may differ in order and content from the submitted
    list - ``deleted``, ``failed``, and ``missing_paths`` are the outcome.

    Status codes:
        200: the tool ran. ``deleted`` lists the paths that went to the trash,
            ``failed`` the ones that raised, and ``missing_paths`` the
            submitted targets that no longer existed. A stale path inside a
            mixed batch is a warning on a 200, not an error.
        400: every submitted path was missing. The MCP tool raises, and the
            global ``MCPToolError`` handler turns it into
            ``{"detail": {"tool": "trash_path", "message": "Path not found: ..."}}``.
        422: the body was not ``{"paths": [...]}`` with at least one path.
        503: the MCP server is unavailable - the manager dependency, or the
            global ``MCPUnavailable`` handler when the connection breaks.
    """
    result = await manager.call_tool(
        "trash_path",
        {"paths": request.paths, "confirm": True},
    )
    return CleanupExecuteResponse(**result)
