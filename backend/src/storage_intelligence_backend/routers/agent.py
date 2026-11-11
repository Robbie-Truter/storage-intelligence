"""LLM-driven agent endpoints (read-only tools only).

``GET /api/agent/models`` lists the models the agent can be configured with.
``POST /api/agent/analyze`` runs the read-only agent and streams the run as
Server-Sent Events (``text/event-stream``), one event per frame::

    event: tool_call
    data: {"type": "tool_call", "name": "...", "args": {...}}

    event: text_delta
    data: {"type": "text_delta", "content": "..."}

    event: complete
    data: {"type": "complete", "summary": "...", "tool_calls": [...]}

    event: error
    data: {"type": "error", "detail": "..."}

``complete`` is the last event on a successful run; ``error`` is the last event
when the run fails after the stream has opened. When the client disconnects
mid-stream the agent run is cancelled server-side instead of being left to
finish in the background.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langgraph.errors import GraphRecursionError

from ..agents.errors import AgentModelError, format_model_error
from ..agents.models import (
    MODEL_CATALOG,
    SUPPORTED_PROVIDERS,
)
from ..agents.storage_agent import build_agent, stream_readonly_analysis
from ..config import get_settings
from ..credentials.api_keys import PROVIDERS, CredentialStoreError, get_api_key
from ..deps import get_mcp_manager
from ..mcp.errors import MCPUnavailable
from ..mcp.manager import StorageMCPClient
from ..schemas import AgentAnalyzeRequest, AgentModelOption

router = APIRouter(prefix="/agent", tags=["agent"])

_CREDENTIAL_PROVIDER_ALIASES = {"google_genai": "google"}


def stored_api_key(provider: str) -> str | None:
    """Return the key saved in the OS credential store for ``provider``.

    LangChain provider ids do not always match the credential-store names;
    ``google_genai`` uses the ``google`` entry. Providers without an entry are
    reported as unset.
    """
    credential_provider = _CREDENTIAL_PROVIDER_ALIASES.get(provider, provider)
    if credential_provider not in PROVIDERS:
        return None

    try:
        return get_api_key(credential_provider)
    except CredentialStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The operating system credential store is unavailable.",
        ) from exc


@router.get("/models", response_model=list[AgentModelOption])
async def list_models() -> list[AgentModelOption]:
    """List the model options the agent can be configured with.

    The catalogue is static and needs neither the MCP server nor a provider
    key, so the frontend can build a model picker before anything is
    configured.
    """
    return [
        AgentModelOption(
            id=option.id,
            label=option.label,
            provider=option.provider,
            model_name=option.model_name,
            mode=option.mode,
        )
        for option in MODEL_CATALOG
    ]


@router.post("/analyze")
async def analyze(
    request: AgentAnalyzeRequest,
    manager: StorageMCPClient = Depends(get_mcp_manager),
) -> StreamingResponse:
    """Analyze the storage usage under ``path`` and stream the run as SSE.

    ``provider`` and ``model_name`` identify the model to build; the provider
    must be one of the installed integrations. ``api_key`` is optional for cloud
    models: when omitted, the key saved in the OS credential store is used. It
    is unused for Ollama.
    ``path`` is optional - without it the agent starts from the default
    location, which is where the MCP tools fall back to. ``question`` is
    optional too: without one the agent looks for what takes the most space.

    The agent is built per request from the injected manager, and it is given
    only the tools on the read-only allowlist - never the raw ``trash_path``
    tool.

    The response is ``text/event-stream``. Each frame carries one event
    (``tool_call``, ``text_delta``, then ``complete``); a failure after the
    stream opens ends it with an ``error`` event. When the client disconnects
    mid-stream - the browser aborting the fetch, for example - the agent run
    is cancelled instead of running on.

    Status codes:
        200: the stream opened; inspect the ``event``/``type`` of each frame.
        422: ``provider`` is unsupported, ``model_name`` is empty, or no API key
            is available for a cloud provider.
        503: the MCP server is unavailable, the OS credential store cannot be
            read, or the chat model could not be constructed (for example, its
            provider integration failed to load).
    """
    settings = get_settings()

    provider = request.provider.strip().lower() if request.provider else None
    model_name = request.model_name.strip() if request.model_name else None

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="provider is required.",
        )

    if provider not in SUPPORTED_PROVIDERS:
        supported_providers = ", ".join(SUPPORTED_PROVIDERS)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported provider {provider!r}. Choose one of: {supported_providers}.",
        )

    if not model_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="model_name must not be empty.",
        )

    api_key = request.api_key.get_secret_value() if request.api_key else None

    if provider != "ollama" and not api_key:
        api_key = stored_api_key(provider)

    if provider != "ollama" and not api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"No API key is available for the {provider} provider. "
                "Save one in Settings or send api_key with the request."
            ),
        )

    try:
        agent = build_agent(
            model=f"{provider}:{model_name}",
            manager=manager,
            temperature=settings.agent_temperature,
            max_iterations=settings.agent_max_iterations,
            api_key=api_key if provider != "ollama" else None,
        )
    except Exception as exc:
        _, message = format_model_error(exc)
        detail = (
            message
            if not message.startswith("Agent model run failed: ")
            else f"Agent model is not available: {exc}"
        )
        raise AgentModelError(detail, status_code=503) from exc

    return StreamingResponse(
        _agent_event_stream(
            agent,
            request.path,
            request.messages,
            max_iterations=settings.agent_max_iterations,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )


async def _agent_event_stream(
    agent: Any,
    path: str | None,
    messages: list[dict[str, Any]] | None,
    *,
    max_iterations: int,
) -> AsyncIterator[str]:
    """Stream one agent run as SSE frames, cancelling the run on disconnect.

    The agent runs in its own task and its events travel through a queue, so
    the response side and the agent side shut down independently: when the
    client disconnects, the server cancels the task driving this generator
    (Starlette raises ``CancelledError`` at the ``await`` this generator is
    blocked on), and the ``finally`` below cancels the agent run rather than
    letting it finish unnoticed in the background.

    Agent failures are forwarded through the queue and re-raised on the
    response side, so they end the stream with an ``error`` frame exactly as
    they did when the generator awaited the agent directly.
    """
    message_id = str(uuid.uuid4())
    text_id = str(uuid.uuid4())

    yield _sse_frame({"type": "start", "messageId": message_id})
    yield _sse_frame({"type": "text-start", "id": text_id})

    queue: asyncio.Queue[dict[str, Any] | Exception | None] = asyncio.Queue()

    async def _run_agent() -> None:
        try:
            async for event in stream_readonly_analysis(agent, path, messages=messages):
                await queue.put(event)
        except Exception as exc:
            await queue.put(exc)
        else:
            await queue.put(None)

    run_task = asyncio.create_task(_run_agent())

    try:
        while True:
            item = await queue.get()
            if isinstance(item, Exception):
                raise item
            if item is None:
                break
            ui_event = _to_ui_events(item, text_id)
            if ui_event:
                yield _sse_frame(ui_event)

        yield _sse_frame({"type": "text-end", "id": text_id})
        yield _sse_frame({"type": "finish"})
        yield "data: [DONE]\n\n"
    except GraphRecursionError:
        detail = (
            "The agent reached its step limit of "
            f"{max_iterations} steps before it could answer."
        )
        yield _sse_frame({"type": "error", "errorText": detail})
    except (AgentModelError, MCPUnavailable) as exc:
        message = exc.message if isinstance(exc, AgentModelError) else str(exc)
        yield _sse_frame({"type": "error", "errorText": message})
    except Exception as exc:
        yield _sse_frame({"type": "error", "errorText": f"Unexpected error: {exc}"})
    finally:
        run_task.cancel()
        with suppress(asyncio.CancelledError):
            await run_task


def _to_ui_events(event: dict[str, Any], id: str) -> dict[str, Any] | None:
    if event["type"] == "text_delta":
        return {
            "type": "text-delta",
            "id": id,
            "delta": event["content"],
        }

    if event["type"] == "tool_call":
        return {
            "type": "tool-input-available",
            "toolCallId": event["id"],
            "toolName": event["name"],
            "input": event["args"],
        }

    if event["type"] == "tool_result":
        return {
            "type": "tool-output-available",
            "toolCallId": event["id"],
            "output": event["result"],
        }


def _sse_frame(event: dict[str, Any]) -> str:
    """Format one event as a Server-Sent Events frame."""
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n\n"
