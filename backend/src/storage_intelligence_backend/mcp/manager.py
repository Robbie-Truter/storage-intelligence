"""Owns the FastMCP client, the LangChain MCP adapter, and the agent allowlist.

The concrete connection (``UvStdioTransport`` subprocess, reconnect handling) is
implemented here, alongside the ``MCPAdapter`` wiring that turns the same
connection into an allowlisted LangChain tool catalogue. The public surface here
is what the rest of the app depends on.

Adapter-reuse spike (the named ``langchain.mcp`` beta risk), verified live
against the MCP server and recorded here:

- ``MCPAdapter(prebuilt_client)`` does **not** hand back the caller's client
    object: our client carries no elicitation callback, so ``__init__`` clones it
    with ``client.new()`` (``langchain/mcp/adapter.py:183-194``) and arms the
    clone — ``adapter.client is client`` is ``False``.
- The clone shares the *same transport instance* (``copy.copy`` keeps it) and
    the stdio transport runs one subprocess behind both clients, so the
    connection — not the object — is what gets reused. Deterministic
    ``call_tool`` calls and the LangChain tools therefore share one subprocess.
- ``list_tools()`` enters and exits the adapter itself (``adapter.py:240``);
    the returned tools hold the adapter's client and re-enter it per call, so
    they stay callable after that exit. The adapter is additionally held on
    ``self._stack`` so its session stays open for the app lifetime, and
    ``stop()`` closes it (adapter → client → subprocess) by exit-stack LIFO.
- Conclusion: reuse works, the ``as_langchain_tool(tool, self._client)``
    fallback is not needed (it remains the escape hatch if a future ``langchain``
    release stops sharing the transport).
"""

from collections.abc import Iterable
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import UvStdioTransport
from langchain.mcp import MCPAdapter
from langchain_core.tools import BaseTool
from mcp.types import CallToolResult, TextContent

from .errors import MCPToolError, MCPUnavailable

READONLY_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "disk_usage",
        "directory_disk_usage",
        "explore_directory",
        "count_files",
        "file_info",
        "find_large_files",
        "find_duplicate_files",
        "find_stale_files",
        "find_empty_directories",
        "find_junk_files",
        "preview_trash",
    }
)


def allowlisted_tools(tools: Iterable[BaseTool]) -> dict[str, BaseTool]:
    """Keep only the tools on the allowlist, keyed by tool name.

    This is the one place the allowlist is applied: the catalogue the agent
    gets is built here, when the MCP connection is opened, so a tool that is
    not on the list - ``trash_path`` above all - never reaches the agent.
    """
    return {tool.name: tool for tool in tools if tool.name in READONLY_TOOL_ALLOWLIST}


class StorageMCPClient:
    """Manages a single MCP server connection for the lifetime of the app."""

    def __init__(self, command: str, args: list[str], project_directory: str) -> None:
        self.command = command
        self.args = args
        self.project_directory = project_directory

        self._client: Client | None = None
        self._adapter: MCPAdapter | None = None
        self._stack: AsyncExitStack | None = None
        self._tools: dict[str, Any] = {}
        self._langchain_tools: dict[str, BaseTool] = {}
        self._ready = False

    @property
    def is_ready(self) -> bool:
        """Whether the MCP connection is open and tools have been listed."""
        return self._ready and self._client is not None

    @property
    def tool_count(self) -> int:
        """Number of raw MCP tools (reported by ``/health/ready``)."""
        return len(self._tools)

    @property
    def langchain_tools(self) -> dict[str, BaseTool]:
        """Allowlisted LangChain tools for the agent, keyed by tool name.

        Only names in ``READONLY_TOOL_ALLOWLIST`` ever appear here — raw
        ``trash_path`` is filtered out during discovery, not by annotation. A
        copy is returned so callers cannot mutate the boundary.
        """
        return dict(self._langchain_tools)

    async def start(self) -> None:
        """Open the MCP connection and cache the tool catalogues.

        One connection serves both surfaces: the raw MCP tool map used by the
        deterministic ``call_tool`` path, and the allowlisted LangChain tools
        served to the agent. Connection failures propagate to the caller; the
        startup policy (fail fast vs. run degraded) belongs to the lifespan.
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

        adapter = MCPAdapter(self._client)
        self._adapter = await self._stack.enter_async_context(adapter)
        agent_tools = await self._adapter.list_tools()
        self._langchain_tools = allowlisted_tools(agent_tools)
        self._ready = True

    async def stop(self) -> None:
        """Close the MCP connection and release the subprocess.

        The exit stack unwinds in LIFO order, so the adapter (entered last)
        closes before the client, and the client before the subprocess.
        """
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._adapter = None
        self._client = None
        self._tools = {}
        self._langchain_tools = {}
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
