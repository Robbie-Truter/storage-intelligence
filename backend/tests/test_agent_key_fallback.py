"""Tests for reading provider keys from the OS credential store.

The agent accepts a client-supplied key, and otherwise falls back to the key
saved through the settings routes. These tests fake the keyring read so no real
credential store is touched.
"""

import pytest
from fastapi import HTTPException

from storage_intelligence_backend.credentials.api_keys import CredentialStoreError
from storage_intelligence_backend.routers import agent


def test_stored_api_key_reads_the_requested_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[str] = []

    def fake_get_api_key(provider: str) -> str | None:
        requested.append(provider)
        return "sk-test-openai"

    monkeypatch.setattr(agent, "get_api_key", fake_get_api_key)

    assert agent.stored_api_key("openai") == "sk-test-openai"
    assert requested == ["openai"]


def test_stored_api_key_maps_google_genai_to_google(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[str] = []

    def fake_get_api_key(provider: str) -> str | None:
        requested.append(provider)
        return "AIza-test-google"

    monkeypatch.setattr(agent, "get_api_key", fake_get_api_key)

    assert agent.stored_api_key("google_genai") == "AIza-test-google"
    assert requested == ["google"]


def test_stored_api_key_ignores_unknown_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(provider: str) -> str | None:
        raise AssertionError(f"unexpected keyring read for {provider}")

    monkeypatch.setattr(agent, "get_api_key", fail)

    assert agent.stored_api_key("anthropic") is None


def test_stored_api_key_reports_an_unavailable_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(provider: str) -> str | None:
        raise CredentialStoreError("backend unavailable")

    monkeypatch.setattr(agent, "get_api_key", fail)

    with pytest.raises(HTTPException) as exc_info:
        agent.stored_api_key("openai")

    assert exc_info.value.status_code == 503
