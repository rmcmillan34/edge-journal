# AGENTS.md

Operational guide for running Edge Journal with **Codex CLI** (or any agent runner). This keeps our repo, CI/CD, and security conventions consistent as we add autonomous/assisted workflows.

---

## 1) Purpose

This document defines:
- Agent **roles** and **boundaries**  
- Standard **prompts**, **checklists**, and **playbooks**  
- Required **repo conventions** (SemVer, branches, CI, Docker, multi-arch)  
- **Security**, **TDD**, and **governance** rules

Agents should be able to pick up tasks with minimal context and produce PRs safely.

---

## 2) Ground Rules (must-follow)

- **Branch protection:** no direct pushes to `main`. All changes via PRs.
- **SemVer:** Pre-1.0 → `0.MINOR.PATCH`. All M2 features are `0.2.x`; when M2 completes → bump to `0.3.0`.  
- **Single source of version truth:** root `VERSION` file.  
- **TDD-first:** add/adjust tests **before** code where feasible.  
- **Security stance:** privacy-first; no telemetry; safe defaults; secrets never committed.  
- **Multi-arch:** Docker images must target `linux/amd64,linux/arm64`.  
- **Repro builds:** no dependence on local files not in repo; builds parameterized via `ARG VERSION`.  
- **Human-in-the-loop:** agents open PRs with clear summaries, risk notes, and test results.  

---

## 3) Repository Map (assumptions)

```
/
├─ VERSION                      # single source of truth for app version
├─ .github/workflows/ci.yml     # tests + multi-arch docker build + release
├─ deploy/
│  ├─ compose.yaml              # one-command install (api/web/db)
│  ├─ .env.example              # example runtime env
│  └─ install.sh                # installer (generates .env; pulls images)
├─ api/
│  ├─ Dockerfile
│  ├─ alembic/versions/         # migrations (0001_*, 0002_*, 0003_*)
│  ├─ app/
│  │  ├─ main.py                # FastAPI app (version from /app/VERSION or env)
│  │  ├─ version.py             # get_version helper
│  │  ├─ routes_*               # routers (auth, uploads, presets, etc.)
│  │  ├─ models.py              # SQLAlchemy models
│  │  ├─ deps.py                # auth deps (get_current_user, etc.)
│  │  └─ schemas.py             # Pydantic schemas
│  └─ tests/                    # pytest suites (functional + unit)
└─ web/
   ├─ Dockerfile
   ├─ package.json / lockfile
   └─ app|pages/                # (Next.js scaffold)
```

---

## 4) Branching, Versioning, Releases

- **Branches:**  
  - `main`: release branch, always deployable  
  - `dev`: integration branch for features  
  - `feat/<scope>`: short-lived branches that PR → `dev`

- **Versioning (SemVer pre-1.0):**  
  - All M2 work ships as `0.2.x` (features bump PATCH).  
  - After M2 complete → `0.3.0`.  
  - Hotfixes on `main` bump PATCH (e.g., `0.2.3` → `0.2.4`).  

- **Release procedure:**  
  1) Merge `dev` → `main` via PR  
  2) `echo "<x.y.z>" > VERSION && git commit`  
  3) `git tag v<x.y.z> && git push origin v<x.y.z>`  
  4) CI: builds multi-arch images (API/Web) to GHCR + creates GitHub Release  

---

## 5) CI/CD Expectations (GitHub Actions)

- **test job:** runs Alembic migrations, sets `PYTHONPATH`, executes `pytest -q`
- **build-and-push job:** builds/pushes Docker images (arm64 & amd64) using `ARG VERSION`
- **release job:** creates a GitHub Release on tags (requires `permissions: contents: write`)

**Do not** introduce steps that require secrets beyond `GITHUB_TOKEN` unless documented here.

---

## 6) Runtime & One-Liner Install

- Images:  
  - `ghcr.io/<OWNER>/edge-journal-api:<tag>`  
  - `ghcr.io/<OWNER>/edge-journal-web:<tag>`
- DB: `postgres:16-alpine` (upstream)

**One-liner (example):**
```bash
EDGEJ_VERSION=v0.2.3 bash -c "$(curl -fsSL https://raw.githubusercontent.com/<OWNER>/edge-journal/main/deploy/install.sh)"
```

---

## 7) Agent Roles

### 7.1 Repo Agent
- Keeps `VERSION` accurate; updates `/api/app/main.py` via `get_version()` (no hardcoding).
- Maintains `.github/workflows/ci.yml` invariants (PYTHONPATH, alembic, build-args).
- Enforces Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).
- Opens PRs with a succinct change log and risk notes.

### 7.2 API Agent
- Adds endpoints with TDD, SQLAlchemy models, Alembic migrations.
- Keeps `/health`, `/version` working; ensures migration idempotency.
- Adds tests under `api/tests/…` (functional + error paths).

### 7.3 Web Agent
- Keeps Next.js scaffold buildable; bakes `NEXT_PUBLIC_APP_VERSION`.
- Adds minimal UI for new APIs and basic e2e health checks (optional later).

### 7.4 Release Manager Agent
- Drives the release checklists, tags, and GHCR visibility (public packages).
- Validates images pull/run on both arm64 and amd64.

### 7.5 Security/QA Agent
- Reviews for secrets, unsafe defaults, excessive scopes.
- Validates auth on new routes, rate limits (if added), and input validation.

---

## 8) Prompts & Checklists

### 8.1 Standard feature prompt
> **Task:** Implement `<feature>`  
> **Constraints:** Follow TDD; update/ add tests; keep SemVer rules; no breaking changes; API documented via OpenAPI from FastAPI; ensure CI passes.  
> **Deliverables:** Code, tests, docs snippets for README, and release notes fragment.  
> **Acceptance:** `pytest -q` green; CI green; local `docker compose up` health checks pass.

### 8.2 PR checklist (agents must include)
- [ ] Why: problem/goal in 1–3 sentences  
- [ ] What: changes (routes, models, migrations)  
- [ ] Tests: added/updated (`pytest -q` output summary)  
- [ ] Migrations: idempotent and applied in CI  
- [ ] Version: updated? (only on release PRs to `main`)  
- [ ] Security: auth on endpoints; input validation  
- [ ] Docs: README snippet if user-facing

### 8.3 Release checklist (Release Manager)
- [ ] `dev` merged into `main`  
- [ ] `VERSION` set to `<x.y.z>`  
- [ ] Tag `v<x.y.z>` pushed  
- [ ] CI published images to GHCR (multi-arch)  
- [ ] Packages set to **Public**  
- [ ] One-liner install tested locally (arm64 and amd64, if possible)

---

## 9) Playbooks

### 9.1 Add an endpoint (API)
1. **Test first:** create/extend `api/tests/test_<feature>.py`  
2. **Model/migration:** create Alembic revision, update `models.py`  
3. **Route:** new or existing router; add dependencies (auth)  
4. **Schemas:** pydantic input/output  
5. **Wire:** include router in `main.py`  
6. **Run:** `docker compose run --rm api pytest -q`  
7. **Commit:** `feat(api): <endpoint>` with test results in PR body

### 9.2 Add a migration
- Generate new file under `alembic/versions/` with `revision`, `down_revision` set
- Write `upgrade()`/`downgrade()` (idempotent with CASCADE where appropriate)
- Ensure CI runs `alembic upgrade head` before tests

### 9.3 Add a preset or mapping feature (M2.4 pattern)
- `/uploads/preview` accepts `mapping` (JSON) & `preset_name`
- `/uploads/commit` supports `mapping`, `preset_name`, `save_as`
- `/presets` CRUD scoped to user, `(user_id, name)` unique
- Tests for preview/commit/preset creation and conflicts

---

## 10) Environment & Secrets

- **Never** commit real secrets.  
- Runtime secrets live in `deploy/.env` (user-generated from `.env.example`).  
- CI uses `GITHUB_TOKEN` only (packages write, contents read; release job needs `contents: write`).  
- Optional registries or PATs must be documented here **before** use.  

**Minimum `.env` keys** (runtime):
```
JWT_SECRET=<random-hex>
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
POSTGRES_USER=edge
POSTGRES_PASSWORD=edge
POSTGRES_DB=edgejournal
DATABASE_URL=postgresql+psycopg2://edge:edge@db:5432/edgejournal
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

---

## 11) Quality Gates

Agents must ensure:
- `docker compose run --rm api pytest -q` passes
- No new flake8/ruff severity errors (if linting enabled in CI later)
- Docker images build with `ARG VERSION` and include a working `/health` and `/version`
- OpenAPI reflects new endpoints (visible at `/openapi.json`)

---

## 12) Coding Style & Docs

- **Python:** FastAPI, pydantic v2, SQLAlchemy, Alembic; type hints encouraged  
- **Tests:** pytest; small, clear, isolated; avoid test interdependence  
- **Docs:** README updates for new user-facing features; inline docstrings for complex logic  
- **Changelogs:** summarize in PR; Release notes auto-generated by action (optional manual edit)

---

## 13) Security & Privacy

- No telemetry; all metrics/analytics are local to the user’s deployment
- Input validation on all external inputs (CSV mapping, JSON bodies, file uploads)
- JWT auth on protected routes; never log secrets or tokens
- Future: rate limits, CORS allowlist (today: `*` for dev; document if changed)

---

## 14) Failure Handling & Rollback

- Migrations must be reversible with `downgrade()`  
- If a release fails:  
  - `docker pull` previous tag, re-run compose  
  - `git tag` hotfix as next PATCH (e.g., `0.2.4`) after fix  
- Agents should always propose a rollback path in PRs with risky changes

---

## 15) Glossary

- **Preset:** Saved mapping of canonical trade fields → CSV headers, per-user  
- **Preview:** Validate mapping + show first rows without committing trades  
- **Commit:** Upsert trades using dedupe key; report inserted/updated/skipped  
- **M2.x:** Milestone 2 feature series (`0.2.x`)

---

### Appendix A — Example Agent Task Template

```
Task: Implement M2.4 presets & preview for CSV imports.

Context: Use existing /uploads/commit; add /uploads/preview; add /presets list/create.
Constraints: TDD; CI must pass; keep version at 0.2.4-dev on dev branch; maintain security stance.

Plan:
- Migration 0003_mapping_presets (idempotent)
- Model MappingPreset
- /presets GET/POST
- /uploads/preview: accepts mapping JSON & preset_name; returns applied mapping + plan + preview
- /uploads/commit: accept mapping/preset_name/save_as; returns applied mapping; save preset if requested
- Tests: preview_with_override; save_and_use_preset; commit_with_preset; duplicate_name_409

Exit Criteria:
- pytest green; routes visible in /openapi.json; preview & commit behave as specified
- PR created against dev with summary, test logs, risk notes
```
