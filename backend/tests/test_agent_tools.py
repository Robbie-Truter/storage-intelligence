"""Tests for the agent tool map.

Safety properties under test: the agent sees exactly the allowlisted read-only
MCP tools from the manager (including ``preview_trash``) and never the raw
``trash_path`` tool.

Uses a fake manager shaped like ``FakeMCPClient`` in ``test_disk.py`` so no MCP
subprocess is spawned.
"""

from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel

from storage_intelligence_backend.agents.storage_agent import build_agent_tool_map
from storage_intelligence_backend.mcp.manager import READONLY_TOOL_ALLOWLIST


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


class FakeManager:
    """Stands in for ``StorageMCPClient``."""

    def __init__(self, tools: dict[str, BaseTool] | None = None) -> None:
        self._tools = tools if tools is not None else {}

    @property
    def langchain_tools(self) -> dict[str, BaseTool]:
        return dict(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError


def _over_exposed_tools() -> dict[str, BaseTool]:
    """The manager's map as it would look if everything MCP serves leaked
    through: the allowlist plus raw ``trash_path`` and an unknown name."""
    tools = {name: _stub_tool(name) for name in READONLY_TOOL_ALLOWLIST}
    tools["trash_path"] = _stub_tool("trash_path")
    tools["not_on_the_allowlist"] = _stub_tool("not_on_the_allowlist")
    return tools


def test_allowlist_includes_preview_trash_and_excludes_trash_path() -> None:
    assert len(READONLY_TOOL_ALLOWLIST) == 11
    assert "preview_trash" in READONLY_TOOL_ALLOWLIST
    assert "trash_path" not in READONLY_TOOL_ALLOWLIST


def test_tool_map_is_exactly_allowlisted_tools() -> None:
    manager = FakeManager(tools=_over_exposed_tools())
    tool_map = build_agent_tool_map(manager)

    assert set(tool_map) == set(READONLY_TOOL_ALLOWLIST)
    assert len(tool_map) == len(READONLY_TOOL_ALLOWLIST)
    assert "trash_path" not in tool_map
    assert "not_on_the_allowlist" not in tool_map
