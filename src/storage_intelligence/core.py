from fastmcp import FastMCP
from fastmcp.apps.approval import Approval

# Create MCP instance
mcp = FastMCP("storage-intelligence")

# Add approval provider for write/delete tools
mcp.add_provider(Approval())
