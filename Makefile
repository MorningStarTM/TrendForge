.PHONY: up down logs build migrate revision shell-backend

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

migrate:
	docker compose run --rm backend uv run alembic upgrade head

revision:
	docker compose run --rm backend uv run alembic revision --autogenerate -m "$(m)"

shell-backend:
	docker compose exec backend /bin/bash
