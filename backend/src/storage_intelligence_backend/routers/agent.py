"""LLM-driven agent endpoints (read-only tools only).

``GET /api/agent/models`` lists the models the agent can be configured with.
``POST /api/agent/analyze`` runs the read-only agent over the allowlisted MCP
tools and reports both its answer and the tools it used.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.errors import GraphRecursionError

from ..agents.models import MODEL_CATALOG, find_model
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

    ``model`` is the ``id`` the client picked from ``GET /api/agent/models``;
    it is validated against the hardcoded catalogue before anything is built.
    ``api_key`` is the client-supplied key for that provider (required for
    cloud models, unused for Ollama). ``path`` is optional - without it the
    agent starts from the default
    location, which is where the MCP tools fall back to. ``question`` is
    optional too: without one the agent looks for what takes the most space.

    The agent is built per request from the injected manager, and it is given
    only the tools on the read-only allowlist - never the raw ``trash_path``
    tool.

    Status codes:
        200: the agent answered; the body carries its ``summary`` and the
            ``tool_calls`` it made.
        400: the agent used up its step limit before it could answer.
        422: ``model`` is not in the catalogue, or ``api_key`` is missing for a
            cloud provider.
        503: the MCP server is unavailable, or the chat model could not be
            constructed (for example, its provider integration failed to load).
    """
    settings = get_settings()

    option = find_model(request.model)

    if option is None:
        supported = ", ".join(model.id for model in MODEL_CATALOG)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported model {request.model!r}. Choose one of: {supported}.",
        )

    api_key = request.api_key.get_secret_value() if request.api_key else None

    if option.provider != "ollama" and not api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"api_key is required for the {option.provider} provider.",
        )

    try:
        agent = build_agent(
            model=option.model_string,
            manager=manager,
            temperature=settings.agent_temperature,
            max_iterations=settings.agent_max_iterations,
            api_key=api_key if option.provider != "ollama" else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent model is not available: {exc}",
        ) from exc

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
