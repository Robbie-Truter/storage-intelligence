"""FastAPI application factory and entry point.

The MCP server connection is opened on startup and closed on shutdown; when it
cannot be reached the app starts in a degraded mode (readiness reports it) unless
``mcp_required`` is set.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from storage_intelligence_backend.agents.storage_agent import build_agent

from . import __version__
from .config import get_settings
from .mcp.errors import MCPToolError, MCPUnavailable
from .mcp.manager import StorageMCPClient
from .routers import agent, cleanup, disk, health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Open the MCP connection on startup and release it on shutdown."""
    settings = get_settings()

    app.state.agent = None
    app.state.mcp = None

    manager = StorageMCPClient(
        command=settings.mcp_server_command,
        args=settings.mcp_server_args,
        project_directory=settings.mcp_server_dir,
    )

    try:
        try:
            await manager.start()
        except Exception:
            if settings.mcp_required:
                raise
            logger.exception("MCP server unavailable; starting in degraded mode")
        else:
            app.state.mcp = manager
            logger.info("MCP server ready: %d tools available", manager.tool_count)

            app.state.agent = build_agent(
                model=settings.agent_model,
                manager=manager,
                temperature=settings.agent_temperature,
                max_iterations=settings.agent_max_iterations,
            )

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

    @app.exception_handler(MCPUnavailable)
    async def _mcp_unavailable(_: Request, exc: MCPUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(MCPToolError)
    async def _mcp_tool_error(_: Request, exc: MCPToolError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.to_detail()})

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
