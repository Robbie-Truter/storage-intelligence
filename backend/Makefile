.PHONY: run dev test lint format typecheck check

run:
	uv run storage-intelligence-backend

dev:
	uv run python -m debugpy --listen 5679 -m uvicorn storage_intelligence_backend.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check --fix

format:
	uv run ruff format

typecheck:
	uv run pyright

check: lint format typecheck test
