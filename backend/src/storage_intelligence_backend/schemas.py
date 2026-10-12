"""Pydantic request/response models shared across routers.

Only the health payloads are defined for now; disk, agent, and cleanup models
are added alongside their endpoints in later milestones.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str


class ReadinessResponse(BaseModel):
    """Readiness payload, including MCP availability."""

    status: str
    mcp: str
    tool_count: int = 0
    detail: str | None = None
