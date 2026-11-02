from textwrap import dedent

from storage_intelligence_mcp.core import mcp


@mcp.resource(
    "storage://docker",
    title="Docker storage guide",
    description=(
        "Read-only guide to Docker images, containers, volumes, and build cache."
    ),
    mime_type="text/markdown",
    tags={"storage", "docker", "cleanup"},
)
def docker_storage_guide() -> str:
    """Return a practical guide to Docker storage and safe cleanup."""
    return dedent(
        """\
        # Docker storage

        Docker stores images, stopped containers, build cache, volumes, and
        (on Docker Desktop) a VM disk image. Inspect usage before deleting.

        ## Inspect

        - `docker system df` - usage summary by type.
        - `docker system df -v` - per-image, container, and volume sizes.
        - `docker volume ls` - list volumes; inspect a name before pruning.

        ## Reclaim, least destructive first

        1. `docker builder prune` - removes unused build cache. Future builds
           repopulate it.
        2. `docker image prune` - removes dangling (untagged) images only.
        3. `docker container prune` - removes stopped containers. Preserve any
           state you still need first.
        4. `docker network prune` - removes unused networks.
        5. `docker system prune` - removes stopped containers, unused networks,
           dangling images, and build cache. Add `--volumes` only when you are
           certain no unused volume holds data.

        ## Risks

        - `docker image prune -a` deletes every image not used by a running
          container. Re-pulling can be slow and breaks offline workflows.
        - `docker system prune -a --volumes` is destructive. Unused volumes can
          contain databases, caches, and uploads.
        - Never delete `/var/lib/docker` or the Docker Desktop disk image
          directly. Use Docker CLI commands or Docker Desktop controls.
        - Docker Desktop's disk image may stay large after data is freed. Its
          "Clean up data" action resets the disk image and destroys all local
          containers and images while keeping settings.

        ## Check before deleting

        - `docker ps -a` for stopped containers you may still need.
        - `docker image ls` for images that are hard to rebuild or re-pull.
        - `docker volume inspect <name>` for volume ownership and contents.
        - Docker Desktop settings for disk image location and size limits.

        ## Sources

        - https://docs.docker.com/engine/manage-resources/pruning/
        - https://docs.docker.com/reference/cli/docker/system/df/
        - https://docs.docker.com/desktop/settings-and-maintenance/settings/
        - https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/
        """
    )
