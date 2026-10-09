"""Tests for trash_path (src/storage_intelligence/tools/cleanup.py:26).

Implements plans/trash_path.md.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fastmcp.exceptions import ToolError

from storage_intelligence.tools import cleanup
from storage_intelligence.tools.cleanup import trash_path

# ===============================================
# Fixtures
# ===============================================


@pytest.fixture
def ctx() -> AsyncMock:
    """Mocked FastMCP Context; info/warning/error are awaitable AsyncMocks."""
    return AsyncMock()


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """tmp_path containing: top.txt, sub/nested.txt, sub/deep/deeper.txt."""
    (tmp_path / "top.txt").write_text("top")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("nested")
    (tmp_path / "sub" / "deep").mkdir()
    (tmp_path / "sub" / "deep" / "deeper.txt").write_text("deeper")
    return tmp_path


@pytest.fixture
def trash(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch send2trash in cleanup's namespace; no real file reaches the trash."""
    mock = MagicMock(name="send2trash")
    monkeypatch.setattr(cleanup, "send2trash", mock)
    return mock


# ===============================================
# 2. Preview (default confirm=False)
# ===============================================


@pytest.mark.anyio
async def test_preview_default_is_dry_run(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    target = str(tree / "top.txt")

    result: Any = await trash_path(ctx, target)

    assert result["mode"] == "preview"
    assert result["requires_confirmation"] is True
    assert "confirm=True" in result["message"]
    trash.assert_not_called()
    assert (tree / "top.txt").exists()


# ===============================================
# 3. Execute a single file
# ===============================================


@pytest.mark.anyio
async def test_execute_single_file(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    target = str(tree / "top.txt")

    result: Any = await trash_path(ctx, target, confirm=True)

    assert result["mode"] == "executed"
    assert result["deleted"] == [target]
    assert result["failed"] == []
    assert result["requires_confirmation"] is False
    trash.assert_called_once_with(target)


# ===============================================
# 4. `path` and `paths` equivalence
# ===============================================


@pytest.mark.anyio
async def test_path_and_paths_give_identical_results(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    target = str(tree / "top.txt")

    single: Any = await trash_path(ctx, target, confirm=True)
    batch: Any = await trash_path(ctx, paths=[target], confirm=True)

    assert single == batch
    assert trash.call_count == 2


@pytest.mark.anyio
async def test_path_and_paths_are_combined(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    first = str(tree / "top.txt")
    second = str(tree / "sub" / "nested.txt")

    result: Any = await trash_path(ctx, first, paths=[second], confirm=True)

    assert sorted(result["paths"]) == sorted([first, second])
    assert result["total_valid_paths"] == 2
    assert trash.call_count == 2


@pytest.mark.anyio
async def test_no_targets_raises_tool_error(ctx: AsyncMock, trash: MagicMock) -> None:
    with pytest.raises(ToolError, match="No paths given"):
        await trash_path(ctx)

    ctx.error.assert_awaited_once()
    trash.assert_not_called()


# ===============================================
# 5. Deduplication
# ===============================================


@pytest.mark.anyio
async def test_duplicate_path_collapses_to_one_target(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    target = str(tree / "top.txt")

    result: Any = await trash_path(ctx, paths=[target, target], confirm=True)

    assert result["paths"] == [target]
    assert result["total_valid_paths"] == 1
    trash.assert_called_once_with(target)


# ===============================================
# 6. Mixed batch: existing + missing
# ===============================================


@pytest.mark.anyio
async def test_mixed_batch_reports_missing_and_trashes_rest(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    existing = str(tree / "top.txt")
    missing = str(tree / "gone.txt")

    result: Any = await trash_path(ctx, paths=[existing, missing], confirm=True)

    assert result["missing_paths"] == [missing]
    assert result["paths"] == [existing]
    ctx.warning.assert_awaited_once()
    trash.assert_called_once_with(existing)


# ===============================================
# 7. All-missing batch
# ===============================================


@pytest.mark.anyio
async def test_all_missing_raises_tool_error(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    missing = [str(tree / "a.txt"), str(tree / "b.txt")]

    with pytest.raises(ToolError, match="Path not found"):
        await trash_path(ctx, paths=missing, confirm=True)

    ctx.error.assert_awaited_once()
    trash.assert_not_called()


# ===============================================
# 8. Empty list
# ===============================================


@pytest.mark.anyio
async def test_empty_list_raises_tool_error(ctx: AsyncMock, trash: MagicMock) -> None:
    with pytest.raises(ToolError, match="No paths given"):
        await trash_path(ctx, paths=[])

    ctx.error.assert_awaited_once()
    trash.assert_not_called()


# ===============================================
# 9. Ordering: deepest first, alphabetical tie-break
# ===============================================


@pytest.mark.anyio
async def test_paths_ordered_deepest_first_and_trash_call_order_matches(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    deep = str(tree / "sub" / "deep" / "deeper.txt")
    nested = str(tree / "sub" / "nested.txt")
    top = str(tree / "top.txt")

    result: Any = await trash_path(ctx, paths=[top, deep, nested], confirm=True)

    assert result["paths"] == [deep, nested, top]
    assert [c.args[0] for c in trash.call_args_list] == [deep, nested, top]


@pytest.mark.anyio
async def test_equal_depth_tie_broken_alphabetically(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    (tree / "a.txt").write_text("a")
    (tree / "b.txt").write_text("b")
    first = str(tree / "a.txt")
    second = str(tree / "b.txt")

    result: Any = await trash_path(ctx, paths=[second, first], confirm=True)

    assert result["paths"] == [first, second]


# ===============================================
# 10. Directory target trashed whole
# ===============================================


@pytest.mark.anyio
async def test_directory_target_single_send2trash_call(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    target = str(tree / "sub")

    result: Any = await trash_path(ctx, target, confirm=True)

    assert result["deleted"] == [target]
    trash.assert_called_once_with(target)


# ===============================================
# 11. Partial failure
# ===============================================


@pytest.mark.anyio
async def test_partial_failure_partition_and_logging(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    good = str(tree / "top.txt")
    bad = str(tree / "sub" / "deep" / "deeper.txt")

    def fail_one(target: str) -> None:
        if target == bad:
            raise OSError("trash bin unavailable")

    trash.side_effect = fail_one

    result: Any = await trash_path(ctx, paths=[good, bad], confirm=True)

    assert result["deleted"] == [good]
    assert result["failed"] == [
        {"path": bad, "error": "OSError: trash bin unavailable"}
    ]
    ctx.error.assert_awaited_once()
    assert "OSError" in ctx.error.await_args.args[0]
    assert ctx.info.await_args_list == [call(f"Trashed: {good}")]


# ===============================================
# 12. total_valid_paths == len(paths) in both modes
# ===============================================


@pytest.mark.anyio
async def test_total_valid_paths_matches_paths_in_both_modes(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    paths = [
        str(tree / "top.txt"),
        str(tree / "sub" / "nested.txt"),
        str(tree / "sub" / "deep" / "deeper.txt"),
    ]

    preview: Any = await trash_path(ctx, paths=paths)
    executed: Any = await trash_path(ctx, paths=paths, confirm=True)

    assert preview["total_valid_paths"] == len(preview["paths"])
    assert executed["total_valid_paths"] == len(executed["paths"])


# ===============================================
# 13. Outer error: Path.exists raising
# ===============================================


@pytest.mark.anyio
async def test_unexpected_error_when_exists_raises(
    ctx: AsyncMock, tree: Path, trash: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Path) -> bool:
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "exists", boom)

    with pytest.raises(RuntimeError, match="boom"):
        await trash_path(ctx, str(tree / "top.txt"))

    ctx.error.assert_awaited_once()
    trash.assert_not_called()


# ===============================================
# 14. ctx.warning includes the ignored-path count
# ===============================================


@pytest.mark.anyio
async def test_warning_message_includes_ignored_path_count(
    ctx: AsyncMock, tree: Path, trash: MagicMock
) -> None:
    existing = str(tree / "top.txt")
    missing = [str(tree / "gone1.txt"), str(tree / "gone2.txt")]

    await trash_path(ctx, paths=[existing, *missing], confirm=True)

    ctx.warning.assert_awaited_once()
    warning = ctx.warning.await_args.args[0]
    assert f"Ignoring {len(missing)} path(s)" in warning
