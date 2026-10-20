"""Read-only LangChain agent over an explicit allowlist of MCP tools.

The tool catalogue is composed here rather than taken straight from MCP: the
agent sees the ten read-only MCP tools plus the backend-authored
``preview_trash`` wrapper, and never the raw ``trash_path`` tool. The agent
itself (``build_agent`` / ``run_readonly_analysis``) is built in a later
milestone.
"""

from collections.abc import Sequence
from typing import Any, Protocol

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from ..mcp.errors import MCPToolError
from ..mcp.manager import READONLY_TOOL_ALLOWLIST


class MCPToolSource(Protocol):
    """The slice of the MCP manager the agent tool map is built from."""

    @property
    def langchain_tools(self) -> dict[str, BaseTool]:
        """Allowlisted LangChain tools exposed by the manager."""
        ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool and return its structured content."""
        ...


class PreviewTrashInput(BaseModel):
    """Arguments for ``preview_trash``.

    Deliberately ``paths`` only: there is no ``confirm`` parameter, so a model
    cannot ask this tool to execute a deletion.
    """

    paths: list[str] = Field(
        description=(
            "Candidate files/directories to preview. Only paths the user may "
            "want to trash; this tool never deletes anything."
        )
    )


def _normalize_preview(payload: Any) -> dict[str, Any]:
    """Turn the MCP ``trash_path`` preview payload into candidate metadata.

    Anything that is not a preview payload is an error, not a silent pass-
    through: this tool's contract is that nothing was deleted.
    """
    if not isinstance(payload, dict):
        raise MCPToolError(
            "preview_trash", "MCP trash_path returned no structured preview"
        )
    mode = payload.get("mode")
    if mode != "preview":
        raise MCPToolError(
            "preview_trash", f"expected a preview payload, got mode={mode!r}"
        )
    return {
        "mode": "preview",
        "candidates": list(payload.get("paths") or []),
        "missing_paths": list(payload.get("missing_paths") or []),
        "total_valid_paths": int(payload.get("total_valid_paths") or 0),
        "message": str(payload.get("message") or ""),
    }


def build_preview_trash_tool(manager: MCPToolSource) -> BaseTool:
    """Build the backend-authored ``preview_trash(paths)`` tool.

    The only cleanup surface the agent gets: it forwards the given paths to MCP
    ``trash_path`` with ``confirm`` hardcoded to ``False``, so the MCP server
    answers with a dry-run preview and nothing is ever trashed. The exposed
    signature is ``paths`` only — ``confirm`` cannot be supplied by the caller.
    """

    async def preview_trash(paths: list[str]) -> dict[str, Any]:
        """Preview which paths trash_path would delete, without deleting them.

        Returns the candidate paths plus metadata (missing paths, counts, and
        the server's message) for the user to review. Deletion is a separate,
        explicitly confirmed step owned by the frontend — never this tool.
        """
        payload = await manager.call_tool(
            "trash_path",
            {"paths": paths, "confirm": False},
        )
        return _normalize_preview(payload)

    return StructuredTool(
        name="preview_trash",
        description=(
            "Dry-run preview of trashing files or directories: shows which of "
            "the given paths exist and would be sent to trash. Never deletes "
            "anything. Use it to gather candidates, then let the user select "
            "what to actually delete."
        ),
        args_schema=PreviewTrashInput,
        coroutine=preview_trash,
    )


def build_agent_tool_map(manager: MCPToolSource) -> dict[str, BaseTool]:
    """Compose the agent's tool map: the 10 allowlisted MCP tools + preview.

    The allowlist filter is applied here as well as in the manager, so a tool
    outside ``READONLY_TOOL_ALLOWLIST`` (``trash_path`` above all) can never
    reach the agent even if the manager's map is widened later.
    """
    tools = {
        name: tool
        for name, tool in manager.langchain_tools.items()
        if name in READONLY_TOOL_ALLOWLIST
    }
    preview_tool = build_preview_trash_tool(manager)
    tools[preview_tool.name] = preview_tool
    return tools


def build_agent(
    model: str,
    tools: Sequence[Any],
    *,
    temperature: float = 0.0,
    max_iterations: int = 10,
) -> Any:
    """Build a read-only agent bound to the given allowlisted tools."""
    raise NotImplementedError("Storage agent implemented in a later milestone")


async def run_readonly_analysis(
    agent: Any,
    path: str,
    question: str | None = None,
) -> dict[str, Any]:
    """Run the agent against ``path`` and return ``{summary, tool_calls}``."""
    raise NotImplementedError("Storage agent implemented in a later milestone")
