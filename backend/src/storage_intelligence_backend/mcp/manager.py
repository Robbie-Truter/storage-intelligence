"""Owns the FastMCP client, the LangChain MCP adapter, and the agent allowlist.

Scaffold only: the concrete connection logic (``UvStdioTransport`` subprocess,
``MCPAdapter`` wiring, reconnect handling) is implemented in a later milestone.
The public surface here is what the rest of the app depends on.
"""

from typing import Any

from .errors import MCPUnavailable

# Explicit allowlist of read-only tools the LangChain agent may call.
# ``trash_path`` is intentionally excluded: annotations describe behaviour,
# they are not a security boundary.
READONLY_TOOL_ALLOWLIST: frozenset[str] = frozenset()


class StorageMCPClient:
    """Manages a single MCP server connection for the lifetime of the app."""

    def __init__(self, command: str, args: list[str], project_directory: str) -> None:
        self.command = command
        self.args = args
        self.project_directory = project_directory
        self._tools: dict[str, Any] = {}

    @property
    def is_ready(self) -> bool:
        """Whether the MCP connection is open and tools have been listed."""
        raise NotImplementedError("MCP manager implemented in a later milestone")

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    async def start(self) -> None:
        """Open the MCP connection and cache the tool catalogue."""
        raise NotImplementedError("MCP manager implemented in a later milestone")

    async def stop(self) -> None:
        """Close the MCP connection and release the subprocess."""
        raise NotImplementedError("MCP manager implemented in a later milestone")

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool and return its structured content."""
        if not self.is_ready:
            raise MCPUnavailable("MCP server is not available")
        raise NotImplementedError("MCP manager implemented in a later milestone")
