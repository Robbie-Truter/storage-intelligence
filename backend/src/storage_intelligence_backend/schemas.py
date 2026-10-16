"""Pydantic request/response models shared across routers.

Only the health payloads and the disk usage payload are defined for now; the
agent and cleanup models are added alongside their endpoints in later
milestones.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str


class DiskUsageResponse(BaseModel):
    """Result of ``get_disk_usage``.

    Figures describe the whole volume containing ``path``, not ``path`` itself.
    """

    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float


class ReadinessResponse(BaseModel):
    """Readiness payload, including MCP availability."""

    status: str
    mcp: str
    tool_count: int = 0
    detail: str | None = None
