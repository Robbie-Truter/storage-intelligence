.PHONY: run inspect test

run:
	uv run storage-intelligence

inspect:
	npx @modelcontextprotocol/inspector env MCP_DEBUG=1 uv run storage-intelligence

test:
	pytest tests/storage