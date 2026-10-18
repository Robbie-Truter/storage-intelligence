"""Tests for ``GET /api/disk/usage``, ``GET /api/disk/directory``,
``GET /api/disk/explore``, ``GET /api/disk/count``, and ``GET /api/disk/info``.

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

DIRECTORY_RESULT: dict[str, Any] = {
    "path": "/Users/me",
    "entries": [
        {"name": "big.bin", "type": "file", "size_bytes": 900},
        {"name": "Downloads", "type": "directory", "size_bytes": 400},
    ],
}

EXPLORE_RESULT: dict[str, Any] = {
    "path": "/Users/me",
    "entries": [
        {"name": "core.py", "path": "/Users/me/core.py", "type": "file "},
        {"name": "src", "path": "/Users/me/src", "type": "directory "},
    ],
    "truncated": False,
}

FILE_INFO_RESULT: dict[str, Any] = {
    "name": "storage-intelligence",
    "path": "/home/user/storage-intelligence",
    "type": "directory",
    "size_bytes": 4096,
    "modified": 1728000000.0,
    "created": 1728000000.0,
    "extension": "",
}

COUNT_RESULT: dict[str, Any] = {
    "path": "/Users/me",
    "total_files": 3,
    "by_extension": {".py": 2, "(no extension)": 1},
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
    assert fake_manager.calls == [("disk_usage", {})]


def test_disk_usage_passes_path_through(
    disk_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    response = disk_client.get("/api/disk/usage", params={"path": "/tmp"})
    assert response.status_code == 200
    assert fake_manager.calls == [("disk_usage", {"path": "/tmp"})]


def test_disk_usage_tool_error_returns_400(fake_manager: FakeMCPClient) -> None:
    fake_manager.error = MCPToolError("disk_usage", "path does not exist")
    response = _disk_client(fake_manager).get("/api/disk/usage")
    assert response.status_code == 400
    assert response.json() == {
        "detail": {"tool": "disk_usage", "message": "path does not exist"}
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


def test_directory_usage_returns_payload() -> None:
    response = _disk_client(FakeMCPClient(DIRECTORY_RESULT)).get("/api/disk/directory")
    assert response.status_code == 200
    assert response.json() == DIRECTORY_RESULT


def test_directory_usage_calls_tool_with_defaults() -> None:
    fake = FakeMCPClient(DIRECTORY_RESULT)
    _disk_client(fake).get("/api/disk/directory")
    assert fake.calls == [("directory_disk_usage", {"top_n": 10})]


def test_directory_usage_passes_path_and_top_n() -> None:
    fake = FakeMCPClient(DIRECTORY_RESULT)
    response = _disk_client(fake).get(
        "/api/disk/directory", params={"path": "/tmp", "top_n": 3}
    )
    assert response.status_code == 200
    assert fake.calls == [("directory_disk_usage", {"path": "/tmp", "top_n": 3})]


def test_explore_directory_returns_payload() -> None:
    response = _disk_client(FakeMCPClient(EXPLORE_RESULT)).get("/api/disk/explore")
    assert response.status_code == 200
    assert response.json() == EXPLORE_RESULT


def test_explore_directory_calls_tool_with_defaults() -> None:
    fake = FakeMCPClient(EXPLORE_RESULT)
    _disk_client(fake).get("/api/disk/explore")
    assert fake.calls == [
        (
            "explore_directory",
            {
                "pattern": "",
                "search": "",
                "kind": "all",
                "recursive": False,
                "max_results": 100,
            },
        )
    ]


def test_explore_directory_passes_path_and_filters() -> None:
    fake = FakeMCPClient(EXPLORE_RESULT)
    response = _disk_client(fake).get(
        "/api/disk/explore",
        params={
            "path": "/tmp",
            "pattern": "*.py",
            "search": "core",
            "kind": "files",
            "recursive": True,
            "max_results": 5,
        },
    )
    assert response.status_code == 200
    assert fake.calls == [
        (
            "explore_directory",
            {
                "path": "/tmp",
                "pattern": "*.py",
                "search": "core",
                "kind": "files",
                "recursive": True,
                "max_results": 5,
            },
        )
    ]


def test_count_files_returns_payload() -> None:
    response = _disk_client(FakeMCPClient(COUNT_RESULT)).get("/api/disk/count")
    assert response.status_code == 200
    assert response.json() == COUNT_RESULT


def test_count_files_calls_tool_without_path() -> None:
    fake = FakeMCPClient(COUNT_RESULT)
    _disk_client(fake).get("/api/disk/count")
    assert fake.calls == [("count_files", {})]


def test_count_files_passes_path_through() -> None:
    fake = FakeMCPClient(COUNT_RESULT)
    response = _disk_client(fake).get("/api/disk/count", params={"path": "/tmp"})
    assert response.status_code == 200
    assert fake.calls == [("count_files", {"path": "/tmp"})]


def test_info_returns_payload() -> None:
    response = _disk_client(FakeMCPClient(FILE_INFO_RESULT)).get("/api/disk/info")
    assert response.status_code == 200
    assert response.json() == FILE_INFO_RESULT


def test_info_calls_tool_without_path() -> None:
    fake = FakeMCPClient(FILE_INFO_RESULT)
    _disk_client(fake).get("/api/disk/info")
    assert fake.calls == [("file_info", {})]


def test_info_passes_path_through() -> None:
    fake = FakeMCPClient(FILE_INFO_RESULT)
    response = _disk_client(fake).get("/api/disk/info", params={"path": "/tmp"})
    assert response.status_code == 200
    assert fake.calls == [("file_info", {"path": "/tmp"})]
