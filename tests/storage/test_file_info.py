"""Tests for file_info (src/storage_intelligence/tools/storage.py:340).

Implements plans/file_info.md.
"""

from pathlib import Path
from stat import S_IFREG
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from storage_intelligence.tools.storage import file_info

# Known byte content for note.txt, used for size_bytes assertions.
CONTENT = "hello file info"

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
    note.txt (known byte content), README (no extension),
    subdir/ containing inner.txt
    """
    (tmp_path / "note.txt").write_text(CONTENT)
    (tmp_path / "README").write_text("readme")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "inner.txt").write_text("x" * 5000)
    return tmp_path


# ===============================================
# 2. Happy path: file
# ===============================================


@pytest.mark.anyio
async def test_happy_path_file(ctx: AsyncMock, tree: Path) -> None:
    note = tree / "note.txt"

    result: Any = await file_info(ctx, path=str(note))

    assert result["name"] == "note.txt"
    assert result["path"] == str(note)
    assert result["type"] == "file"
    assert result["size_bytes"] == len(CONTENT)
    assert result["extension"] == ".txt"


# ===============================================
# 3. Happy path: directory
# ===============================================


@pytest.mark.anyio
async def test_happy_path_directory_uses_own_stat_size(
    ctx: AsyncMock, tree: Path
) -> None:
    subdir = tree / "subdir"

    result: Any = await file_info(ctx, path=str(subdir))

    assert result["name"] == "subdir"
    assert result["type"] == "directory"
    # The directory's own inode size, not the sum of its contents
    # (inner.txt alone is 5000 bytes).
    assert result["size_bytes"] == subdir.stat().st_size
    assert result["size_bytes"] < 5000


# ===============================================
# 4. Timestamps: st_mtime and st_birthtime
# ===============================================


@pytest.mark.anyio
async def test_timestamps_from_stat(ctx: AsyncMock, tree: Path) -> None:
    note = tree / "note.txt"

    result: Any = await file_info(ctx, path=str(note))

    st = note.stat()
    assert result["modified"] == pytest.approx(st.st_mtime)
    # st_birthtime exists on macOS; mirrors the source's getattr fallback.
    assert result["created"] == pytest.approx(getattr(st, "st_birthtime", st.st_ctime))


# ===============================================
# 5. Fallback: no st_birthtime → st_ctime
# ===============================================


@pytest.mark.anyio
async def test_created_falls_back_to_ctime_without_birthtime(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = tree / "note.txt"

    # A stat-like result with no st_birthtime attribute.
    def fake_stat(self: Path, **kwargs: Any) -> Any:
        return SimpleNamespace(
            st_size=42,
            st_mtime=1000.0,
            st_ctime=500.0,
            st_mode=S_IFREG | 0o644,
        )

    monkeypatch.setattr(Path, "stat", fake_stat)

    result: Any = await file_info(ctx, path=str(note))

    assert result["created"] == 500.0
    assert result["modified"] == 1000.0
    assert result["size_bytes"] == 42
    assert result["type"] == "file"


# ===============================================
# 6. No extension
# ===============================================


@pytest.mark.anyio
async def test_file_without_extension_returns_empty_string(
    ctx: AsyncMock, tree: Path
) -> None:
    readme = tree / "README"

    result: Any = await file_info(ctx, path=str(readme))

    assert result["name"] == "README"
    assert result["extension"] == ""


# ===============================================
# 7. Error path: missing path
# ===============================================


@pytest.mark.anyio
async def test_missing_path_returns_path_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    result: Any = await file_info(ctx, path=missing)

    assert result.is_error is True
    assert result.structured_content == {
        "error": "path_not_found",
        "tool": "file_info",
        "path": missing,
    }
    assert "Path not found" in result.content[0].text
    ctx.error.assert_awaited_once()


# ===============================================
# 8. Error path: Path.stat raising
# ===============================================


@pytest.mark.anyio
async def test_unexpected_error_when_stat_raises(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Path, **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "stat", boom)

    result: Any = await file_info(ctx, path=str(tree / "note.txt"))

    assert result.is_error is True
    assert result.structured_content["error"] == "unexpected_error"
    assert result.structured_content["exception_type"] == "RuntimeError"
    assert "RuntimeError" in ctx.error.await_args.args[0]


# ===============================================
# 9. ctx.info on the happy path
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_awaited_with_path(ctx: AsyncMock, tree: Path) -> None:
    note = tree / "note.txt"

    await file_info(ctx, path=str(note))

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Getting metadata for" in message
    assert str(note) in message
