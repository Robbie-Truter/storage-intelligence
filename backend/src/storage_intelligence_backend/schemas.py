"""Pydantic request/response models shared across routers.

The health payloads, the deterministic disk payloads (usage, directory, explore,
count, info), the agent payloads, and the cleanup payloads are defined here.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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


class ExploreDirectoryEntry(BaseModel):
    """One entry from the ``explore_directory`` listing, in scan order."""

    name: str
    path: str
    type: str


class ExploreDirectoryResponse(BaseModel):
    """Result of ``explore_directory``.

    ``entries`` lists the matching children of ``path``; ``truncated`` reports
    whether scanning stopped at ``max_results`` with more matches unseen.
    """

    path: str
    entries: list[ExploreDirectoryEntry]
    truncated: bool


class CountFilesResponse(BaseModel):
    """Result of ``count_files``.

    ``by_extension`` counts the files directly inside ``path`` per lowercased
    extension, largest count first; unextended files group under
    ``"(no extension)"``.
    """

    path: str
    total_files: int
    by_extension: dict[str, int]


class FileInfoResponse(BaseModel):
    """Result of ``file_info``."""

    name: str
    path: str
    type: Literal["file", "directory"]
    size_bytes: int
    modified: float
    created: float
    extension: str


class ReadinessResponse(BaseModel):
    """Readiness payload, including MCP availability."""

    status: str
    mcp: str
    tool_count: int = 0
    detail: str | None = None


class AgentModelOption(BaseModel):
    """One model the agent can be configured with.

    ``provider`` is the ``init_chat_model`` provider prefix, ``model_name`` the
    provider-specific model, and ``mode`` is ``cloud`` or ``local``.
    """

    id: str
    label: str
    provider: str
    model_name: str
    mode: str


class AgentAnalyzeRequest(BaseModel):
    """Request body of ``POST /api/agent/analyze``.

    ``model`` is the ``id`` of a ``GET /api/agent/models`` entry and is
    validated against that catalogue. ``path`` is the directory the agent
    investigates (defaults to the home directory when omitted); ``question`` is
    optional and defaults to a general "what takes the most space" analysis.
    """

    model: str
    path: str | None = None
    question: str | None = None


class AgentToolCall(BaseModel):
    """One tool call the agent made.

    ``args`` are the arguments the model called the tool with, ``status`` is
    ``ok`` or ``error`` (a tool that reported an error is recorded as failed -
    the agent carried on and answered anyway), and ``result`` is the tool's
    structured answer.
    """

    name: str
    args: dict[str, Any]
    status: Literal["ok", "error"]
    result: Any = None


class AgentAnalyzeResponse(BaseModel):
    """Result of an agent analysis run.

    ``summary`` is the agent's final answer; ``tool_calls`` lists the tools it
    used, in the order it called them.
    """

    summary: str
    tool_calls: list[AgentToolCall]


class CleanupExecuteRequest(BaseModel):
    """Request body of ``POST /api/cleanup/execute``.

    ``paths`` are the files/directories the frontend selected; they are handed
    to the MCP ``trash_path`` tool unchanged. Nothing else is accepted - there
    is no ``preview_id``, no preview store, and no client-supplied ``confirm``:
    extra keys are rejected so a client cannot smuggle one in.
    """

    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(min_length=1)


class CleanupFailure(BaseModel):
    """One path that could not be sent to the trash.

    ``error`` is the reason the tool reported, e.g. ``"OSError: ..."``.
    """

    path: str
    error: str


class CleanupExecuteResponse(BaseModel):
    """Outcome of a cleanup execution run.

    Mirrors the executed payload of the MCP ``trash_path`` tool: ``mode`` is
    ``"executed"``, ``paths`` are the targets that existed (deepest path
    first, deduplicated by the tool, so the order may differ from the
    submitted list), ``deleted`` the ones that went to the trash, ``failed``
    the ones that raised, and ``missing_paths`` the submitted targets that no
    longer existed. ``total_valid_paths`` counts the targets that existed.
    """

    mode: str
    paths: list[str]
    deleted: list[str]
    failed: list[CleanupFailure]
    missing_paths: list[str]
    total_valid_paths: int
