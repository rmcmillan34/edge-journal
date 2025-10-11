SHELL := /bin/bash
.PHONY: up down logs fmt lint test api web

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
	docker compose run --rm api pytest -q

api:
	docker compose run --rm api bash

web:
	docker compose run --rm web bash
