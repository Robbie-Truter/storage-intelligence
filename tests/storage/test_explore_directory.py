"""Tests for explore_directory (src/storage_intelligence/tools/storage.py:89).

Implements plans/explore_directory.md.
"""

from pathlib import Path
from typing import Any, Literal
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import explore_directory

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
    root.txt, root.log, sub/b.txt, sub/deep/c.py, emptydir/
    """
    (tmp_path / "root.txt").write_text("root")
    (tmp_path / "root.log").write_text("log")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")
    (tmp_path / "sub" / "deep").mkdir()
    (tmp_path / "sub" / "deep" / "c.py").write_text("c")
    (tmp_path / "emptydir").mkdir()
    return tmp_path


@pytest.fixture
def many_files(tmp_path: Path) -> Path:
    """A directory with exactly 6 matching files, for truncation tests."""
    d = tmp_path / "many"
    d.mkdir()
    for i in range(6):
        (d / f"f{i}.txt").write_text("x")
    return d


def entry(root: Path, rel: str, kind: Literal["file", "directory"]) -> dict[str, str]:
    """Build the expected `ExploreDirectoryEntry` for `rel` under `root`."""
    name = Path(rel).name
    label = "directory " if kind == "directory" else "file "
    return {"name": name, "path": str(root / rel), "type": label}


def sorted_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Sort entries by path so assertions are order-independent."""
    return sorted(entries, key=lambda e: e["path"])


# ===============================================
# 2. Happy path: non-recursive default
# ===============================================


@pytest.mark.anyio
async def test_happy_path_non_recursive_default(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await explore_directory(ctx, path=str(tree))

    assert result["path"] == str(tree)
    # Scan order is filesystem-defined; assert the exact set of entries.
    assert sorted_entries(result["entries"]) == [
        entry(tree, "emptydir", "directory"),
        entry(tree, "root.log", "file"),
        entry(tree, "root.txt", "file"),
        entry(tree, "sub", "directory"),
    ]
    assert result["truncated"] is False


# ===============================================
# 3. kind filters
# ===============================================


@pytest.mark.anyio
async def test_kind_files_lists_only_files(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await explore_directory(ctx, path=str(tree), kind="files")

    assert sorted_entries(result["entries"]) == [
        entry(tree, "root.log", "file"),
        entry(tree, "root.txt", "file"),
    ]
    assert result["truncated"] is False


@pytest.mark.anyio
async def test_kind_dirs_lists_only_directories(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await explore_directory(ctx, path=str(tree), kind="dirs")

    assert sorted_entries(result["entries"]) == [
        entry(tree, "emptydir", "directory"),
        entry(tree, "sub", "directory"),
    ]
    assert result["truncated"] is False


# ===============================================
# 4. pattern and search filters
# ===============================================


@pytest.mark.anyio
async def test_pattern_matches_own_name_at_any_depth(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await explore_directory(
        ctx, path=str(tree), pattern="*.py", recursive=True
    )

    assert result["entries"] == [entry(tree, "sub/deep/c.py", "file")]
    assert result["truncated"] is False


@pytest.mark.anyio
async def test_search_is_case_insensitive_substring(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await explore_directory(ctx, path=str(tree), search="ROOT")

    assert sorted_entries(result["entries"]) == [
        entry(tree, "root.log", "file"),
        entry(tree, "root.txt", "file"),
    ]
    assert result["truncated"] is False


# ===============================================
# 5. recursive uses full paths at any depth
# ===============================================


@pytest.mark.anyio
async def test_recursive_reports_full_paths(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await explore_directory(ctx, path=str(tree), recursive=True)

    assert sorted_entries(result["entries"]) == [
        entry(tree, "emptydir", "directory"),
        entry(tree, "root.log", "file"),
        entry(tree, "root.txt", "file"),
        entry(tree, "sub", "directory"),
        entry(tree, "sub/b.txt", "file"),
        entry(tree, "sub/deep", "directory"),
        entry(tree, "sub/deep/c.py", "file"),
    ]
    # `name` stays the bare filename even when the entry sits at depth.
    names = {e["name"] for e in result["entries"]}
    assert "b.txt" in names
    assert "c.py" in names
    assert result["truncated"] is False


# ===============================================
# 6 & 7. Truncation at max_results
# ===============================================


@pytest.mark.anyio
async def test_truncated_true_when_further_match_exists(
    ctx: AsyncMock, many_files: Path
) -> None:
    result: Any = await explore_directory(ctx, path=str(many_files), max_results=5)

    assert len(result["entries"]) == 5
    assert result["truncated"] is True


@pytest.mark.anyio
async def test_truncated_false_on_exact_fit(ctx: AsyncMock, many_files: Path) -> None:
    result: Any = await explore_directory(ctx, path=str(many_files), max_results=6)

    assert len(result["entries"]) == 6
    assert result["truncated"] is False


# ===============================================
# 8. Empty result
# ===============================================


@pytest.mark.anyio
async def test_filters_excluding_everything_return_empty(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await explore_directory(ctx, path=str(tree), pattern="*.nomatch")

    assert result["entries"] == []
    assert result["truncated"] is False


# ===============================================
# 9. Error path: missing path
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    result: Any = await explore_directory(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "explore_directory",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()


# ===============================================
# 10. Error path: Path.exists raising
# ===============================================


@pytest.mark.anyio
async def test_unexpected_error_when_path_check_raises(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Path) -> bool:
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "exists", boom)

    result: Any = await explore_directory(ctx, path=str(tree))

    assert result.is_error is True
    assert result.structured_content["error"] == "unexpected_error"
    assert result.structured_content["exception_type"] == "RuntimeError"
    assert "RuntimeError" in ctx.error.await_args.args[0]


# ===============================================
# 11. ctx.info on the happy path
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_awaited_with_listing_directory(
    ctx: AsyncMock, tree: Path
) -> None:
    await explore_directory(ctx, path=str(tree))

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Listing directory" in message
    assert str(tree) in message
