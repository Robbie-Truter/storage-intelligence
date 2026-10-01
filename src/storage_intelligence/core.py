from fastmcp import FastMCP

# from fastmcp.apps.approval import Approval

# Create MCP instance
mcp = FastMCP("storage-intelligence")

# Add approval provider for write/delete tools
# Disabled: prefab-ui is a separate package, not part of `fastmcp`, so importing
# this fails unless `fastmcp[apps]` is installed. The tools rely on their own
# `confirm` parameter for consent, which works in every MCP client.
# mcp.add_provider(Approval())
