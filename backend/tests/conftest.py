"""Shared test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from storage_intelligence_backend.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient whose lifespan has run."""
    with TestClient(create_app()) as test_client:
        yield test_client
