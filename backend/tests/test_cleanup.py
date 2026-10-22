"""Tests for ``POST /api/cleanup/execute``.

Use a fake MCP manager via ``dependency_overrides`` so the real subprocess is
never spawned and no file is ever sent to the trash; the MCP connection itself
is covered by integration tests.

Two properties are under test beyond the mapping: the submitted paths reach the
MCP tool unchanged, and this endpoint is the only place in the backend that
may ask the MCP server to execute a deletion.
"""

import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import storage_intelligence_backend
from storage_intelligence_backend.deps import get_mcp_manager
from storage_intelligence_backend.main import create_app
from storage_intelligence_backend.mcp.errors import MCPToolError, MCPUnavailable
from storage_intelligence_backend.mcp.manager import READONLY_TOOL_ALLOWLIST

EXECUTED_RESULT: dict[str, Any] = {
    "mode": "executed",
    "requires_confirmation": False,
    "paths": ["/tmp/a", "/tmp/b"],
    "missing_paths": [],
    "total_valid_paths": 2,
    "deleted": ["/tmp/a", "/tmp/b"],
    "failed": [],
}

MIXED_RESULT: dict[str, Any] = {
    "mode": "executed",
    "requires_confirmation": False,
    "paths": ["/tmp/a"],
    "missing_paths": ["/tmp/gone"],
    "total_valid_paths": 1,
    "deleted": ["/tmp/a"],
    "failed": [],
}

FAILED_RESULT: dict[str, Any] = {
    "mode": "executed",
    "requires_confirmation": False,
    "paths": ["/tmp/a", "/tmp/b"],
    "missing_paths": [],
    "total_valid_paths": 2,
    "deleted": ["/tmp/a"],
    "failed": [{"path": "/tmp/b", "error": "OSError: permission denied"}],
}

PACKAGE_ROOT = Path(storage_intelligence_backend.__file__).parent

# Matches a call that asks MCP to execute a deletion, whether it is written as
# ``confirm=True`` (keyword) or ``"confirm": True`` (argument).
CONFIRM_TRUE = re.compile(r"confirm[\"']?\s*[:=]\s*True")


class FakeMCPClient:
    """Stands in for ``StorageMCPClient``; records calls and returns a canned
    result or raises a canned error."""

    def __init__(
        self,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = EXECUTED_RESULT if result is None else result
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if self.error is not None:
            raise self.error
        return self.result


def _cleanup_client(fake_manager: FakeMCPClient) -> TestClient:
    """App wired to ``fake_manager``; lifespan is not entered (no subprocess)."""
    app = create_app()
    app.state.mcp = None
    app.dependency_overrides[get_mcp_manager] = lambda: fake_manager
    return TestClient(app)


@pytest.fixture
def fake_manager() -> FakeMCPClient:
    return FakeMCPClient()


@pytest.fixture
def cleanup_client(fake_manager: FakeMCPClient) -> TestClient:
    return _cleanup_client(fake_manager)


def test_execute_returns_the_mapped_payload(cleanup_client: TestClient) -> None:
    response = cleanup_client.post("/api/cleanup/execute", json={"paths": ["/tmp/a"]})

    assert response.status_code == 200
    assert response.json() == {
        "mode": "executed",
        "paths": ["/tmp/a", "/tmp/b"],
        "deleted": ["/tmp/a", "/tmp/b"],
        "failed": [],
        "missing_paths": [],
        "total_valid_paths": 2,
    }


def test_execute_passes_the_paths_through_unchanged(
    cleanup_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    response = cleanup_client.post(
        "/api/cleanup/execute", json={"paths": ["/tmp/a", "/tmp/b"]}
    )

    assert response.status_code == 200
    assert fake_manager.calls == [
        ("trash_path", {"paths": ["/tmp/a", "/tmp/b"], "confirm": True})
    ]


def test_execute_calls_the_tool_exactly_once(
    cleanup_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    cleanup_client.post("/api/cleanup/execute", json={"paths": ["/tmp/a"]})

    assert len(fake_manager.calls) == 1
    assert fake_manager.calls[0][0] == "trash_path"


def test_execute_maps_failed_entries(
    fake_manager: FakeMCPClient,
) -> None:
    fake = FakeMCPClient(FAILED_RESULT)
    response = _cleanup_client(fake).post(
        "/api/cleanup/execute", json={"paths": ["/tmp/a", "/tmp/b"]}
    )

    assert response.status_code == 200
    assert response.json()["deleted"] == ["/tmp/a"]
    assert response.json()["failed"] == [
        {"path": "/tmp/b", "error": "OSError: permission denied"}
    ]


def test_execute_rejects_an_empty_path_list(
    cleanup_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    response = cleanup_client.post("/api/cleanup/execute", json={"paths": []})

    assert response.status_code == 422
    assert fake_manager.calls == []


def test_execute_rejects_a_client_supplied_confirm(
    cleanup_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    response = cleanup_client.post(
        "/api/cleanup/execute", json={"paths": ["/tmp/a"], "confirm": True}
    )

    assert response.status_code == 422
    assert fake_manager.calls == []


def test_execute_rejects_a_client_supplied_preview_id(
    cleanup_client: TestClient, fake_manager: FakeMCPClient
) -> None:
    response = cleanup_client.post(
        "/api/cleanup/execute", json={"paths": ["/tmp/a"], "preview_id": "abc"}
    )

    assert response.status_code == 422
    assert fake_manager.calls == []


def test_execute_reports_a_stale_path_in_a_mixed_batch(
    fake_manager: FakeMCPClient,
) -> None:
    fake = FakeMCPClient(MIXED_RESULT)
    response = _cleanup_client(fake).post(
        "/api/cleanup/execute", json={"paths": ["/tmp/a", "/tmp/gone"]}
    )

    assert response.status_code == 200
    assert response.json()["missing_paths"] == ["/tmp/gone"]
    assert response.json()["deleted"] == ["/tmp/a"]
    assert response.json()["total_valid_paths"] == 1
    assert fake.calls == [
        ("trash_path", {"paths": ["/tmp/a", "/tmp/gone"], "confirm": True})
    ]


def test_execute_all_missing_returns_400(fake_manager: FakeMCPClient) -> None:
    fake_manager.error = MCPToolError("trash_path", "Path not found: /tmp/gone")

    response = _cleanup_client(fake_manager).post(
        "/api/cleanup/execute", json={"paths": ["/tmp/gone"]}
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {"tool": "trash_path", "message": "Path not found: /tmp/gone"}
    }


def test_execute_unavailable_returns_503(fake_manager: FakeMCPClient) -> None:
    fake_manager.error = MCPUnavailable("MCP server is not available")

    response = _cleanup_client(fake_manager).post(
        "/api/cleanup/execute", json={"paths": ["/tmp/a"]}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "MCP server is not available"}


def test_execute_503_without_manager(client: TestClient) -> None:
    response = client.post("/api/cleanup/execute", json={"paths": ["/tmp/a"]})

    assert response.status_code == 503
    assert response.json() == {"detail": "MCP server is not available"}


def test_only_the_cleanup_router_asks_mcp_to_execute() -> None:
    """``confirm=True`` reaches the MCP client from one place only.

    Every other route (and every agent tool) must stay preview-only, so the
    execution flag may not appear anywhere else in the package.
    """
    offenders = sorted(
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*.py")
        if CONFIRM_TRUE.search(path.read_text(encoding="utf-8"))
    )

    assert offenders == ["routers/cleanup.py"]


def test_trash_path_is_not_on_the_read_only_allowlist() -> None:
    """The agent must never be able to reach the destructive tool."""
    assert "trash_path" not in READONLY_TOOL_ALLOWLIST
