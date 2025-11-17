import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langchain_core.messages import HumanMessage

from .agent import agent
from .config import DEBUG, USAGE_DAILY_LIMIT
from .tracking import get_client_identity

logger = logging.getLogger("uvicorn.error")

# Setup paths and templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Create router
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the initial chat page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/signup", response_class=HTMLResponse)
async def signup(request: Request):
    """Serves the signup page when triggered."""
    return templates.TemplateResponse("signup.html", {"request": request})


@router.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, prompt: Annotated[str, Form()]):
    """Handles chat messages via the agent, which may invoke the RAG tool as needed."""
    # Enforce usage limit before invoking the model (unless DEBUG is enabled)
    if not DEBUG:
        ip, ua = get_client_identity(request)
        limit = USAGE_DAILY_LIMIT
        usage_tracker = getattr(request.app.state, "usage_tracker", None)
        if usage_tracker is not None:
            try:
                current = await usage_tracker.get_today_count(ip, ua)
            except Exception as exc:
                logger.exception("Usage tracking read failed: %s", exc)
                current = 0
            if current >= (limit - 1):
                # HTMX-aware redirect to signup
                if request.headers.get("hx-request"):
                    return HTMLResponse(content="", headers={"HX-Redirect": "/signup"})
                return RedirectResponse(url="/signup", status_code=303)
            try:
                await usage_tracker.increment(ip, ua)
            except Exception as exc:
                logger.exception("Usage tracking increment failed: %s", exc)
    else:
        logger.debug("DEBUG mode enabled; skipping usage tracking")

    result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
    logger.debug("Agent invoked for prompt sample=%r", prompt[:100])
    logger.debug(f"Raw agent result {result}")

    response = result.get("messages")[-1].content

    # Format messages for the UI
    user_message = f'<div class="text-right my-2"><span class="bg-blue-600 p-2 rounded-lg inline-block">{prompt}</span></div>'
    bot_response = f'<div class="text-left my-2"><span class="bg-gray-700 p-2 rounded-lg inline-block">{response}</span></div>'

    return HTMLResponse(content=user_message + bot_response)


# Function to mount static files (called from main.py)
def mount_static_files(app):
    """Mount static files directory to the app."""
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

