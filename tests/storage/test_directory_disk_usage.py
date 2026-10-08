"""Tests for directory_disk_usage (src/storage_intelligence/tools/storage.py:221).

Implements plans/directory_disk_usage.md.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import directory_disk_usage

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
    big.bin (2000 bytes), small.bin (100 bytes),
    dirA/{one.bin, two.bin} (1000 bytes total), dirA/nested/deep.bin (500 bytes),
    empty/
    """
    (tmp_path / "big.bin").write_bytes(b"x" * 2000)
    (tmp_path / "small.bin").write_bytes(b"x" * 100)
    dir_a = tmp_path / "dirA"
    dir_a.mkdir()
    (dir_a / "one.bin").write_bytes(b"x" * 600)
    (dir_a / "two.bin").write_bytes(b"x" * 400)
    (dir_a / "nested").mkdir()
    (dir_a / "nested" / "deep.bin").write_bytes(b"x" * 500)
    (tmp_path / "empty").mkdir()
    return tmp_path


# ===============================================
# 2. Happy path: descending order of direct children
# ===============================================


@pytest.mark.anyio
async def test_happy_path_sorted_largest_first(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await directory_disk_usage(ctx, path=str(tree))

    assert result["path"] == str(tree)
    names = [entry["name"] for entry in result["entries"]]
    assert names == ["big.bin", "dirA", "small.bin", "empty"]
    sizes = [entry["size_bytes"] for entry in result["entries"]]
    assert sizes == sorted(sizes, reverse=True)
    assert sizes == [2000, 1500, 100, 0]
    assert [entry["type"] for entry in result["entries"]] == [
        "file",
        "directory",
        "file",
        "directory",
    ]


# ===============================================
# 3. Subtree sum for directories
# ===============================================


@pytest.mark.anyio
async def test_directory_size_includes_whole_subtree(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await directory_disk_usage(ctx, path=str(tree))

    dir_a = next(e for e in result["entries"] if e["name"] == "dirA")
    # 600 + 400 at the top level plus 500 in nested/deep.bin.
    assert dir_a["size_bytes"] == 1500


# ===============================================
# 4. Direct children only
# ===============================================


@pytest.mark.anyio
async def test_nested_directory_is_never_an_entry(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await directory_disk_usage(ctx, path=str(tree))

    names = [entry["name"] for entry in result["entries"]]
    assert "nested" not in names
    assert "deep.bin" not in names
    assert len(names) == 4


# ===============================================
# 5. top_n slicing
# ===============================================


@pytest.mark.anyio
async def test_top_n_limits_entries(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await directory_disk_usage(ctx, path=str(tree), top_n=1)

    assert len(result["entries"]) == 1
    assert result["entries"][0]["name"] == "big.bin"


@pytest.mark.anyio
async def test_top_n_larger_than_child_count_returns_all(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await directory_disk_usage(ctx, path=str(tree), top_n=100)

    assert len(result["entries"]) == 4


# ===============================================
# 6. Unreadable file skipped silently
# ===============================================


@pytest.mark.anyio
async def test_unreadable_file_skipped(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_stat = Path.stat

    def stat(self: Path, *args: Any, **kwargs: Any) -> Any:
        # Path.is_file() stats the child before the tool's own try block, so
        # only raise for the tool's direct child.stat() call (storage.py:270);
        # raising for is_file() would surface as unexpected_error instead.
        caller = sys._getframe(1).f_code.co_name
        if self.name == "big.bin" and caller == "directory_disk_usage":
            raise OSError("permission denied")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)

    result: Any = await directory_disk_usage(ctx, path=str(tree))

    assert result["path"] == str(tree)
    names = [entry["name"] for entry in result["entries"]]
    assert "big.bin" not in names
    assert "small.bin" in names
    assert "dirA" in names
    assert names == ["dirA", "small.bin", "empty"]


# ===============================================
# 7. Broken symlink skipped
# ===============================================


@pytest.mark.anyio
async def test_broken_symlink_skipped(ctx: AsyncMock, tree: Path) -> None:
    (tree / "dangling").symlink_to(tree / "missing-target")

    result: Any = await directory_disk_usage(ctx, path=str(tree))

    names = [entry["name"] for entry in result["entries"]]
    assert "dangling" not in names
    # No zero-byte placeholder entry stands in for the skipped link.
    assert len(names) == 4


# ===============================================
# 8. Error paths: missing and non-directory
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    result: Any = await directory_disk_usage(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "directory_disk_usage",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()


@pytest.mark.anyio
async def test_file_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("x")

    result: Any = await directory_disk_usage(ctx, path=str(file_path))

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "directory_disk_usage",
        "path": str(file_path),
    }
    ctx.error.assert_awaited_once()
    assert "not a directory" in ctx.error.await_args.args[0]


# ===============================================
# 9. Error path: iteration raises
# ===============================================


@pytest.mark.anyio
async def test_unexpected_error_when_iterdir_raises(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Path) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "iterdir", boom)

    result: Any = await directory_disk_usage(ctx, path=str(tree))

    assert result.is_error is True
    assert result.structured_content["error"] == "unexpected_error"
    assert result.structured_content["exception_type"] == "RuntimeError"
    assert "RuntimeError" in ctx.error.await_args.args[0]


# ===============================================
# 10. ctx.info includes top_n
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_includes_top_n(ctx: AsyncMock, tree: Path) -> None:
    await directory_disk_usage(ctx, path=str(tree), top_n=3)

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Computing recursive disk usage" in message
    assert str(tree) in message
    assert "top_n=3" in message
