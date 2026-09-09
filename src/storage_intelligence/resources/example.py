from storage_intelligence.core import mcp


@mcp.resource("info://server")
def server_info() -> dict:
    """Return basic server information."""
    return {"name": "storage-intelligence", "version": "0.1.0"}
