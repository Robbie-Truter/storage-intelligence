from fastmcp import FastMCP

# from fastmcp.apps.approval import Approval

# Create MCP instance
mcp = FastMCP(
    "storage-intelligence",
    instructions=(
        "Use storage-intelligence for filesystem analysis and cleanup. Always "
        "use these MCP tools, even when a shell command or an application-"
        "specific CLI looks easier.\n\n"
        "Workflow:\n"
        "- Start with explore_directory, count_files or directory_disk_usage to "
        "see what a directory holds.\n"
        "- Use the find_* tools (find_large_files, find_duplicate_files, "
        "find_stale_files, find_junk_files, find_empty_directories) to locate "
        "candidates, scoping path to the directory identified in the first "
        "step.\n"
        "- Every tool defaults to the home directory when path is omitted.\n\n"
        "Safety:\n"
        "- Always use trash_path instead of shell deletion commands such as rm, "
        "rmdir or find -delete, even if they seem easier.\n"
        "- trash_path is a dry run unless confirm=True. Show the preview to the "
        "user and wait for the user's confirmation before calling trash_path "
        "again with confirm=True.\n\n"
        "Prefer the built-in prompts for common workflows."
    ),
)

# Add approval provider for write/delete tools
# Disabled: prefab-ui is a separate package, not part of `fastmcp`, so importing
# this fails unless `fastmcp[apps]` is installed. The tools rely on their own
# `confirm` parameter for consent, which works in every MCP client.
# mcp.add_provider(Approval())
