FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /workspace

COPY pyproject.toml ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY workers/pyproject.toml workers/pyproject.toml
COPY backend/app /workspace/backend/app

WORKDIR /workspace/workers
RUN uv sync --frozen --no-dev --package trendforge-workers || uv sync --no-dev

COPY workers/app ./app

CMD ["uv", "run", "celery", "-A", "app.celery_app", "worker", "--loglevel=info"]
