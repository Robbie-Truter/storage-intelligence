.PHONY: run inspect inspect-tools inspect-prompts test

run:
	uv run storage-intelligence

inspect:
	npx @modelcontextprotocol/inspector env MCP_DEBUG=1 uv run storage-intelligence

inspect-tools:
	npx @modelcontextprotocol/inspector --cli uv run storage-intelligence --method tools/list

inspect-prompts:
	npx @modelcontextprotocol/inspector --cli uv run storage-intelligence --method prompts/list

test:
	pytest tests/storage -vv