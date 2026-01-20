from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.agent import lifespan_agent
from app.core.config import settings
from app.core.mcp import mcp_app
from app.db import create_db_and_tables, engine
from app.logging_conf import configure_logging
from app.middleware.wide_logging import WideLoggingMiddleware

configure_logging()


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """Combined lifespan for main app and MCP app."""
    await create_db_and_tables()
    async with lifespan_agent(app):
        async with mcp_app.router.lifespan_context(app):
            yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=combined_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(WideLoggingMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve static files from the built frontend
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA, handling client-side routing."""
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")


app.mount("/mcp", mcp_app)
