# syntax=docker/dockerfile:1
# Backend image: FastAPI trend-detection API (uvicorn).
# Build context is the REPO ROOT (it needs the uv workspace files), e.g.:
#   docker build -f backend/Dockerfile -t trendforge-backend .
FROM python:3.12-slim

# uv for fast, reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Workspace resolution files first. Both member pyprojects are needed for uv to
# understand the workspace, but only the backend package is installed
# (`--package trendforge-backend`) — the dormant `workers` package is skipped,
# which also avoids its `app` package colliding with the backend's.
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY workers/pyproject.toml ./workers/pyproject.toml
COPY backend/app ./backend/app

# Heavy ML deps (torch, sentence-transformers) are cached in the uv cache mount,
# so rebuilds don't re-download them.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package trendforge-backend

EXPOSE 8000

# Stdlib healthcheck (slim image has no curl).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uv", "run", "--package", "trendforge-backend", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
