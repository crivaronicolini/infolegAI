import logging
from contextlib import asynccontextmanager, AsyncExitStack
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .tracking import UsageTracker
from .routes import router, mount_static_files
from .mcp import mcp

logger = logging.getLogger("uvicorn.error")

if config.DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.debug("DEBUG mode enabled")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle: setup and teardown of usage tracker."""
    async with AsyncExitStack() as stack:
        # await stack.enter_async_context(mcp.session_manager.run())
        app.state.usage_tracker = UsageTracker(config.USAGE_DB_PATH)
        await app.state.usage_tracker.start()
        logger.info("Usage tracking initialized at %s", config.USAGE_DB_PATH)
        try:
            yield
        finally:
            if app.state.usage_tracker is not None:
                await app.state.usage_tracker.close()
                logger.info("Usage tracking closed")


app = FastAPI(lifespan=lifespan)

# Enable CORS for MCP Inspector
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mount_static_files(app)

app.include_router(router)

# Add logging middleware for MCP requests
@app.middleware("http")
async def log_mcp_requests(request, call_next):
    if request.url.path.startswith("/mcp"):
        logger.debug(f"MCP Request: {request.method} {request.url}")
        logger.debug(f"Headers: {dict(request.headers)}")
        body = await request.body()
        if body:
            logger.debug(f"Body: {body.decode('utf-8', errors='ignore')[:500]}")
        # Reset the body for downstream processing
        from fastapi import Request as FastAPIRequest
        async def receive():
            return {"type": "http.request", "body": body}
        request = FastAPIRequest(request.scope, receive)
    
    response = await call_next(request)
    if request.url.path.startswith("/mcp"):
        logger.debug(f"MCP Response: {response.status_code}")
    return response

app.mount("/mcp", mcp.sse_app())
