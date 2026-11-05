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
when the run fails after the stream has opened.
"""

import json
from collections.abc import AsyncIterator
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
from ..deps import get_mcp_manager
from ..mcp.errors import MCPUnavailable
from ..mcp.manager import StorageMCPClient
from ..schemas import AgentAnalyzeRequest, AgentModelOption

router = APIRouter(prefix="/agent", tags=["agent"])


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
    must be one of the installed integrations. ``api_key`` is the client-supplied
    key for that provider (required for cloud models, unused for Ollama).
    ``path`` is optional - without it the agent starts from the default
    location, which is where the MCP tools fall back to. ``question`` is
    optional too: without one the agent looks for what takes the most space.

    The agent is built per request from the injected manager, and it is given
    only the tools on the read-only allowlist - never the raw ``trash_path``
    tool.

    The response is ``text/event-stream``. Each frame carries one event
    (``tool_call``, ``text_delta``, then ``complete``); a failure after the
    stream opens ends it with an ``error`` event.

    Status codes:
        200: the stream opened; inspect the ``event``/``type`` of each frame.
        422: ``provider`` is unsupported, ``model_name`` is empty, or ``api_key``
            is missing for a cloud provider.
        503: the MCP server is unavailable, or the chat model could not be
            constructed (for example, its provider integration failed to load).
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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"api_key is required for the {provider} provider.",
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

    async def _event_generator() -> AsyncIterator[str]:
        yield _sse_frame({"type": "start", "messageId": "assistant-1"})
        yield _sse_frame({"type": "text-start", "id": "text-1"})
        try:
            async for event in stream_readonly_analysis(agent, request.path, request.question):
                ui_event = _to_ui_events(event)
                if ui_event:
                    yield _sse_frame(ui_event)

            yield _sse_frame({"type": "text-end", "id": "text-1"})
            yield _sse_frame({"type": "finish"})
            yield "data: [DONE]\n\n"
        except GraphRecursionError:
            detail = (
                "The agent reached its step limit of "
                f"{settings.agent_max_iterations} steps before it could answer."
            )
            yield _sse_frame({"type": "error", "errorText": detail})
        except (AgentModelError, MCPUnavailable) as exc:
            message = exc.message if isinstance(exc, AgentModelError) else str(exc)
            yield _sse_frame({"type": "error", "errorText": message})
        except Exception as exc:
            yield _sse_frame({"type": "error", "errorText": f"Unexpected error: {exc}"})

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )


def _to_ui_events(event: dict[str, Any]) -> dict[str, Any] | None:
    if event["type"] == "text_delta":
        return {
            "type": "text-delta",
            "id": "text-1",
            "delta": event["content"],
        }

    if event["type"] == "tool_call":
        return {
            "type": "tool-input-available",
            "toolCallId": event["id"],
            "toolName": event["name"],
            "input": event["args"],
        }


def _sse_frame(event: dict[str, Any]) -> str:
    """Format one event as a Server-Sent Events frame."""
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n\n"
