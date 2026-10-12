"""Cleanup preview and confirmed-execution endpoints.

Preview/execute flow is added in a later milestone. The execute endpoint will
take only a ``preview_id`` plus an explicit ``confirm`` flag; paths are never
accepted from the client.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/cleanup", tags=["cleanup"])
