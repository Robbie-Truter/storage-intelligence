"""Tests for find_duplicate_files (src/storage_intelligence/tools/storage.py:435).

Implements plans/find_duplicate_files.md.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp.exceptions import ToolError

from storage_intelligence.tools.storage import find_duplicate_files

# ===============================================
# Fixtures
# ===============================================


@pytest.fixture
def ctx() -> AsyncMock:
    """Mocked FastMCP Context; info/error are awaitable AsyncMocks."""
    return AsyncMock()


def write_identical_pair(directory: Path, stem: str, size: int) -> tuple[Path, Path]:
    """Create two byte-identical files of `size` bytes inside `directory`."""
    directory.mkdir(exist_ok=True)
    payload = (stem.encode() * size)[:size]
    first = directory / f"{stem}1.bin"
    second = directory / f"{stem}2.bin"
    first.write_bytes(payload)
    second.write_bytes(payload)
    return first, second


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """tmp_path containing:
    copy1.bin, copy2.bin (identical, 2048 bytes), unique.bin (3000 bytes,
    different content), sub/copy3.bin (identical to copy1/copy2).
    """
    payload = b"\xab" * 2048
    (tmp_path / "copy1.bin").write_bytes(payload)
    (tmp_path / "copy2.bin").write_bytes(payload)
    (tmp_path / "unique.bin").write_bytes(b"\xcd" * 3000)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "copy3.bin").write_bytes(payload)
    return tmp_path


# ===============================================
# 2. Happy path: one group of three
# ===============================================


@pytest.mark.anyio
async def test_happy_path_groups_identical_copies(ctx: AsyncMock, tree: Path) -> None:
    result: Any = await find_duplicate_files(ctx, path=str(tree))

    assert isinstance(result, list)
    assert len(result) == 1
    group = result[0]
    assert group["size_bytes"] == 2048
    assert sorted(Path(p).name for p in group["files"]) == [
        "copy1.bin",
        "copy2.bin",
        "copy3.bin",
    ]
    # Recursive: sub/copy3.bin is included.
    assert any(p.endswith("sub/copy3.bin") for p in group["files"])
    # unique.bin has no duplicate.
    assert not any("unique.bin" in p for p in group["files"])


# ===============================================
# 3. Ordering: groups sorted by size descending
# ===============================================


@pytest.mark.anyio
async def test_groups_sorted_by_size_descending(ctx: AsyncMock, tree: Path) -> None:
    write_identical_pair(tree, "large", 4096)

    result: Any = await find_duplicate_files(ctx, path=str(tree))

    assert len(result) == 2
    sizes = [group["size_bytes"] for group in result]
    assert sizes == sorted(sizes, reverse=True)
    assert sizes[0] == 4096
    assert sizes[1] == 2048


# ===============================================
# 4. Size floor
# ===============================================


@pytest.mark.anyio
async def test_min_size_floor_excludes_smaller_files(
    ctx: AsyncMock, tmp_path: Path
) -> None:
    write_identical_pair(tmp_path, "tiny", 100)

    default_result: Any = await find_duplicate_files(ctx, path=str(tmp_path))
    assert default_result == []

    lowered: Any = await find_duplicate_files(
        ctx, path=str(tmp_path), min_size_bytes=10
    )
    assert len(lowered) == 1
    assert lowered[0]["size_bytes"] == 100


# ===============================================
# 5. Singleton buckets are never hashed
# ===============================================


@pytest.mark.anyio
async def test_unique_file_never_reported(ctx: AsyncMock, tmp_path: Path) -> None:
    (tmp_path / "lonely.bin").write_bytes(b"\xef" * 5000)

    result: Any = await find_duplicate_files(ctx, path=str(tmp_path))

    assert result == []


# ===============================================
# 6. Recursive: pair split across subdirectories
# ===============================================


@pytest.mark.anyio
async def test_duplicate_pair_across_subdirectories(
    ctx: AsyncMock, tmp_path: Path
) -> None:
    payload = b"\x11" * 2048
    (tmp_path / "here.bin").write_bytes(payload)
    (tmp_path / "nested" / "deeper").mkdir(parents=True)
    (tmp_path / "nested" / "deeper" / "there.bin").write_bytes(payload)

    result: Any = await find_duplicate_files(ctx, path=str(tmp_path))

    assert len(result) == 1
    files = result[0]["files"]
    assert len(files) == 2
    assert any(f.endswith("here.bin") for f in files)
    assert any(f.endswith("there.bin") for f in files)


# ===============================================
# 7. Same size, different content
# ===============================================


@pytest.mark.anyio
async def test_same_size_different_content_not_grouped(
    ctx: AsyncMock, tmp_path: Path
) -> None:
    (tmp_path / "a.bin").write_bytes(b"\x01" * 2048)
    (tmp_path / "b.bin").write_bytes(b"\x02" * 2048)

    result: Any = await find_duplicate_files(ctx, path=str(tmp_path))

    assert result == []


# ===============================================
# 8. Error path: missing path
# ===============================================


@pytest.mark.anyio
async def test_missing_path_raises_tool_error(ctx: AsyncMock, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")

    with pytest.raises(ToolError, match="Path not found"):
        await find_duplicate_files(ctx, path=missing)

    ctx.error.assert_awaited_once()


# ===============================================
# 9. Error path: hash read failure skipped per file
# ===============================================


@pytest.mark.anyio
async def test_unreadable_duplicate_skipped_without_crash(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_open = Path.open

    def open_(self: Path, *args: Any, **kwargs: Any) -> Any:
        # Path.open is only used by the per-file hasher; a failure there must
        # skip the file, not abort the scan. The caller guard is file_hash.
        caller = sys._getframe(1).f_code.co_name
        if self.name == "copy1.bin" and caller == "file_hash":
            raise OSError("read failed")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_)

    result: Any = await find_duplicate_files(ctx, path=str(tree))

    # copy1.bin is skipped; copy2.bin and copy3.bin still form a group.
    assert isinstance(result, list)
    assert len(result) == 1
    names = sorted(Path(p).name for p in result[0]["files"])
    assert names == ["copy2.bin", "copy3.bin"]


@pytest.mark.anyio
async def test_all_hash_reads_failing_returns_empty(
    ctx: AsyncMock, tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def open_(self: Path, *args: Any, **kwargs: Any) -> Any:
        raise OSError("read failed")

    monkeypatch.setattr(Path, "open", open_)

    result: Any = await find_duplicate_files(ctx, path=str(tree))

    assert isinstance(result, list)
    assert result == []


# ===============================================
# 10. ctx.info includes min_size_bytes
# ===============================================


@pytest.mark.anyio
async def test_ctx_info_includes_min_size_bytes(ctx: AsyncMock, tree: Path) -> None:
    await find_duplicate_files(ctx, path=str(tree), min_size_bytes=2048)

    ctx.info.assert_awaited_once()
    message = ctx.info.await_args.args[0]
    assert "Scanning for duplicates" in message
    assert str(tree) in message
    assert "min_size_bytes=2048" in message
