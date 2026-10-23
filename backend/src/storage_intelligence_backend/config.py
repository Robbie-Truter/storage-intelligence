"""Application settings, loaded from the environment with the
``STORAGE_BACKEND_`` prefix (and an optional ``.env`` file).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/storage_intelligence_backend/config.py -> repository root.
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Backend configuration.

    Provider API keys are intentionally not modelled here; LangChain reads them
    from the environment directly and they are never sent to the frontend.
    """

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_BACKEND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MCP server connection. ``UvStdioTransport`` runs
    # ``uv run --directory <mcp_server_dir> <mcp_server_command> <args>``, so the
    # command is the server's console script, not ``uv`` itself. The default is
    # resolved to an absolute path so the launch working directory is irrelevant.
    mcp_server_dir: str = str(_REPO_ROOT / "mcp-server")
    mcp_server_command: str = "storage-intelligence"
    mcp_server_args: list[str] = Field(default_factory=list)
    mcp_required: bool = False

    # Agent / LLM. The model itself is chosen per request from the catalogue
    # in ``agents/models.py``, so it is not an environment setting.
    agent_temperature: float = 0.0
    agent_max_iterations: int = 10

    # HTTP / CORS.
    cors_origins: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
