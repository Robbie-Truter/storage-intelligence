"""Read-only LangChain agent over an explicit allowlist of MCP tools.

The tool catalogue is composed from the MCP server's allowlisted tools. The
agent sees only the tools in ``READONLY_TOOL_ALLOWLIST`` (including the MCP
server's ``preview_trash`` tool), and never the raw ``trash_path`` tool. The
agent itself (``build_agent`` / ``run_readonly_analysis``) is built in a later
milestone.
"""

from collections.abc import Sequence
from typing import Any, Protocol

from langchain_core.tools import BaseTool

from ..mcp.manager import READONLY_TOOL_ALLOWLIST


class MCPToolSource(Protocol):
    """The slice of the MCP manager the agent tool map is built from."""

    @property
    def langchain_tools(self) -> dict[str, BaseTool]:
        """Allowlisted LangChain tools exposed by the manager."""
        ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool and return its structured content."""
        ...


def build_agent_tool_map(manager: MCPToolSource) -> dict[str, BaseTool]:
    """Compose the agent's tool map from the allowlisted MCP tools.

    The allowlist filter is applied here as well as in the manager, so a tool
    outside ``READONLY_TOOL_ALLOWLIST`` (``trash_path`` above all) can never
    reach the agent even if the manager's map is widened later.
    """
    tools = {
        name: tool
        for name, tool in manager.langchain_tools.items()
        if name in READONLY_TOOL_ALLOWLIST
    }
    return tools


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
