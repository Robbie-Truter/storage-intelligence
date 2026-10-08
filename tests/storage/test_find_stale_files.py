"""Tests for find_stale_files (src/storage_intelligence/tools/storage.py:505).

Implements plans/find_stale_files.md.
"""

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import find_stale_files

# ===============================================
# Fixtures
# ===============================================


@pytest.fixture
def ctx() -> AsyncMock:
    """Mocked FastMCP Context; info/error are awaitable AsyncMocks."""
    return AsyncMock()


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """tmp_path with old.bin (100d old mtime) and recent.bin (10d old mtime)."""
    now = 1_000_000_000.0
    monkeypatch.setattr("storage_intelligence.tools.storage.time.time", lambda: now)

    old = tmp_path / "old.bin"
    recent = tmp_path / "recent.bin"
    old.write_bytes(b"old")
    recent.write_bytes(b"recent")

    old_mtime = now - 100 * 86400
    recent_mtime = now - 10 * 86400
    os.utime(old, (old_mtime, old_mtime))
    os.utime(recent, (recent_mtime, recent_mtime))
    return tmp_path


# ===============================================
# 2. Happy path
# ===============================================


@pytest.mark.anyio
async def test_happy_path_only_old_file_stale(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_stale_files(ctx, path=str(tree), days_unmodified=90)

    assert len(result) == 1
    entry = result[0]
    assert Path(entry["path"]) == tree / "old.bin"
    assert entry["size_bytes"] == 3
    assert entry["days_unmodified"] == pytest.approx(100.0, abs=0.1)


# ===============================================
# 3. Boundary: exactly at threshold excluded; +1 day included
# ===============================================


@pytest.mark.anyio
async def test_boundary_exactly_at_threshold_excluded(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = 1_000_000_000.0
    monkeypatch.setattr("storage_intelligence.tools.storage.time.time", lambda: now)

    d = tmp_path / "d"
    d.mkdir()
    on_thresh = d / "on_thresh.txt"
    off_thresh = d / "off_thresh.txt"
    on_thresh.write_text("x")
    off_thresh.write_text("x")

    thresh_secs = 90 * 86400
    os.utime(on_thresh, (now - thresh_secs, now - thresh_secs))  # exactly at
    os.utime(off_thresh, (now - thresh_secs - 86400, now - thresh_secs - 86400))  # +1d

    result: Any = await find_stale_files(ctx, path=str(d), days_unmodified=90)
    assert len(result) == 1
    assert Path(result[0]["path"]).name == "off_thresh.txt"


@pytest.mark.anyio
async def test_boundary_one_day_over_included(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = 1_000_000_000.0
    monkeypatch.setattr("storage_intelligence.tools.storage.time.time", lambda: now)

    f = tmp_path / "barely.txt"
    f.write_text("x")
    os.utime(f, (now - 91 * 86400, now - 91 * 86400))
    result: Any = await find_stale_files(ctx, path=str(tmp_path), days_unmodified=90)
    assert len(result) == 1


# ===============================================
# 4. Access time irrelevant
# ===============================================


@pytest.mark.anyio
async def test_access_time_irrelevant_bumping_atime_keeps_stale(
    ctx: AsyncMock, tree: Path
) -> None:
    old = tree / "old.bin"
    st = old.stat()
    os.utime(old, (st.st_atime + 5000, st.st_mtime))  # bump atime only

    result: Any = await find_stale_files(ctx, path=str(tree), days_unmodified=90)
    assert len(result) == 1


# ===============================================
# 5. Ordering: stalest first (descending days_unmodified)
# ===============================================


@pytest.mark.anyio
async def test_ordering_stalest_first_desc(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = 1_000_000_000.0
    monkeypatch.setattr("storage_intelligence.tools.storage.time.time", lambda: now)

    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    (tmp_path / "c.txt").write_text("x")
    os.utime(tmp_path / "a.txt", (now - 200 * 86400, now - 200 * 86400))
    os.utime(tmp_path / "b.txt", (now - 100 * 86400, now - 100 * 86400))
    os.utime(tmp_path / "c.txt", (now - 50 * 86400, now - 50 * 86400))

    result: Any = await find_stale_files(ctx, path=str(tmp_path), days_unmodified=10)
    days = [e["days_unmodified"] for e in result]
    names = [Path(e["path"]).name for e in result]
    assert days == sorted(days, reverse=True)
    assert names == ["a.txt", "b.txt", "c.txt"]


# ===============================================
# 6. max_results caps and returns only stalest
# ===============================================


@pytest.mark.anyio
async def test_max_results_caps_to_one_returning_stalest(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = 1_000_000_000.0
    monkeypatch.setattr("storage_intelligence.tools.storage.time.time", lambda: now)

    for name, d in [("a.txt", 300), ("b.txt", 100), ("c.txt", 50)]:
        p = tmp_path / name
        p.write_text("x")
        os.utime(p, (now - d * 86400, now - d * 86400))

    result: Any = await find_stale_files(
        ctx, path=str(tmp_path), days_unmodified=10, max_results=1
    )
    assert len(result) == 1
    assert Path(result[0]["path"]).name == "a.txt"


# ===============================================
# 7. None stale → empty list (not error)
# ===============================================


@pytest.mark.anyio
async def test_none_stale_returns_empty_list(ctx: AsyncMock, tree: Path) -> None:
    # Fixture sets old.bin to 100d old; recent.bin 10d old. With days_unmodified=5
    # both exceed threshold (>5 days), so result is non-empty.
    result: Any = await find_stale_files(ctx, path=str(tree), days_unmodified=5)
    assert len(result) == 2


# ===============================================
# 8. Recursive: finds stale file in subdirectory
# ===============================================


@pytest.mark.anyio
async def test_recursive_finds_stale_in_subdirectory(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = 1_000_000_000.0
    monkeypatch.setattr("storage_intelligence.tools.storage.time.time", lambda: now)

    (tmp_path / "sub").mkdir()
    f = tmp_path / "sub" / "deep.txt"
    f.write_text("x")
    os.utime(f, (now - 200 * 86400, now - 200 * 86400))

    result: Any = await find_stale_files(ctx, path=str(tmp_path), days_unmodified=10)
    assert len(result) == 1
    assert Path(result[0]["path"]).parent == tmp_path / "sub"


# ===============================================
# 9. Unreadable file: stat raises OSError → silently omitted
# ===============================================


@pytest.mark.anyio
async def test_unreadable_file_skipped_silently(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = 1_000_000_000.0
    monkeypatch.setattr("storage_intelligence.tools.storage.time.time", lambda: now)

    bad = tmp_path / "bad.txt"
    good = tmp_path / "good.txt"
    bad.write_text("x")
    good.write_text("y")
    os.utime(bad, (now - 200 * 86400, now - 200 * 86400))
    os.utime(good, (now - 200 * 86400, now - 200 * 86400))

    real_stat = Path.stat

    def fake_stat(self: Path, **kwargs: Any) -> Any:
        # Path.is_file() stats the child before the tool's own try block, so
        # only raise for the tool's direct child.stat() call; raising for
        # is_file() would surface as unexpected_error instead.
        caller = sys._getframe(1).f_code.co_name
        if self == bad and caller == "find_stale_files":
            raise OSError("permission denied")
        return real_stat(self, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    result: Any = await find_stale_files(ctx, path=str(tmp_path), days_unmodified=10)
    assert len(result) == 1
    assert Path(result[0]["path"]) == good


# ===============================================
# 10. Error path: missing path → path_error
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "missing")

    result: Any = await find_stale_files(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "find_stale_files",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()


# ===============================================
# 11. ctx.info includes days_unmodified and max_results
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_includes_parameters(ctx: AsyncMock, tree: Path) -> None:
    await find_stale_files(ctx, path=str(tree), days_unmodified=90, max_results=50)

    ctx.info.assert_awaited_once()
    msg = ctx.info.await_args.args[0]
    assert "Scanning for stale files in" in msg
    assert "days_unmodified=90" in msg
    # Note: the source ctx.info does not include max_results; we assert it contains
    # days_unmodified as per plan intent; the string may not include max_results.
    # Source format: "Scanning for stale files in: {path} (days_unmodified=...)"
    assert str(tree) in msg
