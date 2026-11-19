"""Cooperative cancellation for scans offloaded to a worker thread."""

import asyncio
import threading

import pytest

from storage_intelligence_mcp.tools.storage import _run_scan


@pytest.mark.anyio
async def test_run_scan_returns_worker_result() -> None:
    def scan(cancel: threading.Event) -> str:
        assert not cancel.is_set()
        return "done"

    assert await _run_scan(scan) == "done"


@pytest.mark.anyio
async def test_cancelled_scan_sets_event_and_propagates_immediately() -> None:
    """Cancelling _run_scan propagates CancelledError without waiting for the
    worker thread to finish.

    Previously _run_scan awaited the thread task after setting the cancel flag,
    which blocked the event loop for the duration of the thread's current
    iteration before raising CancelledError.  The fix removes that await so
    CancelledError propagates to the caller (LangGraph) right away, while the
    worker stops cooperatively in the background once it sees the flag.

    We verify:
    1. CancelledError is raised.
    2. The cancel flag was set (the worker will stop on its own).
    3. The worker does in fact stop within a reasonable time (background drain).
    """
    started = threading.Event()
    stopped = threading.Event()
    seen_cancel: list[bool] = []

    def scan(cancel: threading.Event) -> None:
        started.set()
        while not cancel.is_set():
            threading.Event().wait(0.01)
        seen_cancel.append(True)
        stopped.set()

    task = asyncio.create_task(_run_scan(scan))

    for _ in range(100):
        if started.is_set():
            break
        await asyncio.sleep(0.01)
    assert started.is_set()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # The cancel flag must have been set so the worker stops cooperatively.
    # We do NOT assert stopped.is_set() here because _run_scan no longer
    # waits for the thread — the worker drains in the background.  Give it a
    # short window to finish so the test stays deterministic.
    for _ in range(50):
        if stopped.is_set():
            break
        await asyncio.sleep(0.02)
    assert stopped.is_set(), (
        "worker thread did not stop within 1 s after cancel flag was set"
    )
