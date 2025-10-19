# Edge-Journal (Starter Scaffold)

Local-first, OSS trading journal — **CSV-first** imports, dashboards, and journaling. Runs locally with Docker.

## What’s in here
- `web/`: Next.js app (App Router). Uploads, Trades, Dashboard.
- `api/`: FastAPI service with tests (pytest) and Alembic migrations.
- `docker-compose.yml`: runs Web + API + Postgres.
- `.github/workflows/ci.yml`: lint/tests + multi-arch images.
- `Makefile`: quality-of-life commands.
- `docs/`: Roadmap, agents, requirements, examples.

## Quick start
```bash
# one-time build + run
docker compose up --build

# Web: http://localhost:3000
# API: http://localhost:8000 (health at /health)
```

Sign up in the web UI, then:
- Upload CSV at `/upload` → preview mapping and timezone → commit
- See imports at `/uploads` (download errors CSV, delete import)
- Browse trades at `/trades` (filters, add manual trade, journal notes, delete/undo, CSV export)
- Dashboard at `/dashboard` (KPIs, all‑time equity curve, month calendar)

## Dev workflows
```bash
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api black .

docker compose run --rm web npm install
docker compose up web
```

API auto-runs Alembic migrations on startup when `ENV=dev`.

## Features (M2–M3)
- CSV import presets, custom mapping, preview + commit, per‑upload timezone
- Imports history, error CSV download, delete import (removes its trades)
- Trades list with filters (symbol/account/date), presets (Today/Week/Month), sorting, pagination, page size, CSV export
- Manual trade entry (dedupe by stable key), journal notes, delete + undo
- Dashboard: KPIs, all‑time equity curve, month calendar with daily PnL, filters + display timezone
- Typable dropdowns for known Symbols/Accounts

## Timezones: CSV vs Display
- CSV timezone is applied at commit to convert timestamps to UTC for storage.
- Display timezone is a UI setting on Trades/Dashboard (does not change stored data).
- If your CSV times are already UTC, commit with `tz=UTC` to avoid double shifting.

## API overview
- `GET /metrics` — KPIs + equity curve; filters: `start`, `end` (YYYY‑MM‑DD), `symbol`, `account`, `tz`
- `GET /trades` — list; supports `start`, `end`, `symbol`, `account`, `limit`, `offset`, `sort`
- `POST /trades` — manual create (fields: account_name|account_id, symbol, side, open_time, close_time?, qty_units, entry_price, exit_price?, fees?, net_pnl?, notes_md?, tz?)
- `PATCH /trades/{id}` — update notes/fees/net
- `DELETE /trades/{id}` — delete; returns `restore_payload` for undo
- `GET /trades/symbols` — distinct symbols (optional `account` filter)
- `GET /uploads` — history; `POST /uploads/preview` and `POST /uploads/commit` for import flow
- `DELETE /uploads/{id}` — remove import and its trades
- `GET /uploads/{id}/errors.csv` — download errors as CSV
- `GET/POST /accounts`, `GET/POST /presets`

## Environment
- API: `MAX_UPLOAD_MB` (default 20)
- Web: `NEXT_PUBLIC_API_BASE` (default http://localhost:8000), `NEXT_PUBLIC_MAX_UPLOAD_MB` (default 20)

## Versioning
- Pre‑1.0 SemVer from `VERSION`. M3 bump → v0.3.0.

## Stretch ideas
- Dashboard month CSV export (date, net PnL, equity) honoring filters/timezone.
