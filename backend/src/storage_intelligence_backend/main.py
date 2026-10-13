"""FastAPI application factory and entry point.

The MCP server connection is opened on startup and closed on shutdown; when it
cannot be reached the app starts in a degraded mode (readiness reports it) unless
``mcp_required`` is set.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .mcp.manager import StorageMCPClient
from .routers import agent, cleanup, disk, health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Open the MCP connection on startup and release it on shutdown."""
    settings = get_settings()

    manager = StorageMCPClient(
        command=settings.mcp_server_command,
        args=settings.mcp_server_args,
        project_directory=settings.mcp_server_dir,
    )

    try:
        await manager.start()
    except Exception:
        if settings.mcp_required:
            raise
        logger.exception("MCP server unavailable; starting in degraded mode")
        app.state.mcp = None
    else:
        logger.info("MCP server ready: %d tools available", manager.tool_count)
        app.state.mcp = manager

    try:
        yield
    finally:
        await manager.stop()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Storage Intelligence Backend",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(disk.router, prefix="/api")
    app.include_router(agent.router, prefix="/api")
    app.include_router(cleanup.router, prefix="/api")

    return app


app = create_app()


def run() -> None:
    """Run the API with uvicorn."""
    import uvicorn

    uvicorn.run(
        "storage_intelligence_backend.main:app",
        host="127.0.0.1",
        port=8000,
    )
