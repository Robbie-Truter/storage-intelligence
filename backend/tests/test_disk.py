"""Tests for ``GET /api/disk/usage``.

Use a fake MCP manager via ``dependency_overrides`` so the real subprocess is
never spawned; the MCP connection itself is covered by integration tests.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from storage_intelligence_backend.deps import get_mcp_manager
from storage_intelligence_backend.main import create_app
from storage_intelligence_backend.mcp.errors import MCPToolError, MCPUnavailable

USAGE_RESULT: dict[str, Any] = {
    "path": "/Users/me",
    "total_bytes": 500,
    "used_bytes": 200,
    "free_bytes": 300,
    "usage_percent": 40.0,
}


class FakeMCPClient:
    """Stands in for ``StorageMCPClient``; records calls and returns a canned
    result or raises a canned error."""

    def __init__(
        self,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = USAGE_RESULT if result is None else result
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if self.error is not None:
            raise self.error
        return self.result


def _disk_client(fake_manager: FakeMCPClient) -> TestClient:
    """App wired to ``fake_manager``; lifespan is not entered (no subprocess)."""
    app = create_app()
    app.state.mcp = None
    app.dependency_overrides[get_mcp_manager] = lambda: fake_manager
    return TestClient(app)


@pytest.fixture
def fake_manager() -> FakeMCPClient:
    return FakeMCPClient()


@pytest.fixture
def disk_client(fake_manager: FakeMCPClient) -> TestClient:
    return _disk_client(fake_manager)


def test_disk_usage_returns_payload(disk_client: TestClient) -> None:
    response = disk_client.get("/api/disk/usage")
    assert response.status_code == 200
    assert response.json() == USAGE_RESULT


def test_disk_usage_calls_tool_without_path(
    disk_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    disk_client.get("/api/disk/usage")
    assert fake_manager.calls == [("get_disk_usage", {})]


def test_disk_usage_passes_path_through(
    disk_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    response = disk_client.get("/api/disk/usage", params={"path": "/tmp"})
    assert response.status_code == 200
    assert fake_manager.calls == [("get_disk_usage", {"path": "/tmp"})]


def test_disk_usage_tool_error_returns_400(fake_manager: FakeMCPClient) -> None:
    fake_manager.error = MCPToolError("get_disk_usage", "path does not exist")
    response = _disk_client(fake_manager).get("/api/disk/usage")
    assert response.status_code == 400
    assert response.json() == {
        "detail": {"tool": "get_disk_usage", "message": "path does not exist"}
    }


def test_disk_usage_unavailable_returns_503(fake_manager: FakeMCPClient) -> None:
    fake_manager.error = MCPUnavailable("MCP server is not available")
    response = _disk_client(fake_manager).get("/api/disk/usage")
    assert response.status_code == 503
    assert response.json() == {"detail": "MCP server is not available"}


def test_disk_usage_503_without_manager(client: TestClient) -> None:
    response = client.get("/api/disk/usage")
    assert response.status_code == 503
    assert response.json() == {"detail": "MCP server is not available"}
