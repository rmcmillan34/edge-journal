SHELL := /bin/bash
.PHONY: up down logs fmt lint test api web build-api migrate
.PHONY: clean-cache
.PHONY: fonts

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

fmt:
	docker compose run --rm api black .

lint:
	docker compose run --rm api ruff check .

test:
	docker compose build api
	# Run migrations and tests in the same container so the SQLite file persists
	docker compose run --rm -e DATABASE_URL=sqlite:////tmp/test.db -e PYTHONPATH=/app api bash -lc "alembic upgrade head && pytest -q"

build-api:
	docker compose build api

api:
	docker compose run --rm api bash

web:
	docker compose run --rm web bash

migrate:
	# Ensure DB is up and run Alembic against Postgres in compose
	docker compose up -d db
	docker compose run --rm -e PYTHONPATH=/app -e DATABASE_URL=postgresql+psycopg2://edge:edge@db:5432/edgejournal api alembic upgrade head

fonts:
	@echo "Fetching Iosevka Nerd Font (Regular/Bold) into web/public/fonts"
	@mkdir -p web/public/fonts
	@curl -L -o /tmp/IosevkaNF.zip https://github.com/ryanoasis/nerd-fonts/releases/download/v3.1.0/Iosevka.zip
	@unzip -j -o /tmp/IosevkaNF.zip "*IosevkaNerdFont-Regular.ttf" "*IosevkaNerdFont-Bold.ttf" -d web/public/fonts
	@ls -la web/public/fonts

# One-liner to nuke build caches (Docker + Next.js)
clean-cache:
	@echo "Pruning Docker caches, removing old images, and clearing Next.js cache" ; \
	(docker compose down -v --remove-orphans || true) ; \
	docker builder prune -af -f || true ; \
	docker buildx prune -af -f || true ; \
	(docker image rm -f edge-journal-web edge-journal-api || true) ; \
	rm -rf web/.next web/.turbo || true ; \
	echo "Done. Rebuild with: docker compose build --no-cache --progress=plain web"
