from textwrap import dedent

from storage_intelligence_mcp.core import mcp


@mcp.resource(
    "storage://python",
    title="Python storage guide",
    description=(
        "Read-only guide to pip, uv, conda, virtual environments, and bytecode."
    ),
    mime_type="text/markdown",
    tags={"storage", "python", "cleanup"},
)
def python_storage_guide() -> str:
    """Return a practical guide to Python storage and safe cleanup."""
    return dedent(
        """\
        # Python storage

        Python storage is mostly package caches, virtual environments, and
        bytecode. Caches are shared across projects; virtual environments are
        per project.

        ## Inspect

        - `pip cache dir` and `pip cache info`.
        - `uv cache dir`.
        - `conda info`.
        - `du -sh .venv venv __pycache__ .pytest_cache .mypy_cache 2>/dev/null`.

        ## Package caches

        - pip: `pip cache list` shows cached wheels. `pip cache purge` clears
          everything; `pip cache remove <pattern>` removes selected entries.
          Missing wheels are downloaded again when needed.
        - uv: `uv cache prune` removes unused entries; `uv cache clean` clears
          the cache. uv recreates entries on demand.
        - conda: `conda clean --all` removes unused packages, tarballs, and
          index caches. It does not remove environments. Use
          `conda clean --tarballs --packages` for a narrower cleanup.
        - Poetry, PDM, and other tools: use their own cache commands rather
          than guessing cache paths.

        ## Project artifacts

        - `__pycache__` and `*.pyc` are compiled bytecode. They are always
          regenerable and removing them does not change source behavior.
        - `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`,
          `htmlcov/`, `build/`, `dist/`, and `*.egg-info/` are regenerable.
        - `.venv/` or `venv/` can be recreated from the project's lockfile or
          requirements. Do not delete an environment while a process uses it,
          and verify its dependencies can be reinstalled first.
        - `.tox/` and `.nox/` hold test environments. Recreate them with the
          project's test command.

        ## Never delete without investigation

        - Source files, `pyproject.toml`, lockfiles, requirements files, or
          migration and configuration data.
        - A virtual environment whose dependencies cannot be reinstalled, such
          as one using a private index or unavailable system libraries.
        - `site-packages` by hand. Remove or recreate the environment instead.
        - Cache directories while `pip`, `uv`, `conda`, or a build is running.

        ## Sources

        - https://pip.pypa.io/en/stable/cli/pip_cache/
        - https://docs.astral.sh/uv/concepts/cache/
        - https://docs.python.org/3/tutorial/modules.html#compiled-python-files
        - https://docs.conda.io/projects/conda/en/latest/commands/clean.html
        """
    )
