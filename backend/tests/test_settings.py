"""Tests for the local API key management endpoints.

The OS credential store is faked with an in-memory mapping, so tests never
touch the real keychain. Every key written by the tests is a dummy value.
"""

import pytest
from fastapi.testclient import TestClient
from keyring.errors import NoKeyringError, PasswordDeleteError

from storage_intelligence_backend.credentials import api_keys

Store = dict[tuple[str, str], str]


@pytest.fixture
def keyring_store(monkeypatch: pytest.MonkeyPatch) -> Store:
    """Replace the keyring backend with an in-memory store."""
    store: Store = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    def delete_password(service: str, username: str) -> None:
        try:
            del store[(service, username)]
        except KeyError as exc:
            raise PasswordDeleteError("password not found") from exc

    monkeypatch.setattr(api_keys.keyring, "get_password", get_password)
    monkeypatch.setattr(api_keys.keyring, "set_password", set_password)
    monkeypatch.setattr(api_keys.keyring, "delete_password", delete_password)
    return store


def test_get_reports_no_keys_initially(client: TestClient, keyring_store: Store) -> None:
    response = client.get("/api/settings/api-keys")

    assert response.status_code == 200
    assert response.json() == {"openai": False, "google": False}


def test_put_stores_a_key_under_the_expected_service_and_provider(
    client: TestClient, keyring_store: Store
) -> None:
    response = client.put("/api/settings/api-keys", json={"openai": "sk-test-openai"})

    assert response.status_code == 200
    assert response.json() == {"openai": True, "google": False}
    assert keyring_store[("storage-intelligence", "openai")] == "sk-test-openai"


def test_put_manages_the_providers_independently(
    client: TestClient, keyring_store: Store
) -> None:
    client.put("/api/settings/api-keys", json={"openai": "sk-test-openai"})
    response = client.put("/api/settings/api-keys", json={"google": "AIza-test-google"})

    assert response.status_code == 200
    assert response.json() == {"openai": True, "google": True}
    assert keyring_store[("storage-intelligence", "openai")] == "sk-test-openai"
    assert keyring_store[("storage-intelligence", "google")] == "AIza-test-google"


def test_put_never_returns_the_key(client: TestClient, keyring_store: Store) -> None:
    response = client.put("/api/settings/api-keys", json={"openai": "sk-super-secret"})

    assert response.status_code == 200
    assert "sk-super-secret" not in response.text


def test_put_replaces_an_existing_key(client: TestClient, keyring_store: Store) -> None:
    client.put("/api/settings/api-keys", json={"openai": "sk-old"})
    response = client.put("/api/settings/api-keys", json={"openai": "sk-new"})

    assert response.status_code == 200
    assert keyring_store[("storage-intelligence", "openai")] == "sk-new"


def test_put_with_an_empty_string_clears_the_key(
    client: TestClient, keyring_store: Store
) -> None:
    client.put("/api/settings/api-keys", json={"openai": "sk-test", "google": "AIza"})

    response = client.put("/api/settings/api-keys", json={"openai": ""})

    assert response.status_code == 200
    assert response.json() == {"openai": False, "google": True}
    assert ("storage-intelligence", "openai") not in keyring_store
    assert keyring_store[("storage-intelligence", "google")] == "AIza"


def test_put_with_whitespace_only_clears_the_key(
    client: TestClient, keyring_store: Store
) -> None:
    client.put("/api/settings/api-keys", json={"openai": "sk-test"})

    response = client.put("/api/settings/api-keys", json={"openai": "   "})

    assert response.status_code == 200
    assert response.json() == {"openai": False, "google": False}


def test_put_omitted_field_leaves_the_key_unchanged(
    client: TestClient, keyring_store: Store
) -> None:
    client.put("/api/settings/api-keys", json={"openai": "sk-test", "google": "AIza"})

    response = client.put("/api/settings/api-keys", json={"openai": "sk-replaced"})

    assert response.status_code == 200
    assert response.json() == {"openai": True, "google": True}
    assert keyring_store[("storage-intelligence", "google")] == "AIza"


def test_put_rejects_a_body_with_neither_provider(
    client: TestClient, keyring_store: Store
) -> None:
    response = client.put("/api/settings/api-keys", json={})

    assert response.status_code == 422


def test_put_rejects_unknown_fields(client: TestClient, keyring_store: Store) -> None:
    response = client.put("/api/settings/api-keys", json={"anthropic": "sk-test"})

    assert response.status_code == 422


def test_clearing_a_missing_key_is_not_an_error(
    client: TestClient, keyring_store: Store
) -> None:
    response = client.put("/api/settings/api-keys", json={"openai": ""})

    assert response.status_code == 200
    assert response.json() == {"openai": False, "google": False}


def test_get_returns_503_when_the_credential_store_is_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_args: str) -> str | None:
        raise NoKeyringError("no keyring backend")

    monkeypatch.setattr(api_keys.keyring, "get_password", _boom)

    response = client.get("/api/settings/api-keys")

    assert response.status_code == 503
    assert "credential store" in response.json()["detail"]


def test_put_returns_503_when_the_credential_store_cannot_be_written(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_args: str) -> None:
        raise NoKeyringError("no keyring backend")

    monkeypatch.setattr(api_keys.keyring, "set_password", _boom)

    response = client.put("/api/settings/api-keys", json={"openai": "sk-test"})

    assert response.status_code == 503
    assert "sk-test" not in response.text
