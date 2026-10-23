"""In-memory, path-bound preview and confirmation records.

Unused scaffolding: v1 has no preview store. The cleanup flow is frontend-driven
- the frontend submits the paths the user selected and
``POST /api/cleanup/execute`` passes them straight to MCP ``trash_path`` - so
there is no preview to record and no confirmation gate to hold. The methods
below stay unimplemented; they exist as a placeholder for a possible v2 preview
store and must not be relied on.

Note: this store is single-process only. Move to a database before running more
than one worker.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class PreviewRecord:
    """A reviewed, path-bound cleanup preview awaiting confirmation."""

    preview_id: str
    reviewed_targets: list[str]
    created_at: datetime
    expires_at: datetime
    status: str
    fingerprints: dict[str, Any]


class PreviewStore:
    """Holds short-lived preview records keyed by ``preview_id``."""

    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl_seconds = ttl_seconds
        self._records: dict[str, PreviewRecord] = {}

    def create(self, reviewed_targets: list[str]) -> PreviewRecord:
        """Store a preview built from the normalized MCP paths."""
        raise NotImplementedError("Cleanup previews implemented in a later milestone")

    def get(self, preview_id: str) -> PreviewRecord | None:
        """Return an unconsumed, unexpired record, or ``None``."""
        raise NotImplementedError("Cleanup previews implemented in a later milestone")

    def consume(self, preview_id: str) -> None:
        """Mark a record as consumed after successful execution."""
        raise NotImplementedError("Cleanup previews implemented in a later milestone")
