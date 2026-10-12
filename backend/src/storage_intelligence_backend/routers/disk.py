"""Deterministic disk endpoints (no LLM).

Backed directly by MCP ``call_tool_mcp``; endpoints are added in a later
milestone (usage, directory, explore, combined scan).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/disk", tags=["disk"])
