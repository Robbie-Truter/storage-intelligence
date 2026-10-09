---
name: fastmcp-tool-dev
description: Best practices for authoring, updating, and documenting FastMCP tools in storage-intelligence.
---

# FastMCP Tool Development Guide

This skill provides patterns and standards for building tools in `src/storage_intelligence/tools/`.

## 1. Tool Function Structure

Every tool function exposed via FastMCP should follow this pattern:

```python
from fastmcp import Context, FastMCP

from storage_intelligence.utils import path_error


@mcp.tool()
async def example_tool(path: str, confirm: bool = False, ctx: Context = None) -> dict:
    """Clear, concise docstring explaining what the tool does.

    Detail dry-run behavior when confirm=False vs execution when confirm=True.
    """
    try:
        # 1. Validation & Input Normalization
        if not path:
            raise path_error(path)

        # 2. Dry-Run / Preview Mode
        if not confirm:
            await ctx.info(f"Preview mode for path: {path}")
            return {
                "mode": "preview",
                "requires_confirmation": True,
                "target": path,
                "message": "Call with confirm=True to apply changes.",
            }

        # 3. Execution
        # Perform action...
        await ctx.info(f"Executed action on: {path}")
        return {
            "mode": "executed",
            "requires_confirmation": False,
            "target": path,
            "status": "success",
        }

    except Exception as exc:
        # Log every failure, then surface it as an MCP tool error. A re-raised
        # ToolError stays a FastMCPError and is never masked.
        await ctx.error(f"example_tool failed: {type(exc).__name__}: {exc}")
        raise
```

## 2. Context & Logging

- Always inject `ctx: Context` as a tool argument.
- Use `await ctx.info(...)`, `await ctx.warning(...)`, and `await ctx.error(...)` for rich client updates.
- Keep log messages action-oriented and clear.

## 3. Return Payload Standards

Returned payloads should always be JSON-serializable dictionaries containing:

- `"mode"`: Either `"preview"` or `"executed"`.
- `"requires_confirmation"`: `True` for dry runs, `False` for execution.
- Relevant diagnostic fields (`"paths"`, `"deleted"`, `"failed"`, `"message"`).

## 4. Error Handling

Never return an error-shaped payload (e.g. a `ToolResult` with `is_error=True` and
`structured_content`). Strict MCP clients validate `structured_content` against the
tool's success `outputSchema` even when `isError=True`, producing an opaque `-32602`;
the spec says error results MUST NOT carry `structuredContent`.

Instead, **raise** a `ToolError` (from `fastmcp.exceptions`). FastMCP converts it to a
`CallToolResult` with `isError=True` and no `structured_content`, and the message is
always passed through unmasked.

- Use the helpers in `utils.py`: `path_error(path)` for missing paths and
  `not_a_directory_error(path)` for paths that exist but are not directories. Both
  return a `ToolError`, so call sites use `raise path_error(path)`.
- Validation failures are raised directly, without a separate `ctx.error` call. Keep a
  single outer handler: `except Exception as exc:` logs via `ctx.error(...)` then
  `raise` (a bare re-raise) so the original exception propagates. This also catches
  `ToolError`, which stays a `FastMCPError` and is never masked.
- Tests assert expected errors with `pytest.raises(ToolError, match=...)` and unexpected
  errors with `pytest.raises(<OriginalException>, match=...)`.
