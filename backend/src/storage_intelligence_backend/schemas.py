"""Pydantic request/response models shared across routers.

Only the health payloads and the disk usage payload are defined for now; the
agent and cleanup models are added alongside their endpoints in later
milestones.
"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str


class DiskUsageResponse(BaseModel):
    """Result of ``disk_usage``.

    Figures describe the whole volume containing ``path``, not ``path`` itself.
    """

    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float


class DirectoryUsageEntry(BaseModel):
    """One child in the ``directory_disk_usage`` ranking."""

    name: str
    type: Literal["file", "directory"]
    size_bytes: int


class DirectoryDiskUsageResponse(BaseModel):
    """Result of ``directory_disk_usage``.

    The largest immediate children of ``path``, largest first.
    """

    path: str
    entries: list[DirectoryUsageEntry]


class ReadinessResponse(BaseModel):
    """Readiness payload, including MCP availability."""

    status: str
    mcp: str
    tool_count: int = 0
    detail: str | None = None
