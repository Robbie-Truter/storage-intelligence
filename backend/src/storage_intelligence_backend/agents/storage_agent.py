"""Read-only LangChain agent over an explicit allowlist of MCP tools.

Scaffold only: the agent is built around ``langchain.mcp.MCPAdapter`` and a
provider-agnostic ``init_chat_model`` in a later milestone.
"""

from collections.abc import Sequence
from typing import Any


def build_agent(
    model: str,
    tools: Sequence[Any],
    *,
    temperature: float = 0.0,
    max_iterations: int = 10,
) -> Any:
    """Build a read-only agent bound to the given allowlisted tools."""
    raise NotImplementedError("Storage agent implemented in a later milestone")


async def run_readonly_analysis(
    agent: Any,
    path: str,
    question: str | None = None,
) -> dict[str, Any]:
    """Run the agent against ``path`` and return ``{summary, tool_calls}``."""
    raise NotImplementedError("Storage agent implemented in a later milestone")
