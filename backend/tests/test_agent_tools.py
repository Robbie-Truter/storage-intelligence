"""Tests for the agent tool map and the backend-authored ``preview_trash`` tool.

Safety properties under test: the agent sees exactly the 10 read-only MCP tools
plus ``preview_trash`` (never raw ``trash_path``), and ``preview_trash`` can
only ever ask MCP for a ``confirm=False`` preview.

Uses a fake manager shaped like ``FakeMCPClient`` in ``test_disk.py`` so no MCP
subprocess is spawned.
"""

from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel

from storage_intelligence_backend.agents.storage_agent import (
    build_agent_tool_map,
    build_preview_trash_tool,
)
from storage_intelligence_backend.mcp.errors import MCPToolError
from storage_intelligence_backend.mcp.manager import READONLY_TOOL_ALLOWLIST

PREVIEW_PAYLOAD: dict[str, Any] = {
    "mode": "preview",
    "requires_confirmation": True,
    "paths": ["/Users/me/big.bin", "/Users/me/old.log"],
    "missing_paths": ["/Users/me/gone.txt"],
    "total_valid_paths": 2,
    "message": "Dry run: Call trash_path with confirm=True to send items to trash.",
}

EXPECTED_PREVIEW_RESULT: dict[str, Any] = {
    "mode": "preview",
    "candidates": ["/Users/me/big.bin", "/Users/me/old.log"],
    "missing_paths": ["/Users/me/gone.txt"],
    "total_valid_paths": 2,
    "message": "Dry run: Call trash_path with confirm=True to send items to trash.",
}


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
    """Stands in for ``StorageMCPClient``; records ``call_tool`` calls and
    returns a canned result."""

    def __init__(
        self,
        result: dict[str, Any] | None = None,
        tools: dict[str, BaseTool] | None = None,
    ) -> None:
        self.result = PREVIEW_PAYLOAD if result is None else result
        self._tools = tools if tools is not None else {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    @property
    def langchain_tools(self) -> dict[str, BaseTool]:
        return dict(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        return self.result


def _over_exposed_tools() -> dict[str, BaseTool]:
    """The manager's map as it would look if *everything* MCP serves leaked
    through: the allowlist plus raw ``trash_path`` and an unknown name."""
    tools = {name: _stub_tool(name) for name in READONLY_TOOL_ALLOWLIST}
    tools["trash_path"] = _stub_tool("trash_path")
    tools["not_on_the_allowlist"] = _stub_tool("not_on_the_allowlist")
    return tools


def test_allowlist_is_exactly_the_ten_read_only_tools() -> None:
    assert len(READONLY_TOOL_ALLOWLIST) == 10
    assert READONLY_TOOL_ALLOWLIST == {
        "disk_usage",
        "directory_disk_usage",
        "explore_directory",
        "count_files",
        "file_info",
        "find_large_files",
        "find_duplicate_files",
        "find_stale_files",
        "find_empty_directories",
        "find_junk_files",
    }
    assert "trash_path" not in READONLY_TOOL_ALLOWLIST


def test_tool_map_is_allowlist_plus_preview_trash() -> None:
    manager = FakeManager(tools=_over_exposed_tools())
    tool_map = build_agent_tool_map(manager)

    assert set(tool_map) == set(READONLY_TOOL_ALLOWLIST) | {"preview_trash"}
    assert len(tool_map) == 11
    assert "trash_path" not in tool_map
    assert "not_on_the_allowlist" not in tool_map


def test_preview_trash_schema_exposes_only_paths() -> None:
    manager = FakeManager(tools=_over_exposed_tools())
    preview = build_agent_tool_map(manager)["preview_trash"]

    assert set(preview.args) == {"paths"}
    assert "confirm" not in preview.args


async def test_preview_trash_always_calls_mcp_with_confirm_false() -> None:
    manager = FakeManager()
    preview = build_preview_trash_tool(manager)

    result = await preview.ainvoke(
        {"paths": ["/Users/me/big.bin", "/Users/me/gone.txt"]}
    )

    assert manager.calls == [
        (
            "trash_path",
            {
                "paths": ["/Users/me/big.bin", "/Users/me/gone.txt"],
                "confirm": False,
            },
        )
    ]
    assert result == EXPECTED_PREVIEW_RESULT


async def test_preview_trash_returns_normalized_candidates() -> None:
    manager = FakeManager()
    preview = build_preview_trash_tool(manager)

    result: dict[str, Any] = await preview.ainvoke({"paths": ["/Users/me/big.bin"]})

    assert result["candidates"] == ["/Users/me/big.bin", "/Users/me/old.log"]
    assert result["missing_paths"] == ["/Users/me/gone.txt"]
    assert result["total_valid_paths"] == 2
    assert result["mode"] == "preview"
    assert isinstance(result["message"], str)


async def test_confirm_true_cannot_be_smuggled_through_the_schema() -> None:
    """A ``confirm`` key in the tool input never reaches the MCP manager."""
    manager = FakeManager()
    preview = build_preview_trash_tool(manager)

    await preview.ainvoke({"paths": ["/Users/me/big.bin"], "confirm": True})

    assert manager.calls == [
        ("trash_path", {"paths": ["/Users/me/big.bin"], "confirm": False})
    ]


async def test_non_preview_payload_is_rejected() -> None:
    """The tool refuses anything that is not a dry-run preview payload."""
    manager = FakeManager(result={"mode": "executed", "paths": ["/Users/me"]})
    preview = build_preview_trash_tool(manager)

    try:
        await preview.ainvoke({"paths": ["/Users/me"]})
    except MCPToolError as exc:
        assert exc.tool == "preview_trash"
    else:
        raise AssertionError("expected MCPToolError for a non-preview payload")

    assert manager.calls == [("trash_path", {"paths": ["/Users/me"], "confirm": False})]
