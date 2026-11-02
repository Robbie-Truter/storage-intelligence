"""Tests for read_storage_guide (src/storage_intelligence_mcp/tools/resources.py)."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

import storage_intelligence_mcp.server  # noqa: F401
from storage_intelligence_mcp.core import mcp
from storage_intelligence_mcp.tools import resources
from storage_intelligence_mcp.tools.resources import (
    StorageGuideTopic,
    read_storage_guide,
)

GUIDES: list[tuple[StorageGuideTopic, str, str]] = [
    ("docker", "storage://docker", "# Docker storage"),
    ("macos", "storage://macos", "# macOS storage"),
    ("node", "storage://nodejs", "# Node.js storage"),
    ("python", "storage://python", "# Python storage"),
]


@pytest.fixture
def ctx() -> AsyncMock:
    """Mocked FastMCP Context; info/error are awaitable AsyncMocks."""
    return AsyncMock()


@pytest.mark.anyio
@pytest.mark.parametrize(("topic", "uri", "heading"), GUIDES)
async def test_returns_registered_resource_content(
    ctx: AsyncMock, topic: StorageGuideTopic, uri: str, heading: str
) -> None:
    result: Any = await read_storage_guide(ctx, topic)

    assert result["topic"] == topic
    assert result["uri"] == uri
    assert result["mime_type"] == "text/markdown"
    assert result["content"].startswith(heading)
    assert "## Sources" in result["content"]
    ctx.info.assert_awaited()


@pytest.mark.anyio
async def test_tool_schema_restricts_topic_values() -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    topic = tools["read_storage_guide"].parameters["properties"]["topic"]

    assert topic["enum"] == ["docker", "macos", "node", "python"]


@pytest.mark.anyio
async def test_resource_failure_is_logged_and_reraised(
    ctx: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(_uri: str) -> None:
        raise RuntimeError("resource registry unavailable")

    monkeypatch.setattr(resources.mcp, "read_resource", boom)

    with pytest.raises(RuntimeError, match="resource registry unavailable"):
        await read_storage_guide(ctx, "docker")

    ctx.error.assert_awaited_once()
