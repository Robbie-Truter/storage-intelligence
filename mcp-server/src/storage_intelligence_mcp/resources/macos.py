from textwrap import dedent

from storage_intelligence_mcp.core import mcp


@mcp.resource(
    "storage://macos",
    title="macOS storage guide",
    description=("Read-only guide to common macOS storage consumers and safe cleanup."),
    mime_type="text/markdown",
    tags={"storage", "macos", "cleanup"},
)
def macos_storage_guide() -> str:
    """Return a practical guide to macOS storage and safe cleanup."""
    return dedent(
        """\
        # macOS storage

        macOS storage is a mix of user files, app data, caches, local backups,
        snapshots, and developer artifacts. Start with System Settings >
        General > Storage, then inspect large directories before deleting.

        ## Common consumers

        - `~/Library/Caches` - app caches. They regenerate, but apps may slow
          down on the next launch.
        - `~/Library/Logs` - diagnostics. Old logs are usually safe to remove.
        - `~/Library/Application Support` - app data. Many apps keep databases,
          profiles, and settings here. Do not bulk-delete.
        - `~/Library/Containers` - sandboxed app data. Some containers hold
          documents or state; inspect per app.
        - `~/Library/Application Support/MobileSync/Backup` - local iPhone and
          iPad backups. Delete only backups you no longer need.
        - `~/Library/Developer/Xcode/DerivedData` - Xcode build products and
          indexes. Regenerated on build; close Xcode first.
        - `~/Library/Developer/CoreSimulator/Devices` - simulator data. Remove
          unused simulators with Xcode or `xcrun simctl`.
        - `~/.Trash` - empty only after confirming the contents.
        - Time Machine local snapshots - APFS snapshots used for local backups.
          macOS thins them automatically when space is needed.

        ## Safe approach

        1. Review System Settings > General > Storage and its recommendations.
        2. Inspect directories with `du -sh ~/Library/* | sort -h`.
        3. Move selected files to Trash, or use this server's `preview_trash` tool
           to review them before taking action.
        4. Empty Trash only after verifying what it contains.

        ## Never delete without investigation

        - `~/Library/Application Support`, `~/Library/Containers`, or
          `~/Library/Group Containers` as a whole. They can hold active app
          data and licenses.
        - `~/Library/Keychains`, `~/Library/Mobile Documents` (iCloud Drive),
          `~/Documents`, `~/Desktop`, or `~/Pictures` by pattern.
        - `/System`, `/Library`, `/private/var/db`, and `/private/var/vm` by
          hand.
        - Time Machine snapshots or backup bundles. Use Apple's tools instead.

        ## Sources

        - https://support.apple.com/en-us/102624
        - https://support.apple.com/en-us/108809
        - https://support.apple.com/guide/mac-help/mchlp1093/mac
        - https://support.apple.com/guide/mac-help/mh35933/mac
        """
    )
