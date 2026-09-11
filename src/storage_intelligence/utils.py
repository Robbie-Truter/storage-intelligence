from fastmcp.tools import ToolResult

# Shared helpers that convert storage failures into consistent, machine-readable
# ToolResult objects. Every tool returns these so the AI receives a uniform error
# shape it can act on instead of ad-hoc strings:
#
#   path_error()       - predictable, recoverable failures (e.g. missing path).
#                        The AI can diagnose and try an alternative.
#   unexpected_error() - genuine faults / unexpected exceptions (permissions,
#                        invalid types, filesystem issues). Signals a real defect
#                        rather than a recoverable condition.


def path_error(tool: str, path: str) -> ToolResult:
    """Build a structured error result for a missing path."""
    return ToolResult(
        content=f"Path not found: {path}",
        structured_content={"error": "path_not_found", "tool": tool, "path": path},
        is_error=True,
    )


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