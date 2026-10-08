"""Tests for get_disk_usage (src/storage_intelligence/tools/storage.py:301).

Implements plans/get_disk_usage.md.
"""

import shutil
from collections import namedtuple
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import get_disk_usage

# shutil.disk_usage returns a named 3-tuple; the tool only reads
# .total/.used/.free, so a local stand-in is enough for mocking.
Usage = namedtuple("Usage", ["total", "used", "free"])

# ===============================================
# Fixtures
# ===============================================


@pytest.fixture
def ctx() -> AsyncMock:
    """Mocked FastMCP Context; info/error are awaitable AsyncMocks."""
    return AsyncMock()


def patch_disk_usage(monkeypatch: pytest.MonkeyPatch, usage: Usage) -> None:
    """Make shutil.disk_usage return `usage` for any path."""
    monkeypatch.setattr(shutil, "disk_usage", lambda *_: usage)


# ===============================================
# 2. Happy path: exact values
# ===============================================


@pytest.mark.anyio
async def test_happy_path_exact_values(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_disk_usage(monkeypatch, Usage(total=1000, used=600, free=400))

    result: Any = await get_disk_usage(ctx, path=str(tmp_path))

    assert set(result) == {
        "path",
        "total_bytes",
        "used_bytes",
        "free_bytes",
        "usage_percent",
    }
    assert result["total_bytes"] == 1000
    assert result["used_bytes"] == 600
    assert result["free_bytes"] == 400
    assert result["usage_percent"] == 60.0


# ===============================================
# 3. Rounding to one decimal
# ===============================================


@pytest.mark.anyio
async def test_usage_percent_rounded_to_one_decimal(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_disk_usage(monkeypatch, Usage(total=3, used=1, free=2))

    result: Any = await get_disk_usage(ctx, path=str(tmp_path))

    assert result["usage_percent"] == 33.3


# ===============================================
# 4. Zero-size volume
# ===============================================


@pytest.mark.anyio
async def test_zero_total_volume_reports_zero_percent(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_disk_usage(monkeypatch, Usage(total=0, used=0, free=0))

    result: Any = await get_disk_usage(ctx, path=str(tmp_path))

    assert result["usage_percent"] == 0.0
    assert result["total_bytes"] == 0
    assert result["used_bytes"] == 0
    assert result["free_bytes"] == 0


# ===============================================
# 5. path echo
# ===============================================


@pytest.mark.anyio
async def test_path_echoes_passed_path_not_volume_root(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_disk_usage(monkeypatch, Usage(total=1000, used=600, free=400))

    result: Any = await get_disk_usage(ctx, path=str(tmp_path))

    assert result["path"] == str(tmp_path)


# ===============================================
# 6. Error path: missing path
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []

    def spy(*args: Any) -> Usage:
        calls.append(args)
        return Usage(1000, 600, 400)

    monkeypatch.setattr(shutil, "disk_usage", spy)

    missing = str(tmp_path / "does-not-exist")
    result: Any = await get_disk_usage(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "get_disk_usage",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()
    # Checked before disk_usage is consulted.
    assert calls == []


# ===============================================
# 7. Error path: disk_usage raises
# ===============================================


@pytest.mark.anyio
async def test_disk_usage_failure_returns_unexpected_error(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: Any) -> Usage:
        raise OSError("device unavailable")

    monkeypatch.setattr(shutil, "disk_usage", boom)

    result: Any = await get_disk_usage(ctx, path=str(tmp_path))

    assert result.is_error is True
    assert result.structured_content["error"] == "unexpected_error"
    assert result.structured_content["exception_type"] == "OSError"
    assert "OSError" in result.content[0].text
    ctx.error.assert_awaited_once()


# ===============================================
# 8. ctx.info with the path
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_awaited_with_path(
    ctx: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_disk_usage(monkeypatch, Usage(total=1000, used=600, free=400))

    await get_disk_usage(ctx, path=str(tmp_path))

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Getting disk usage" in message
    assert str(tmp_path) in message
