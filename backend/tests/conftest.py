"""Shared test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from storage_intelligence_backend.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A ``TestClient`` for unit tests that does not run the lifespan.

    Without entering the context manager the startup hooks are skipped, so the
    real MCP subprocess is never spawned and ``app.state.mcp`` stays unset
    (readiness reports unavailable). Integration tests exercise the real
    lifespan separately.
    """
    app = create_app()
    app.state.mcp = None
    yield TestClient(app)
