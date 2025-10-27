# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Edge-Journal is a local-first, open-source trading journal application with CSV imports, performance metrics, daily journaling, playbooks/checklists, and guardrails. It runs entirely locally via Docker.

**Tech Stack:**
- **Backend:** FastAPI + SQLAlchemy ORM + PostgreSQL (Alembic migrations)
- **Frontend:** Next.js 14 (App Router) + React 18 + TypeScript
- **Container:** Docker Compose (multi-arch: linux/amd64, linux/arm64)
- **Auth:** JWT-based (python-jose + argon2)
- **Testing:** pytest with FastAPI TestClient (SQLite for test isolation)

**Current Version:** v0.6.1 (from VERSION file)

## Git Commit Conventions

**IMPORTANT:** Do NOT include "Generated with Claude Code" or "Co-Authored-By: Claude" footers in commit messages for this project. Keep commit messages clean and focused on the changes themselves.

## Development Commands

### Starting the Application
```bash
# Build and start all services (API + Web + Postgres)
make up
# or: docker compose up --build

# Access:
# - Web UI: http://localhost:3000
# - API: http://localhost:8000
# - Health check: http://localhost:8000/health
```

### Testing and Code Quality
```bash
# Run API tests (uses SQLite, auto-runs migrations)
make test

# Run API linting
make lint

# Run API formatting
make fmt
```

**Test Pattern:**
```bash
docker compose run --rm -e DATABASE_URL=sqlite:////tmp/test.db -e PYTHONPATH=/app api bash -lc "alembic upgrade head && pytest -q"
```

Tests use SQLite for isolation and migrations are auto-run before tests. Each test typically:
1. Registers a user
2. Logs in to get JWT token
3. Uses token in Authorization header for authenticated requests

### Development Shells
```bash
# Open bash shell in API container
make api

# Open bash shell in Web container
make web
```

### Other Commands
```bash
# Run Alembic migrations against Postgres
make migrate

# Stop all services and remove volumes
make down

# Fetch Nerd Font files to web/public/fonts
make fonts

# Clean Docker caches and Next.js build artifacts
make clean-cache
```

## Architecture

### Backend Structure (FastAPI)

**Directory Layout:**
```
api/
├── app/
│   ├── main.py               # FastAPI app, CORS, router includes, startup migrations
│   ├── models.py             # SQLAlchemy models (User, Trade, Account, etc.)
│   ├── schemas.py            # Pydantic schemas for request/response
│   ├── db.py                 # Database connection & session factory
│   ├── deps.py               # Dependency injection (get_current_user, get_db)
│   ├── auth_utils.py         # Password hashing, JWT token logic
│   ├── enforcement.py        # Risk cap & breach logic
│   ├── routes_*.py           # Feature-based route modules (12 total)
│   └── version.py
├── tests/                    # pytest tests (15+ test modules)
├── alembic/                  # Database migrations
│   └── versions/             # Migration scripts (0017+ versions)
└── .env                      # Dev environment variables
```

**Router Organization:**
- Modular routers per feature domain: `routes_auth.py`, `routes_uploads.py`, `routes_trades.py`, `routes_accounts.py`, `routes_presets.py`, `routes_metrics.py`, `routes_journal.py`, `routes_templates.py`, `routes_playbooks.py`, `routes_playbook_responses.py`, `routes_settings.py`, `routes_breaches.py`
- Each router uses `APIRouter(prefix="/path", tags=["domain"])`
- Routers are included in `main.py` via `app.include_router()`

**Dependency Injection:**
- `get_db()` yields SQLAlchemy session
- `get_current_user()` validates JWT and returns User model
- Use `Depends()` in route parameters

**Database Model Patterns:**
- Explicit `__tablename__` for all models
- Foreign keys for relationships with proper indexes
- Timestamps use `server_default=func.now()` for audit trails
- Financial data uses `Numeric(precision, scale)` for precision
- User isolation via `user_id` on all major tables (multi-tenant design)

**Pydantic Schema Patterns:**
- Separate schemas for Create, Update, Out (response)
- Use `model_config = ConfigDict(from_attributes=True)` for ORM conversion
- Validation via `Field()` with constraints
- `RootModel` for dict-like schemas

**Migration Pattern:**
- Alembic migrations in `/api/alembic/versions/` (numbered 0001-0017+)
- Auto-run on startup in dev mode (`ENV=dev`)
- Manually run in CI/prod via `alembic upgrade head`
- Each migration has up() and down() for reversibility

### Frontend Structure (Next.js)

**Directory Layout:**
```
web/
├── app/                      # Next.js App Router
│   ├── layout.tsx            # Root layout with Catppuccin CSS theme
│   ├── page.tsx              # Home/landing page
│   ├── auth/                 # /auth/register, /auth/login
│   ├── trades/               # /trades (list) + /trades/[id] (detail)
│   ├── upload/               # /upload (CSV upload)
│   ├── uploads/              # /uploads (import history)
│   ├── dashboard/            # /dashboard (KPIs, equity curve, calendar)
│   ├── journal/              # /journal/[date] (daily journal)
│   ├── templates/            # /templates (CRUD note templates)
│   ├── playbooks/            # /playbooks (playbook management)
│   ├── settings/             # /settings (user settings, alert level, caps)
│   └── guardrails/           # /guardrails (breach list, acknowledge)
├── components/               # Reusable React components
└── public/                   # Static assets + fonts
```

**Routing:**
- File-based routing: `/app/trades/page.tsx` → `/trades` route
- Dynamic routes: `/app/trades/[id]/page.tsx` → `/trades/1`, `/trades/2`, etc.
- Use `"use client"` directive for client-side interactivity

**Styling & Theme:**
- **Catppuccin Mocha** CSS variables for dark mode
- Nerd Font preference with system font fallbacks
- Dark mode toggle persisted to `localStorage` via `ej_theme`
- Color scheme loaded in inline `<script>` to prevent flash

**API Integration:**
- Environment: `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`)
- Token stored client-side, passed in Authorization headers
- Use fetch or axios for REST calls

### Database Schema

**Core Tables:**
- **users** — email, password_hash, is_active, tz, created_at
- **uploads** — CSV import audit trail
- **accounts** — trading accounts with risk caps
- **trades** — individual trades with P&L, notes, attachments
- **instruments** — symbol list
- **attachments** — files linked to trades/journals
- **daily_journal** — daily notes with Markdown
- **playbook_templates** — versioned checklists with grading
- **playbook_responses** — completed playbook forms
- **trading_rules** — user alert thresholds
- **breaches** — risk cap violations

**Relationships:**
- Foreign keys from trades → accounts, instruments
- Foreign keys from attachments → trades, journals
- Foreign keys from playbook_responses → templates, trades, journals
- All major tables have `user_id` for multi-tenant isolation

## Coding Conventions

### Python (Backend)
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **File naming:** `routes_*.py` for route modules
- **Error handling:** Use `HTTPException` with status code + detail
- **Testing:** Use FastAPI `TestClient`, setup user auth in each test
- **Formatting:** Black (run via `make fmt`)
- **Linting:** Ruff (run via `make lint`)

### TypeScript (Frontend)
- **Naming:** camelCase for functions/variables, PascalCase for components
- **Config:** `strict: false` in tsconfig for flexibility, but `strictNullChecks: true`
- **Components:** Feature-organized in `/components`

## Environment Variables

### API (.env)
```bash
ENV=dev|prod
PYTHONPATH=/app
DATABASE_URL=postgresql+psycopg2://user:pass@host:port/dbname
JWT_SECRET=<random-long-secret>
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
MAX_UPLOAD_MB=20
ATTACH_BASE_DIR=/data/uploads
ATTACH_MAX_MB=10
ATTACH_THUMB_SIZE=256
CORS_ORIGINS=comma-separated-origins
```

### Web (runtime)
```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_MAX_UPLOAD_MB=20
NEXT_PUBLIC_APP_VERSION=<version>
```

## Key Features & Workflows

### CSV Import Workflow
1. Upload CSV at `/upload`
2. Choose/confirm preset and mapping
3. Set timezone for CSV timestamps
4. Preview first rows with inline errors
5. Commit to create/update trades
6. View import history at `/uploads`

### Trades Management
- List view at `/trades` with filters (symbol, account, date range)
- Detail view at `/trades/[id]` with notes (Markdown) and attachments
- Manual trade creation with deduplication by stable key
- Apply templates to notes, save with Cmd/Ctrl+S
- Attachments: upload images/PDFs with EXIF stripping, thumbnails, metadata, reorder, multi-select delete/download

### Daily Journal
- Visit `/journal/YYYY-MM-DD` for daily entries
- Markdown notes with template support
- Link trades for the day
- Attachments with same features as trades

### Playbooks & Guardrails
- Playbook templates at `/playbooks` with versioned checklists
- Guardrails track risk caps and alert thresholds
- Breach events logged and shown on dashboard calendar
- Acknowledge breaches at `/guardrails`

### Dashboard
- KPIs, equity curve, month calendar with daily P&L
- Calendar shows journal presence (blue dot), attachments (×N pill)
- Color-coded days (green/red by P&L)
- Breach badges: ⚠️ loss streak, 🟨 losing day streak, 🟧 losing week streak, ⛔ risk cap exceeded

## Common Development Tasks

### Adding a new route
1. Create `routes_<feature>.py` in `/api/app/`
2. Define `APIRouter(prefix="/path", tags=["feature"])`
3. Add route functions with proper schemas and dependencies
4. Include router in `main.py` via `app.include_router()`
5. Write tests in `/api/tests/test_<feature>.py`

### Adding a database migration
```bash
# Auto-generate migration from model changes
docker compose run --rm api alembic revision --autogenerate -m "description"

# Review and edit generated migration in /api/alembic/versions/

# Test migration
docker compose run --rm api alembic upgrade head
```

### Adding a new frontend page
1. Create directory under `/web/app/<route>/`
2. Add `page.tsx` with page component
3. Use `"use client"` if client-side interactivity needed
4. Add API integration via fetch to backend endpoints

### Running a single test file
```bash
docker compose run --rm -e DATABASE_URL=sqlite:////tmp/test.db -e PYTHONPATH=/app api bash -lc "alembic upgrade head && pytest -q tests/test_specific.py"
```

### Running a single test function
```bash
docker compose run --rm -e DATABASE_URL=sqlite:////tmp/test.db -e PYTHONPATH=/app api bash -lc "alembic upgrade head && pytest -q tests/test_specific.py::test_function_name"
```

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml`:
- **Test job:** Python 3.11 + Postgres 16 + Alembic migrations + pytest
- **Build & Push job:** Multi-arch Docker builds (amd64, arm64) → GitHub Container Registry on main/tags
- **Release job:** Auto-create GitHub releases on version tags

## Deployment Notes

- Docker Compose locally for development
- Multi-arch images pushed to GHCR for production
- API auto-runs migrations on startup when `ENV=dev`
- For production, run `alembic upgrade head` manually before deploying new version
- Health check available at `/health` endpoint

## Timezone Handling

- **CSV timezone:** Applied at import commit to convert timestamps to UTC for storage
- **Display timezone:** UI setting for Trades/Dashboard (does not change stored data)
- If CSV times are already UTC, commit with `tz=UTC` to avoid double shifting

## Keyboard Shortcuts

- **Cmd/Ctrl+S:** Save notes on Trade detail and Daily journal pages
- **Esc:** Exit attachment reorder mode

## Documentation

- `docs/USAGE.md` — Comprehensive user guide with workflows and API examples
- `docs/ROADMAP.md` — Milestone roadmap (M0-M9)
- `docs/CHANGELOG.md` — Version history
- `docs/AGENTS.md` — AI agent personas for development
- `docs/M5_PLAYBOOKS_TECH_DESIGN.md` — Playbook/guardrails design
- `docs/M7_REPORTS_FILTERS_TECH_DESIGN.md` — Advanced reporting design (in progress)
