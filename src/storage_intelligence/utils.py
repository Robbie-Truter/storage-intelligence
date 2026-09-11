from fastmcp.tools import ToolResult

# Helper functions for creating ToolResult objects for missing paths and other errors.
def path_error(tool: str, path: str) -> ToolResult:
    """Build a structured error result for a missing path."""
    return ToolResult(
        content=f"Path not found: {path}",
        structured_content={"error": "path_not_found", "tool": tool, "path": path},
        is_error=True,
    )

# Helper functions for creating ToolResult objects for unexpected exceptions.
def unexpected_error(tool: str, path: str, exc: Exception) -> ToolResult:
    """Build a structured error result for any unexpected exception."""
    return ToolResult(
        content=f"{tool} failed: {type(exc).__name__}: {exc}",
        structured_content={
            "error": "unexpected_error",
            "tool": tool,
            "path": path,
            "exception_type": type(exc).__name__,
            "message": str(exc),
        },
        is_error=True,
    )