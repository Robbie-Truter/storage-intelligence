"""LLM-driven agent endpoints (read-only tools only).

``POST /api/agent/analyze`` runs the read-only agent over the allowlisted MCP
tools and reports both its answer and the tools it used.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.errors import GraphRecursionError

from ..agents.storage_agent import build_agent, run_readonly_analysis
from ..config import get_settings
from ..deps import get_mcp_manager
from ..mcp.manager import StorageMCPClient
from ..schemas import AgentAnalyzeRequest, AgentAnalyzeResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/analyze", response_model=AgentAnalyzeResponse)
async def analyze(
    request: AgentAnalyzeRequest,
    manager: StorageMCPClient = Depends(get_mcp_manager),
) -> AgentAnalyzeResponse:
    """Analyze the storage usage under ``path`` with the read-only agent.

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
        503: the MCP server is unavailable, or the chat model could not be
            constructed (for example, no provider key is configured).
    """
    settings = get_settings()

    try:
        agent = build_agent(
            model=settings.agent_model,
            manager=manager,
            temperature=settings.agent_temperature,
            max_iterations=settings.agent_max_iterations,
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
