"""Tests for find_large_files (src/storage_intelligence/tools/storage.py:382).

Implements plans/find_large_files.md.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import find_large_files

MIB = 1024 * 1024

# ===============================================
# Fixtures
# ===============================================


@pytest.fixture
def ctx() -> AsyncMock:
    """Mocked FastMCP Context; info/error are awaitable AsyncMocks."""
    return AsyncMock()


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """tmp_path containing:
    exact.bin (exactly 1 MiB), under.bin (1 MiB - 1), big.bin (3 MiB),
    sub/nested.bin (2 MiB)
    """
    (tmp_path / "exact.bin").write_bytes(b"\x00" * (1 * MIB))
    (tmp_path / "under.bin").write_bytes(b"\x00" * (1 * MIB - 1))
    (tmp_path / "big.bin").write_bytes(b"\x00" * (3 * MIB))
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.bin").write_bytes(b"\x00" * (2 * MIB))
    return tmp_path


# ===============================================
# 2. Boundary: threshold is inclusive
# ===============================================


@pytest.mark.anyio
async def test_threshold_boundary_inclusive(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_large_files(ctx, path=str(tree), min_size_mb=1.0)

    paths = [Path(e["path"]).name for e in result]
    assert "exact.bin" in paths
    assert "under.bin" not in paths


# ===============================================
# 3. Ordering: largest first
# ===============================================


@pytest.mark.anyio
async def test_results_sorted_largest_first(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_large_files(ctx, path=str(tree), min_size_mb=1.0)

    names = [Path(e["path"]).name for e in result]
    assert names == ["big.bin", "nested.bin", "exact.bin"]
    sizes = [e["size_bytes"] for e in result]
    assert sizes == sorted(sizes, reverse=True)


# ===============================================
# 4. Recursion: nested file found
# ===============================================


@pytest.mark.anyio
async def test_nested_file_found_at_depth(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_large_files(ctx, path=str(tree), min_size_mb=1.0)

    nested = [e for e in result if e["path"].endswith("sub/nested.bin")]
    assert len(nested) == 1
    assert nested[0]["size_bytes"] == 2 * MIB


# ===============================================
# 5. max_results slicing
# ===============================================


@pytest.mark.anyio
async def test_max_results_one_returns_largest(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_large_files(
        ctx, path=str(tree), min_size_mb=1.0, max_results=1
    )

    assert len(result) == 1
    assert Path(result[0]["path"]).name == "big.bin"


@pytest.mark.anyio
async def test_max_results_two_returns_two(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_large_files(
        ctx, path=str(tree), min_size_mb=1.0, max_results=2
    )

    assert len(result) == 2
    assert [Path(e["path"]).name for e in result] == ["big.bin", "nested.bin"]


# ===============================================
# 6. size_mb rounded to one decimal
# ===============================================


@pytest.mark.anyio
async def test_size_mb_rounded_to_one_decimal(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_large_files(ctx, path=str(tree), min_size_mb=1.0)

    big = next(e for e in result if Path(e["path"]).name == "big.bin")
    assert big["size_bytes"] == 3145728
    assert big["size_mb"] == 3.0


# ===============================================
# 7. No matches returns an empty list, not an error
# ===============================================


@pytest.mark.anyio
async def test_no_matches_returns_empty_list(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_large_files(ctx, path=str(tree), min_size_mb=100.0)

    assert result == []
    ctx.error.assert_not_awaited()


# ===============================================
# 8. Unreadable file skipped silently
# ===============================================


@pytest.mark.anyio
async def test_unreadable_file_skipped(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_stat = Path.stat

    def stat(self: Path, *args: Any, **kwargs: Any) -> Any:
        # Path.is_file() stats the child before the tool's own try block, so
        # only raise for the tool's direct child.stat() call (storage.py:416);
        # raising for is_file() would surface as unexpected_error instead.
        caller = sys._getframe(1).f_code.co_name
        if self.name == "big.bin" and caller == "find_large_files":
            raise OSError("permission denied")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)

    result: Any = await find_large_files(ctx, path=str(tree), min_size_mb=1.0)

    names = [Path(e["path"]).name for e in result]
    assert "big.bin" not in names
    assert "nested.bin" in names
    assert "exact.bin" in names


# ===============================================
# 9. Error path: missing path
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    result: Any = await find_large_files(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "find_large_files",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()


# ===============================================
# 10. Error path: rglob raises
# ===============================================


@pytest.mark.anyio
async def test_unexpected_error_when_rglob_raises(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Path, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "rglob", boom)

    result: Any = await find_large_files(ctx, path=str(tree), min_size_mb=1.0)

    assert result.is_error is True
    assert result.structured_content["error"] == "unexpected_error"
    assert result.structured_content["exception_type"] == "RuntimeError"
    assert "RuntimeError" in ctx.error.await_args.args[0]


# ===============================================
# 11. ctx.info includes threshold and max_results
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_includes_threshold_and_max_results(
    ctx: AsyncMock, tree: Path
) -> None:
    await find_large_files(ctx, path=str(tree), min_size_mb=2.5, max_results=7)

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Searching for files > 2.5 MB" in message
    assert str(tree) in message
    assert "max_results=7" in message
