"""Owns the FastMCP client, the LangChain MCP adapter, and the agent allowlist.

The concrete connection (``UvStdioTransport`` subprocess, reconnect handling) is
implemented here; the LangChain ``MCPAdapter`` wiring is added alongside the
agent in a later milestone. The public surface here is what the rest of the app
depends on.
"""

from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import UvStdioTransport
from mcp.types import CallToolResult, TextContent

from .errors import MCPToolError, MCPUnavailable

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

        self._client: Client | None = None
        self._stack: AsyncExitStack | None = None
        self._tools: dict[str, Any] = {}
        self._ready = False

    @property
    def is_ready(self) -> bool:
        """Whether the MCP connection is open and tools have been listed."""
        return self._ready and self._client is not None

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    async def start(self) -> None:
        """Open the MCP connection and cache the tool catalogue.

        Connection failures propagate to the caller; the startup policy
        (fail fast vs. run degraded) belongs to the lifespan.
        """
        transport = UvStdioTransport(
            command=self.command,
            args=self.args,
            project_directory=Path(self.project_directory),
        )
        self._client = Client(transport)
        self._stack = AsyncExitStack()
        await self._stack.enter_async_context(self._client)
        tools = await self._client.list_tools()
        self._tools = {tool.name: tool for tool in tools}
        self._ready = True

    async def stop(self) -> None:
        """Close the MCP connection and release the subprocess."""
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._client = None
        self._tools = {}
        self._ready = False

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool and return its structured content."""
        if not self.is_ready or self._client is None:
            raise MCPUnavailable("MCP server is not available")
        result = await self._client.call_tool_mcp(name, arguments)
        if result.is_error:
            raise MCPToolError(name, self._error_message(result))
        return result.structured_content

    @staticmethod
    def _error_message(result: CallToolResult) -> str:
        """Extract a human-readable message from a failed tool result."""
        for block in result.content or []:
            if isinstance(block, TextContent):
                return block.text
        return "MCP tool call failed"
