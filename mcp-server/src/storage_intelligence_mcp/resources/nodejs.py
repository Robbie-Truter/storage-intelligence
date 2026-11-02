from textwrap import dedent

from storage_intelligence_mcp.core import mcp


@mcp.resource(
    "storage://nodejs",
    title="Node.js storage guide",
    description=("Read-only guide to npm, pnpm, Yarn, node_modules, and build output."),
    mime_type="text/markdown",
    tags={"storage", "nodejs", "cleanup"},
)
def nodejs_storage_guide() -> str:
    """Return a practical guide to Node.js storage and safe cleanup."""
    return dedent(
        """\
        # Node.js storage

        Node.js storage is dominated by package-manager caches and per-project
        `node_modules` and build output. Cache cleanup is global; project
        cleanup is per directory.

        ## Inspect

        - `npm config get cache` or `npm cache verify`.
        - `pnpm store path`.
        - `yarn cache dir`.
        - `du -sh node_modules dist build .next .nuxt coverage 2>/dev/null`.

        ## Package-manager caches

        - npm: run `npm cache verify` first. Use `npm cache clean --force` only
          when the cache is corrupted or space is critical; npm rebuilds it on
          demand.
        - pnpm: `pnpm store prune` removes packages no longer referenced by any
          project. Do not delete the store directory by hand.
        - Yarn: `yarn cache clean` clears the global cache. It is repopulated on
          the next install.
        - Do not remove Corepack or package-manager installations as a storage
          fix; they are small compared with caches and projects.

        ## Project cleanup

        - `node_modules` is regenerable from the lockfile. Prefer removing it
          for projects you are not actively building, then reinstall with the
          same package manager and lockfile.
        - Build output such as `dist/`, `build/`, `.next/`, `.nuxt/`,
          `coverage/`, `.vite/`, `.parcel-cache/`, `.turbo/`, and
          `*.tsbuildinfo` is regenerable.
        - Some projects store data in these directories. Check `package.json`
          scripts and `.gitignore` before deleting.
        - Close dev servers and file watchers before removing `node_modules` or
          build output.

        ## Never delete without investigation

        - Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`),
          `.env*`, source files, or test fixtures.
        - `node_modules` for a project you cannot reinstall, such as one using
          an unavailable private registry or hard-to-reproduce native builds.
        - Global installs or pnpm store contents by hand. Use the package
          manager's own command.

        ## Sources

        - https://docs.npmjs.com/cli/v11/commands/npm-cache
        - https://pnpm.io/cli/store
        - https://yarnpkg.com/cli/cache/clean
        """
    )
