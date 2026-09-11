.PHONY: run inspect test

run:
	uv run storage-intelligence

inspect:
	npx @modelcontextprotocol/inspector env MCP_DEBUG=1 uv run storage-intelligence

test:
	uv run python -c "from storage_intelligence.server import mcp; print('Server loads OK')"