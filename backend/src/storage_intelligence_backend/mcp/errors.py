"""Error types raised by the MCP integration layer."""

from typing import Any


class MCPError(Exception):
    """Base class for MCP integration errors."""


class MCPUnavailable(MCPError):
    """The MCP server could not be reached or disconnected."""


class MCPToolError(MCPError):
    """An MCP tool call returned an error result."""

    def __init__(self, tool: str, message: str) -> None:
        self.tool = tool
        self.message = message
        super().__init__(f"{tool}: {message}")

    def to_detail(self) -> dict[str, Any]:
        return {"tool": self.tool, "message": self.message}
