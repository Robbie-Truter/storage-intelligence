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
