"""FastAPI application factory and entry point.

Scaffold only: the MCP client is wired into the lifespan in a later milestone.
For now the state is initialised to ``None`` so readiness can report it.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .routers import agent, cleanup, disk, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise and tear down shared resources."""
    app.state.mcp = None
    yield
    app.state.mcp = None


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
