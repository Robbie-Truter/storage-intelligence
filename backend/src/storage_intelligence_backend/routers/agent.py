"""LLM-driven agent endpoints (read-only tools only).

``GET /api/agent/models`` lists the models the agent can be configured with.
``POST /api/agent/analyze`` runs the read-only agent over the allowlisted MCP
tools and reports both its answer and the tools it used.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.errors import GraphRecursionError

from ..agents.errors import AgentModelError, format_model_error
from ..agents.models import (
    MODEL_CATALOG,
    SUPPORTED_PROVIDERS,
)
from ..agents.storage_agent import build_agent, run_readonly_analysis
from ..config import get_settings
from ..deps import get_mcp_manager
from ..mcp.manager import StorageMCPClient
from ..schemas import AgentAnalyzeRequest, AgentAnalyzeResponse, AgentModelOption

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


@router.post("/analyze", response_model=AgentAnalyzeResponse)
async def analyze(
    request: AgentAnalyzeRequest,
    manager: StorageMCPClient = Depends(get_mcp_manager),
) -> AgentAnalyzeResponse:
    """Analyze the storage usage under ``path`` with the read-only agent.

    ``provider`` and ``model_name`` identify the model to build; the provider
    must be one of the installed integrations. ``api_key`` is the client-supplied
    key for that provider (required for cloud models, unused for Ollama).
    ``path`` is optional - without it the agent starts from the default
    location, which is where the MCP tools fall back to. ``question`` is
    optional too: without one the agent looks for what takes the most space.

    The agent is built per request from the injected manager, and it is given
    only the tools on the read-only allowlist - never the raw ``trash_path``
    tool.

    Status codes:
        200: the agent answered; the body carries its ``summary`` and the
            ``tool_calls`` it made.
        400: the agent used up its step limit before it could answer.
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
            detail=(
                f"Unsupported provider {provider!r}. Choose one of: {supported_providers}."
            ),
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
        status_code, message = format_model_error(exc)
        detail = (
            message
            if not message.startswith("Agent model run failed: ")
            else f"Agent model is not available: {exc}"
        )
        raise AgentModelError(detail, status_code=status_code) from exc

    try:
        result = await run_readonly_analysis(agent, request.path, request.question)
    except GraphRecursionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The agent reached its step limit of "
                f"{settings.agent_max_iterations} steps before it could answer."
            ),
        ) from exc

    return AgentAnalyzeResponse(**result)
