---
name: fastmcp-tool-dev
description: Best practices for authoring, updating, and documenting FastMCP tools in storage-intelligence.
---

# FastMCP Tool Development Guide

This skill provides patterns and standards for building tools in `src/storage_intelligence/tools/`.

## 1. Tool Function Structure

Every tool function exposed via FastMCP should follow this pattern:

```python
from mcp.server.fastmcp import Context, FastMCP


@mcp.tool()
async def example_tool(path: str, confirm: bool = False, ctx: Context = None) -> dict:
    """Clear, concise docstring explaining what the tool does.

    Detail dry-run behavior when confirm=False vs execution when confirm=True.
    """
    try:
        # 1. Validation & Input Normalization
        if not path:
            await ctx.error("Validation failed: path is empty")
            return path_error("example_tool", path)

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
        await ctx.error(f"example_tool failed: {exc}")
        return unexpected_error("example_tool", path, exc)
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
