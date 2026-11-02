from typing import Literal

from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from storage_intelligence_mcp.core import mcp
from storage_intelligence_mcp.utils import ReadStorageGuideResult

# ===============================================
# List of storage guide tools, in the order they are implemented:
# ===============================================
# 1. read_storage_guide - read a guide for a platform or tool
# ===============================================

# Read only annotation hint, because this tool does not modify the file system
READ_ONLY = ToolAnnotations(read_only_hint=True)

StorageGuideTopic = Literal["docker", "macos", "node", "python"]

STORAGE_GUIDE_URIS: dict[StorageGuideTopic, str] = {
    "docker": "storage://docker",
    "macos": "storage://macos",
    "node": "storage://nodejs",
    "python": "storage://python",
}


# 1. read_storage_guide - read a guide for a platform or tool
@mcp.tool(annotations=READ_ONLY)
async def read_storage_guide(
    ctx: Context,
    topic: StorageGuideTopic,
) -> ReadStorageGuideResult:
    """Read a practical storage guide for Docker, macOS, Node.js, or Python.

    Use when: the user asks where a platform or tool keeps its data, what
    commonly consumes space, or what is safe to clean up. This tool returns
    documentation only; it does not inspect or change the local filesystem.

    Not for: measuring this machine's storage, finding files, or deleting
    anything. Use the analysis tools to inspect paths, preview_trash to
    review cleanup targets, and trash_path to move confirmed targets to Trash.

    Topics: `docker` reads `storage://docker`; `macos` reads
    `storage://macos`; `node` reads `storage://nodejs`; `python` reads
    `storage://python`.

    Output: the resource's `topic`, `uri`, `mime_type`, and Markdown
    `content`.

    Args:
        topic: One of `docker`, `macos`, `node`, or `python`.
    """
    uri = STORAGE_GUIDE_URIS[topic]
    await ctx.info(f"Reading storage guide for {topic}: {uri}")
    try:
        result = await mcp.read_resource(uri)

        if not result.contents:
            raise ToolError(f"No content returned for resource: {uri}")

        first = result.contents[0]
        content = first.content
        if isinstance(content, bytes):
            content = content.decode()

        await ctx.info(f"read_storage_guide completed successfully: {uri}")
        return {
            "topic": topic,
            "uri": uri,
            "mime_type": first.mime_type or "text/markdown",
            "content": content,
        }
    except Exception as exc:
        await ctx.error(f"read_storage_guide failed: {type(exc).__name__}: {exc}")
        raise
