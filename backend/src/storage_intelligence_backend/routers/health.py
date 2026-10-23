"""Health endpoints.

``/health`` is a cheap liveness check with no MCP dependency. ``/health/ready``
reports readiness and returns 503 when the MCP server is unavailable, so a
temporarily dead MCP does not look like a dead backend.
"""

from fastapi import APIRouter, Request, Response, status

from ..schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report that the FastAPI process is up."""
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Report whether the service can fulfil MCP-dependent requests."""
    manager = getattr(request.app.state, "mcp", None)
    if manager is None or not getattr(manager, "is_ready", False):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="unavailable",
            mcp="unavailable",
            detail="MCP server is not connected",
        )
    return ReadinessResponse(status="ok", mcp="ok", tool_count=manager.tool_count)
