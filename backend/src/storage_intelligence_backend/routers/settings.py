"""Local provider API key management.

Keys live in the operating system's credential store, not in SQLite, JSON, or
``.env`` files. The endpoints report only whether a provider is configured; a
submitted key is written to the keychain and never echoed, logged, or returned.
OpenAI and Google Gemini are managed independently.
"""

from fastapi import APIRouter, HTTPException, status

from ..credentials.api_keys import (
    PROVIDERS,
    CredentialStoreError,
    clear_api_key,
    has_api_key,
    set_api_key,
)
from ..schemas import ApiKeyStatusResponse, ApiKeysUpdateRequest

router = APIRouter(prefix="/settings", tags=["settings"])


def _status() -> ApiKeyStatusResponse:
    try:
        return ApiKeyStatusResponse(
            openai=has_api_key("openai"),
            google=has_api_key("google"),
        )
    except CredentialStoreError as exc:
        raise _unavailable(exc) from exc


@router.get("/api-keys", response_model=ApiKeyStatusResponse)
async def get_api_key_status() -> ApiKeyStatusResponse:
    """Report whether each provider has a stored API key.

    Only boolean flags are returned - never the keys themselves.
    """
    return _status()


@router.put("/api-keys", response_model=ApiKeyStatusResponse)
async def update_api_keys(request: ApiKeysUpdateRequest) -> ApiKeyStatusResponse:
    """Store, replace, or clear the submitted provider keys.

    Each field is handled independently:

    - a non-empty value stores or replaces that provider's key;
    - an empty (or whitespace-only) value clears it;
    - an omitted field leaves the existing key unchanged.

    A body with neither ``openai`` nor ``google`` is a 422. The response is the
    same presence payload as ``GET``, so a key is never returned.

    Status codes:
        200: the update ran; the body reports which providers are configured.
        422: neither provider field was supplied.
        503: the OS credential store could not be read or written.
    """
    try:
        for provider in PROVIDERS:
            if provider not in request.model_fields_set:
                continue

            secret = getattr(request, provider)
            if secret is None:
                continue

            value = secret.get_secret_value().strip()
            if value:
                set_api_key(provider, value)
            else:
                clear_api_key(provider)
    except CredentialStoreError as exc:
        raise _unavailable(exc) from exc

    return _status()


def _unavailable(exc: CredentialStoreError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )
