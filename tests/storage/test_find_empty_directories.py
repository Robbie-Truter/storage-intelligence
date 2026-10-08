"""Tests for find_empty_directories (src/storage_intelligence/tools/storage.py:570).

Implements plans/find_empty_directories.md.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import find_empty_directories

# ===============================================
# Fixtures
# ===============================================


@pytest.fixture
def ctx() -> AsyncMock:
    """Mocked FastMCP Context; info/error/warning are awaitable AsyncMocks."""
    return AsyncMock()


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """tmp_path containing:
    a/b/c (all empty), top/ (empty), full/file.txt
    """
    (tmp_path / "a" / "b" / "c").mkdir(parents=True)
    (tmp_path / "top").mkdir()
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "file.txt").write_text("x")
    return tmp_path


# ===============================================
# 2. Cascade: parents that become empty are counted
# ===============================================


@pytest.mark.anyio
async def test_cascade_counts_parents_that_become_empty(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await find_empty_directories(ctx, path=str(tree))

    assert result["total_empty_directories"] == 4
    names = {Path(d).name for d in result["sample"]}
    assert names == {"top", "a", "b", "c"}
    # `full` still holds file.txt, so it is never a candidate.
    assert not any(d.endswith("/full") for d in result["sample"])


# ===============================================
# 3. Ordering: deepest first, path tie-break
# ===============================================


@pytest.mark.anyio
async def test_sample_ordered_deepest_first(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_empty_directories(ctx, path=str(tree))

    assert result["sample"] == [
        str(tree / "a" / "b" / "c"),
        str(tree / "a" / "b"),
        str(tree / "a"),
        str(tree / "top"),
    ]


# ===============================================
# 4. path itself is never reported
# ===============================================


@pytest.mark.anyio
async def test_path_itself_never_reported(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_empty_directories(ctx, path=str(tree))

    assert str(tree) not in result["sample"]


# ===============================================
# 5. recursive=False: immediate children only
# ===============================================


@pytest.mark.anyio
async def test_non_recursive_reports_only_immediate_children(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await find_empty_directories(ctx, path=str(tree), recursive=False)

    assert result["sample"] == [str(tree / "top")]
    assert result["total_empty_directories"] == 1
    # `a` still contains `a/b`, so it is not empty at this level.
    assert not any(d.endswith("/a") for d in result["sample"])


# ===============================================
# 6. Result metadata
# ===============================================


@pytest.mark.anyio
async def test_result_echoes_path_and_recursive(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_empty_directories(ctx, path=str(tree), recursive=True)

    assert result["path"] == str(tree)
    assert result["recursive"] is True
    assert result["total_empty_directories"] == len(result["sample"])
    assert result["truncated"] is False
    assert result["skipped_directories_count"] == 0
    assert result["skipped_directories"] == []


# ===============================================
# 7. Truncation at SAMPLE_LIMIT
# ===============================================


@pytest.mark.anyio
async def test_sample_truncated_at_limit_count_still_exact(
    ctx: AsyncMock, tmp_path: Path
) -> None:
    for i in range(26):
        (tmp_path / f"empty{i:02d}").mkdir()

    result: Any = await find_empty_directories(ctx, path=str(tmp_path))

    assert len(result["sample"]) == 25
    assert result["truncated"] is True
    assert result["total_empty_directories"] == 26


# ===============================================
# 8. Unreadable directory goes to skipped_directories
# ===============================================


@pytest.mark.anyio
async def test_unreadable_directory_skipped_never_reported(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked = tree / "a" / "b"
    original_iterdir = Path.iterdir

    def iterdir(self: Path) -> Any:
        if self == blocked:
            raise PermissionError("permission denied")
        return original_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", iterdir)

    result: Any = await find_empty_directories(ctx, path=str(tree))

    assert result["skipped_directories"] == [str(blocked)]
    assert result["skipped_directories_count"] == 1
    assert str(blocked) not in result["sample"]
    # The skipped parent cannot be proven empty, so `a` is excluded too;
    # its child `a/b/c` was already examined and still counts.
    names = {Path(d).name for d in result["sample"]}
    assert "c" in names
    assert "b" not in names
    assert "a" not in names


# ===============================================
# 9. Error paths: missing and non-directory
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    result: Any = await find_empty_directories(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "find_empty_directories",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()


@pytest.mark.anyio
async def test_file_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("x")

    result: Any = await find_empty_directories(ctx, path=str(file_path))

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "find_empty_directories",
        "path": str(file_path),
    }
    ctx.error.assert_awaited_once()
    assert "not a directory" in ctx.error.await_args.args[0]


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

    result: Any = await find_empty_directories(ctx, path=str(tree))

    assert result.is_error is True
    assert result.structured_content["error"] == "unexpected_error"
    assert result.structured_content["exception_type"] == "RuntimeError"
    assert "RuntimeError" in ctx.error.await_args.args[0]


# ===============================================
# 11. ctx.info includes recursive; ctx.warning for skipped
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_includes_recursive_flag(ctx: AsyncMock, tree: Path) -> None:
    await find_empty_directories(ctx, path=str(tree), recursive=False)

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Scanning for empty directories" in message
    assert str(tree) in message
    assert "recursive=False" in message


@pytest.mark.anyio
async def test_ctx_warning_awaited_for_skipped_directory(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked = tree / "a" / "b"
    original_iterdir = Path.iterdir

    def iterdir(self: Path) -> Any:
        if self == blocked:
            raise PermissionError("permission denied")
        return original_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", iterdir)

    await find_empty_directories(ctx, path=str(tree))

    ctx.warning.assert_awaited_once()
    message = ctx.warning.await_args.args[0]
    assert str(blocked) in message
    assert "PermissionError" in message
