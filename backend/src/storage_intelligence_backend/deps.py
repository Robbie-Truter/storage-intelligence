"""Shared FastAPI dependencies."""

from fastapi import HTTPException, Request, status

from .mcp.manager import StorageMCPClient


def get_mcp_manager(request: Request) -> StorageMCPClient:
    """Return the ready MCP client, or fail with 503.

    Overridable in tests via ``app.dependency_overrides``.
    """
    manager: StorageMCPClient | None = getattr(request.app.state, "mcp", None)
    if manager is None or not manager.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP server is not available",
        )
    return manager
