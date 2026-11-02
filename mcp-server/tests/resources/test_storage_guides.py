"""Tests for the read-only storage guides in resources/."""

from collections.abc import Callable

import pytest

from storage_intelligence_mcp.core import mcp
from storage_intelligence_mcp.resources import docker, macos, nodejs, python

STORAGE_GUIDES: list[tuple[str, Callable[[], str], str]] = [
    ("storage://docker", docker.docker_storage_guide, "# Docker storage"),
    ("storage://macos", macos.macos_storage_guide, "# macOS storage"),
    ("storage://nodejs", nodejs.nodejs_storage_guide, "# Node.js storage"),
    ("storage://python", python.python_storage_guide, "# Python storage"),
]


@pytest.mark.anyio
async def test_storage_guides_are_registered_as_markdown() -> None:
    resources = {str(resource.uri): resource for resource in await mcp.list_resources()}

    for uri, _, _ in STORAGE_GUIDES:
        assert uri in resources
        assert resources[uri].mime_type == "text/markdown"


@pytest.mark.parametrize(("uri", "guide", "heading"), STORAGE_GUIDES)
def test_storage_guide_content(
    uri: str, guide: Callable[[], str], heading: str
) -> None:
    text = guide()

    assert uri.startswith("storage://")
    assert text.startswith(heading)
    assert "## Sources" in text
    assert "https://" in text
