"""LLM-driven agent endpoints (read-only tools only).

``POST /api/agent/analyze`` is added in a later milestone.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/agent", tags=["agent"])
