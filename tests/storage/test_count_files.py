"""Tests for count_files (src/storage_intelligence/tools/storage.py:173).

Implements plans/count_files.md.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import count_files

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
    a.py, b.py, C.PY, data.txt, README (no extension), sub/ignored.py
    """
    (tmp_path / "a.py").write_text("a")
    (tmp_path / "b.py").write_text("b")
    (tmp_path / "C.PY").write_text("C")
    (tmp_path / "data.txt").write_text("data")
    (tmp_path / "README").write_text("readme")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "ignored.py").write_text("ignored")
    return tmp_path


# ===============================================
# 2. Happy path: exact result shape
# ===============================================


@pytest.mark.anyio
async def test_happy_path_result_shape(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await count_files(ctx, path=str(tree))

    assert result["path"] == str(tree)
    # Subdirectory contents are ignored, so sub/ignored.py is not counted.
    assert result["total_files"] == 5
    assert result["by_extension"] == {".py": 3, ".txt": 1, "(no extension)": 1}
    # Groups always sum to total_files.
    assert sum(result["by_extension"].values()) == result["total_files"]


# ===============================================
# 3. Extension grouping: case-insensitive
# ===============================================


@pytest.mark.anyio
async def test_extensions_lowercased_group_together(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await count_files(ctx, path=str(tree))

    by_extension = result["by_extension"]
    assert ".py" in by_extension
    assert ".PY" not in by_extension
    # a.py, b.py and C.PY all land in the one lowercased ".py" group.
    assert by_extension[".py"] == 3


# ===============================================
# 4. No-extension grouping
# ===============================================


@pytest.mark.anyio
async def test_file_without_extension_grouped_by_placeholder(
    ctx: AsyncMock, tree: Path
) -> None:
    result: Any = await count_files(ctx, path=str(tree))

    assert result["by_extension"]["(no extension)"] == 1


# ===============================================
# 5. Ordering: count descending, alphabetical tie-break
# ===============================================


@pytest.mark.anyio
async def test_by_extension_sorted_count_desc_then_alphabetical(
    ctx: AsyncMock, tmp_path: Path
) -> None:
    for i in range(3):
        (tmp_path / f"l{i}.log").write_text("x")
    for name in ("one.txt", "two.txt", "a.md", "z.md"):
        (tmp_path / name).write_text("x")

    result: Any = await count_files(ctx, path=str(tmp_path))

    # .log wins on count; .md beats .txt on the alphabetical tie at count 2.
    assert list(result["by_extension"].items()) == [
        (".log", 3),
        (".md", 2),
        (".txt", 2),
    ]


# ===============================================
# 6. Empty directory
# ===============================================


@pytest.mark.anyio
async def test_empty_directory_returns_zero_and_empty_groups(
    ctx: AsyncMock, tmp_path: Path
) -> None:
    result: Any = await count_files(ctx, path=str(tmp_path))

    assert result["total_files"] == 0
    assert result["by_extension"] == {}


# ===============================================
# 7. Error path: missing path
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    result: Any = await count_files(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "count_files",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()


# ===============================================
# 8. Error path: path is a file, not a directory
# ===============================================


@pytest.mark.anyio
async def test_file_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("x")

    result: Any = await count_files(ctx, path=str(file_path))

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "count_files",
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

    result: Any = await count_files(ctx, path=str(tree))

    assert result.is_error is True
    assert result.structured_content["error"] == "unexpected_error"
    assert result.structured_content["exception_type"] == "RuntimeError"
    assert "RuntimeError" in ctx.error.await_args.args[0]


# ===============================================
# 10. ctx.info on the happy path
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_awaited_with_counting_files(ctx: AsyncMock, tree: Path) -> None:
    await count_files(ctx, path=str(tree))

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Counting files in" in message
    assert str(tree) in message
