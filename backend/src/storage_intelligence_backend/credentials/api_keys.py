"""Provider API keys stored in the operating system's credential store.

Keys are kept in the OS keychain via :mod:`keyring` - never in SQLite, JSON, or
``.env`` files. Every provider is stored independently under the same service
name and its own provider name, so one key can be set, replaced, or cleared
without touching the other.
"""

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE_NAME = "storage-intelligence"
PROVIDERS = ("openai", "google")


class CredentialStoreError(RuntimeError):
    """Raised when the OS credential store cannot be read or written."""


def get_api_key(provider: str) -> str | None:
    """Return the stored key for ``provider``, or ``None`` when unset."""
    _validate_provider(provider)
    try:
        return keyring.get_password(SERVICE_NAME, provider)
    except KeyringError as exc:
        raise CredentialStoreError(
            f"Could not read the {provider} API key from the OS credential store."
        ) from exc


def has_api_key(provider: str) -> bool:
    """Report whether a non-empty key is stored for ``provider``."""
    return bool(get_api_key(provider))


def set_api_key(provider: str, api_key: str) -> None:
    """Store or replace the key for ``provider``."""
    _validate_provider(provider)
    try:
        keyring.set_password(SERVICE_NAME, provider, api_key)
    except KeyringError as exc:
        raise CredentialStoreError(
            f"Could not store the {provider} API key in the OS credential store."
        ) from exc


def clear_api_key(provider: str) -> None:
    """Remove the key for ``provider``; leaving it absent is not an error."""
    _validate_provider(provider)
    try:
        keyring.delete_password(SERVICE_NAME, provider)
    except PasswordDeleteError:
        return
    except KeyringError as exc:
        raise CredentialStoreError(
            f"Could not clear the {provider} API key from the OS credential store."
        ) from exc


def _validate_provider(provider: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported credential provider: {provider!r}.")
