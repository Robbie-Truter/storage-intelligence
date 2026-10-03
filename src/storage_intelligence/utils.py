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


class EmptyDirectoriesResult(TypedDict):
    """Successful `delete_empty_directories` result.

    `mode` is the discriminator: `preview` means nothing was deleted and
    `requires_confirmation` is True; `executed` means the scan ran with
    confirmation and the deleted/skipped/failed fields describe the outcome.
    Every field is always present so clients can rely on the shape, except the
    three preview-only fields, which are omitted entirely when `executed`.

    Preview-only, present only when `mode` is `preview`:
        total_empty_directories - exact count of directories that would be
            deleted. Never truncated, so it stays a cheap integer even when
            the scan matches tens of thousands of paths.
        sample - bounded excerpt of those paths. Capped because the result is
            read into the model's context; a recursive scan of the home
            directory would otherwise return the whole tree as strings.
        truncated - whether `sample` is shorter than the total. Without this an
            agent cannot tell a bounded excerpt from a complete list and may
            describe the total as though it had seen every path.

    These are omitted rather than left empty in `executed` mode, where
    `deleted_directories` already reports every affected path. An empty
    `sample` there would be ambiguous between "nothing matched", "nothing
    pending" and "not applicable", and the cheapest reading is to ignore it.
    """

    mode: Literal["preview", "executed"]
    path: str
    recursive: bool
    requires_confirmation: bool
    deleted_directories_count: int
    deleted_directories: list[str]
    skipped_directories_count: int
    skipped_directories: list[str]
    failed_directories_count: int
    failed_directories: list[str]
    total_empty_directories: NotRequired[int]
    sample: NotRequired[list[str]]
    truncated: NotRequired[bool]


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
