from storage_intelligence.core import mcp


@mcp.tool()
def hello_world(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"
