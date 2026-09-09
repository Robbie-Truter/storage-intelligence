from storage_intelligence.core import mcp


@mcp.prompt()
def greet(name: str) -> str:
    """Generate a greeting prompt."""
    return f"Please greet the user named {name} warmly."
