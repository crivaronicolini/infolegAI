import random
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import settings

logger = structlog.stdlib.get_logger("app.request")


class WideLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that emits a single structured log event per request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip health checks and static files
        if request.url.path in ("/health"):
            return await call_next(request)

        clear_contextvars()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            http_path=request.url.path,
        )
        start_time = time.perf_counter()

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            bind_contextvars(error_type=type(e).__name__, error_message=str(e))
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            if self._should_log(request_id, status_code, duration_ms):
                logger.info(
                    "request_completed",
                    status_code=status_code,
                    duration_ms=round(duration_ms, 2),
                )

    def _should_log(
        self, request_id: str, status_code: int, duration_ms: float
    ) -> bool:
        """Tail sampling: always log errors/slow, sample normal requests."""
        # Always log errors
        if status_code >= 400:
            return True

        # Always log slow requests
        if duration_ms > settings.LOG_SLOW_THRESHOLD_MS:
            return True

        # random sample
        return random.random() < settings.LOG_SAMPLE_RATE
