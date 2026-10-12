"""Application settings, loaded from the environment with the
``STORAGE_BACKEND_`` prefix (and an optional ``.env`` file).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # MCP server connection.
    mcp_server_dir: str = "mcp-server"
    mcp_server_command: str = "uv"
    mcp_server_args: list[str] = Field(
        default_factory=lambda: [
            "run",
            "--directory",
            "mcp-server",
            "storage-intelligence",
        ]
    )
    mcp_required: bool = False

    # Agent / LLM.
    agent_model: str = "openai:gpt-4.1"
    agent_temperature: float = 0.0
    agent_max_iterations: int = 10

    # HTTP / CORS.
    cors_origins: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
