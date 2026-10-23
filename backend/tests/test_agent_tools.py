"""Tests for the tool catalogue the agent is given.

Safety properties under test: the catalogue holds exactly the allowlisted
read-only MCP tools (including ``preview_trash``) and never the raw
``trash_path`` tool. The filtering lives in ``mcp/manager.py``, where the
allowlist is applied as the manager hands the catalogue out; it is called here
with stub tools, so no MCP subprocess is spawned.
"""

from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel

from storage_intelligence_backend.mcp.manager import (
    READONLY_TOOL_ALLOWLIST,
    StorageMCPClient,
    allowlisted_tools,
)


class _StubInput(BaseModel):
    """Placeholder input schema for stub tools that are never invoked."""


async def _stub_coroutine(**_: Any) -> Any:
    return None


def _stub_tool(name: str) -> BaseTool:
    return StructuredTool(
        name=name,
        description=f"stub {name}",
        args_schema=_StubInput,
        coroutine=_stub_coroutine,
    )


def _over_exposed_tools() -> list[BaseTool]:
    """The MCP tools as they would look if everything served leaked through:
    the allowlist plus raw ``trash_path`` and an unknown name."""
    names = [*READONLY_TOOL_ALLOWLIST, "trash_path", "not_on_the_allowlist"]
    return [_stub_tool(name) for name in names]


class _Manager(StorageMCPClient):
    """A manager whose tool catalogue was filled without opening a connection."""

    def __init__(self, tools: list[BaseTool]) -> None:
        super().__init__(command="", args=[], project_directory="")
        self._langchain_tools = {tool.name: tool for tool in tools}


def test_allowlist_includes_preview_trash_and_excludes_trash_path() -> None:
    assert len(READONLY_TOOL_ALLOWLIST) == 11
    assert "preview_trash" in READONLY_TOOL_ALLOWLIST
    assert "trash_path" not in READONLY_TOOL_ALLOWLIST


def test_tool_map_is_exactly_allowlisted_tools() -> None:
    tool_map = allowlisted_tools(_over_exposed_tools())

    assert set(tool_map) == set(READONLY_TOOL_ALLOWLIST)
    assert len(tool_map) == len(READONLY_TOOL_ALLOWLIST)
    assert "trash_path" not in tool_map
    assert "not_on_the_allowlist" not in tool_map


def test_the_manager_hands_out_only_allowlisted_tools() -> None:
    manager = _Manager(_over_exposed_tools())

    handed_out = manager.langchain_tools

    assert set(handed_out) == set(READONLY_TOOL_ALLOWLIST)
    assert "trash_path" not in handed_out
    assert "not_on_the_allowlist" not in handed_out
