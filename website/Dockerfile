# Stage 1: Build frontend
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Stage 2: Python backend
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

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

# Prepare data directory for SQLite
RUN mkdir -p /data /tmp/.cache/uv

# Copy application code
COPY app ./app

# Copy built frontend from previous stage
COPY --from=frontend-builder /frontend/dist ./static

EXPOSE 8080

# Start the FastAPI server in production mode
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
