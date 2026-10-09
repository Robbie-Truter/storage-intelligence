"""Tests for find_junk_files (src/storage_intelligence/tools/storage.py:668).

Implements plans/find_junk_files.md.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp.exceptions import ToolError

from storage_intelligence.tools.storage import find_junk_files

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
    app.log, tmp.tmp, UPPER.LOG, notes.txt, .DS_Store,
    node_modules/, dist/, sub/
    """
    (tmp_path / "app.log").write_text("log")
    (tmp_path / "tmp.tmp").write_text("tmp")
    (tmp_path / "UPPER.LOG").write_text("upper")
    (tmp_path / "notes.txt").write_text("notes")
    (tmp_path / ".DS_Store").write_text("ds")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "dist").mkdir()
    (tmp_path / "sub").mkdir()
    return tmp_path


# ===============================================
# 2. Happy path: exact counts
# ===============================================


@pytest.mark.anyio
async def test_happy_path_counts_junk_files(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_junk_files(ctx, path=str(tree))

    assert result["path"] == str(tree)
    # app.log, tmp.tmp, UPPER.LOG, .DS_Store — notes.txt is not junk.
    assert result["total_files"] == 4
    assert result["by_extension"] == {".log": 2, ".tmp": 1, ".ds_store": 1}
    assert sum(result["by_extension"].values()) == result["total_files"]


# ===============================================
# 3. Case folding
# ===============================================


@pytest.mark.anyio
async def test_uppercase_suffix_counted_lowercased(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_junk_files(ctx, path=str(tree))

    assert result["by_extension"][".log"] == 2
    assert ".LOG" not in result["by_extension"]


# ===============================================
# 4. .DS_Store grouped by name
# ===============================================


@pytest.mark.anyio
async def test_ds_store_grouped_despite_no_suffix(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_junk_files(ctx, path=str(tree))

    assert result["by_extension"][".ds_store"] == 1


# ===============================================
# 5. by_extension ordering
# ===============================================


@pytest.mark.anyio
async def test_by_extension_sorted_count_desc_then_alphabetical(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await find_junk_files(ctx, path=str(tree))

    # .log wins on count 2; .ds_store beats .tmp on the count-1 tie.
    assert list(result["by_extension"].items()) == [
        (".log", 2),
        (".ds_store", 1),
        (".tmp", 1),
    ]


# ===============================================
# 6. Directories: sorted full paths, excluded from counts
# ===============================================


@pytest.mark.anyio
async def test_junk_directories_sorted_full_paths(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_junk_files(ctx, path=str(tree))

    assert result["directories"] == [
        str(tree / "dist"),
        str(tree / "node_modules"),
    ]
    # sub/ is a normal directory, not a junk name.
    assert not any(d.endswith("/sub") for d in result["directories"])
    # Directory names never contribute to file counts.
    assert result["total_files"] == 4


# ===============================================
# 7. Non-recursion
# ===============================================


@pytest.mark.anyio
async def test_nested_junk_directory_not_matched(ctx: AsyncMock, tree: Path) -> None:
    (tree / "sub" / "node_modules").mkdir()

    result: Any = await find_junk_files(ctx, path=str(tree))

    assert result["directories"] == [
        str(tree / "dist"),
        str(tree / "node_modules"),
    ]


# ===============================================
# 8. Empty directory
# ===============================================


@pytest.mark.anyio
async def test_empty_directory_returns_zero_result(
    ctx: AsyncMock, tmp_path: Path
) -> None:
    result: Any = await find_junk_files(ctx, path=str(tmp_path))

    assert result["path"] == str(tmp_path)
    assert result["total_files"] == 0
    assert result["by_extension"] == {}
    assert result["directories"] == []
    assert result["sample"] == []
    assert result["truncated"] is False


# ===============================================
# 9. Truncation at SAMPLE_LIMIT
# ===============================================


@pytest.mark.anyio
async def test_sample_truncated_but_count_exact(ctx: AsyncMock, tmp_path: Path) -> None:
    for i in range(26):
        (tmp_path / f"junk{i:02d}.log").write_text("x")

    result: Any = await find_junk_files(ctx, path=str(tmp_path))

    assert len(result["sample"]) == 25
    assert result["total_files"] == 26
    assert result["truncated"] is True
    assert sum(result["by_extension"].values()) == 26


# ===============================================
# 10. Error paths: missing and non-directory
# ===============================================


@pytest.mark.anyio
async def test_missing_path_raises_tool_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    with pytest.raises(ToolError, match="Path not found"):
        await find_junk_files(ctx, path=missing)

    ctx.error.assert_awaited_once()


@pytest.mark.anyio
async def test_file_path_raises_not_a_directory(ctx: AsyncMock, tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("x")

    with pytest.raises(ToolError, match="Not a directory"):
        await find_junk_files(ctx, path=str(file_path))

    ctx.error.assert_awaited_once()
    assert "Not a directory" in ctx.error.await_args.args[0]


# ===============================================
# 11. Error path: iteration raises
# ===============================================


@pytest.mark.anyio
async def test_unexpected_error_when_iterdir_raises(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Path) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "iterdir", boom)

    with pytest.raises(RuntimeError, match="boom"):
        await find_junk_files(ctx, path=str(tree))

    assert "RuntimeError" in ctx.error.await_args.args[0]


# ===============================================
# 12. ctx.info on the happy path
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_awaited_on_happy_path(ctx: AsyncMock, tree: Path) -> None:
    await find_junk_files(ctx, path=str(tree))

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Counting junk files" in message
    assert str(tree) in message
