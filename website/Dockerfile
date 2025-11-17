FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    XDG_CACHE_HOME=/tmp/.cache \
    UV_CACHE_DIR=/tmp/.cache/uv

WORKDIR /app

# Install dependencies using lockfile via BuildKit mounts (no project install)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Prepare data directory for SQLite and set permissions for non-root user
RUN mkdir -p /data && chown -R 1000:1000 /data /app
RUN mkdir -p /tmp/.cache/uv && chown -R 1000:1000 /tmp/.cache

# Copy application code
COPY src ./src
COPY templates ./templates
COPY static ./static

# Drop privileges
USER 1000:1000

EXPOSE 8080

# Start the FastAPI server with reload for development
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
