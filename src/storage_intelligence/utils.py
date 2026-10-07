from typing import Literal, NotRequired, TypedDict

from fastmcp.tools import ToolResult

# Shared response shapes for the storage tools.
#
# Success is described by a TypedDict, because FastMCP derives the tool's
# advertised output schema from the return annotation. An annotation of
# `dict | str | ToolResult` yields NO output schema at all: any `ToolResult`
# member suppresses the entire union, so the model is told nothing about the
# response shape. Errors are the opposite case -- they stay `ToolResult`, and
# `convert_result()` passes those through before any schema coercion, so the
# annotation only needs to describe the success path.
#
#   path_error()       - predictable, recoverable failures (e.g. missing path).
#                        The AI can diagnose and try an alternative.
#   unexpected_error() - genuine faults / unexpected exceptions (permissions,
#                        invalid types, filesystem issues). Signals a real defect
#                        rather than a recoverable condition.


class FindEmptyDirectoriesResult(TypedDict):
    """Successful `find_empty_directories` result.

    Read-only counterpart to `delete_empty_directories`: it reports what *would*
    be deleted, including the parent directories that only become empty once
    their children are removed, without touching the filesystem.

        path - the root that was searched.
        recursive - whether subdirectories were searched at all depth.
        total_empty_directories - exact count of directories that would be
            deleted. Never truncated, so it stays a cheap integer even when the
            scan matches tens of thousands of paths.
        sample - bounded excerpt of those paths, deepest first. Capped because
            the result is read into the model's context; a recursive scan of
            the home directory would otherwise return the whole tree as strings.
        truncated - whether `sample` is shorter than the total. Without this an
            agent cannot tell a bounded excerpt from a complete list and may
            describe the total as though it had seen every path.
        skipped_directories_count - directories that could not be read, most
            often due to permissions. Reported here so the agent learns it will
            need Full Disk Access (or similar) *before* deleting, rather than
            discovering an under-deleting run afterwards.
        skipped_directories - the unreadable paths.
    """

    path: str
    recursive: bool
    total_empty_directories: int
    sample: list[str]
    truncated: bool
    skipped_directories_count: int
    skipped_directories: list[str]


class TrashPathResult(TypedDict):
    """Successful `trash_path` result.

    `mode` is the discriminator: `preview` means nothing was trashed and
    `requires_confirmation` is True; `executed` means the targets were sent to
    the trash and `deleted`/`failed` describe the outcome.

        paths - the targets that existed, deepest path first. Present in both
            modes so the two can be compared directly: in `executed` it is the
            set that was attempted, and `deleted` + `failed` partitions it.
        missing_paths - targets that did not exist. Tolerated rather than fatal,
            because one stale path should not abort a batch, but always reported
            so the caller can tell a shorter delete from a failed one.
        total_valid_paths - how many targets existed, i.e. len(paths).

    Present only when `mode` is `executed`:
        deleted - targets actually sent to the trash.
        failed - targets that raised, each with its error. A path can land here
            because send2trash rejected it, not because it still exists.

    Present only when `mode` is `preview`:
        message - what to do next, so the agent does not have to infer it.
    """

    mode: Literal["preview", "executed"]
    requires_confirmation: bool
    paths: list[str]
    missing_paths: list[str]
    total_valid_paths: int
    deleted: NotRequired[list[str]]
    failed: NotRequired[list[dict]]
    message: NotRequired[str]


class CountFilesResult(TypedDict):
    """Successful `count_files` result.

    Non-recursive snapshot of the files directly inside the directory.

        total_files - how many files matched, before grouping.
        by_extension - count per lowercased extension, largest count first.
            Files without an extension group under "(no extension)" so the
            groups still add up to `total_files`.
    """

    total_files: int
    by_extension: dict[str, int]


class DirectoryUsageEntry(TypedDict):
    """One child in the `directory_disk_usage` ranking, largest first.

    name - the child's bare name, not a path.
    type - "file" or "directory". For a directory the size covers its
        whole subtree, not the entry itself.
    size_bytes - apparent size: `st_size` for a file, the recursive
        total for a directory.
    """

    name: str
    type: Literal["file", "directory"]
    size_bytes: int


class GetDiskUsageResult(TypedDict):
    """Successful `get_disk_usage` result.

    Figures describe the whole volume, not the directory that was passed in.

        path - the path whose volume was measured.
        total_bytes / used_bytes / free_bytes - the raw `shutil.disk_usage`
            figures for that volume.
        usage_percent - used divided by total, rounded to one decimal, or
            0.0 for a zero-size volume.
    """

    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float


class FileInfoResult(TypedDict):
    """Successful `file_info` result.

    name / path - the entry's bare name and absolute path.
    type - "file" or "directory".
    size_bytes - the entry's own size. For a directory this is the small
        platform-dependent inode size, not its contents' total.
    modified - `st_mtime` as a Unix timestamp.
        created - creation time as a Unix timestamp. Prefers the platform's
            birth time (`st_birthtime` on macOS); falls back to `st_ctime`
            where none exists -- creation time on Windows, last metadata
            change on Linux.
    extension - suffix including the dot, or "" when there is none.
    """

    name: str
    path: str
    type: Literal["file", "directory"]
    size_bytes: int
    modified: float
    created: float
    extension: str


class LargeFileEntry(TypedDict):
    """One file in the `find_large_files` listing, largest first.

    path - absolute path of the file.
    size_bytes - apparent size used against the threshold.
    size_mb - size in mebibytes rounded to one decimal, so the reader
        does not have to convert the raw figure itself.
    """

    path: str
    size_bytes: int
    size_mb: float


class DuplicateFileGroup(TypedDict):
    """One group of byte-identical files from `find_duplicate_files`.

    size_bytes - the size every member of the group shares; groups are
        ordered by it, largest first.
    files - absolute paths of the identical copies, at least two. Which
        copy to keep is a judgement call left to the caller.
    """

    size_bytes: int
    files: list[str]


class StaleFileEntry(TypedDict):
    """One file in the `find_stale_files` listing, stalest first.

    path - absolute path of the file.
    size_bytes - apparent size of the file.
    days_unmodified - days since `st_mtime`, rounded to one decimal.
    """

    path: str
    size_bytes: int
    days_unmodified: float


class FindJunkFilesResult(TypedDict):
    """Successful `find_junk_files` result.

    path - the directory that was inspected (direct children only).
    total_files - how many junk files matched; never truncated.
    by_extension - count per matching suffix, largest count first.
        `.DS_Store` files group under ".ds_store" because a leading-dot
        name has no suffix to match on.
    sample - the first matching paths, capped at SAMPLE_LIMIT so the
        result can be handed straight to `trash_path`.
    truncated - whether `sample` is shorter than `total_files`. Without
        it an excerpt is indistinguishable from a complete list.
    """

    path: str
    total_files: int
    by_extension: dict[str, int]
    sample: list[str]
    truncated: bool


def path_error(tool: str, path: str) -> ToolResult:
    """Build a structured error result for a missing path."""
    return ToolResult(
        content=f"Path not found: {path}",
        structured_content={"error": "path_not_found", "tool": tool, "path": path},
        is_error=True,
    )


def unexpected_error(tool: str, path: str, exc: Exception) -> ToolResult:
    """Build a structured error result for any unexpected exception."""
    return ToolResult(
        content=f"{tool} failed: {type(exc).__name__}: {exc}",
        structured_content={
            "error": "unexpected_error",
            "tool": tool,
            "path": path,
            "exception_type": type(exc).__name__,
            "message": str(exc),
        },
        is_error=True,
    )
