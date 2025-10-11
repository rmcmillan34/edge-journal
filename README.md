# Edge-Journal (Starter Scaffold)

Local-first, OSS trading journal — **blank app + Docker + CI** to start learning-by-building.

## What’s in here
- **web/**: Next.js placeholder app (TypeScript, Tailwind-ready).
- **api/**: FastAPI service with `/health` and TDD scaffold (pytest).
- **docker-compose.yml**: runs `web` and `api` together.
- **.github/workflows/ci.yml**: CI that lints/tests and builds containers.
- **Makefile**: quality-of-life commands.
- **docs/**: Roadmap & stretch goals (Insight Coach marked as stretch).

## Quick start
```bash
docker compose up --build
# Web: http://localhost:3000
# API: http://localhost:8000/health
```

## Dev workflows
```bash
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api black .

docker compose run --rm web npm install
docker compose up web
```
