# Milestone 5 — Playbooks v1: Working Context

Status: Implemented (first pass)
Owner: Edge‑Journal
Updated: 21 Oct 2025

## 1) What’s in this slice
- Playbook Templates (schema‑driven, versioned) with fields: boolean, select, number, text, rating, rich‑text; required/weight; grade thresholds; risk schedule; template max risk.
- Playbook Responses (trade‑attached and daily instrument checklists) with persisted `computed_grade` and `compliance_score` on save.
- Evidence links at field level: trade/journal attachments or URLs; reuse (copy) across multiple fields.
- Trading rules (user‑level) + calendar breaches (day/week/month streaks + risk‑cap exceeded) with a legend + per‑icon tooltips in UI.
- Grade surface in Trades list (filter by grade) and on Trade Playbook tab.

## 2) Data model (API/alembic)
- Tables
  - `playbook_templates` (user_id, name, purpose, schema_json, version, is_active, grade_thresholds_json, risk_schedule_json, template_max_risk_pct, created_at)
  - `playbook_responses` (user_id, trade_id?, journal_id?, template_id, template_version, entry_type, values_json, comments_json, intended_risk_pct, computed_grade, compliance_score, created_at)
  - `playbook_evidence_links` (response_id, field_key, source_kind, source_id?, url?, note, created_at)
  - `user_trading_rules` (user_id unique, max_losses_row_day, max_losing_days_streak_week, max_losing_weeks_streak_month, alerts_enabled, created_at)
  - `breach_events` (optional audit; user_id, account_id?, scope, date_or_week, rule_key, details_json, created_at)
  - `accounts.account_max_risk_pct` (nullable float) — per‑account risk cap
- Alembic revisions added
  - `0013_playbooks_core.py` — templates/responses/evidence
  - `0014_trading_rules_and_breaches.py` — trading rules + breach events
  - `0015_accounts_risk_cap.py` — account risk cap column

## 3) API surface (FastAPI)
- Playbooks (templates)
  - `GET /playbooks/templates?purpose=&active=`
  - `POST /playbooks/templates` (create v1)
  - `PATCH /playbooks/templates/{id}` (version‑bump copy)
  - `POST /playbooks/templates/{id}/export`
  - `POST /playbooks/templates/import`
  - `POST /playbooks/evaluate` → { compliance_score, grade, risk_cap_pct, cap_breakdown }
  - `GET /playbooks/grades?trade_ids=1,2,3` → latest grades per trade
- Playbook responses
  - Trade: `GET /trades/{trade_id}/playbook-responses`, `POST /trades/{trade_id}/playbook-responses`
  - Instrument checklist:
    - `GET /journal/{date}/instrument/{symbol}/playbook-response` (latest or symbol‑match)
    - `GET /journal/{date}/instrument/{symbol}/playbook-responses` (all for the day)
    - `POST /journal/{date}/instrument/{symbol}/playbook-response`
  - Evidence: `GET/POST /playbook-responses/{response_id}/evidence`, `DELETE /playbook-responses/{response_id}/evidence/{evidence_id}`
- Settings (trading rules)
  - `GET/PUT /settings/trading-rules`
- Metrics (calendar)
  - `GET /metrics/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD&tz=` → { days: [{ date, trades, net_pnl, breaches[] }] }
  - Breach keys: `loss_streak_day`, `losing_days_week`, `losing_weeks_month`, `risk_cap_exceeded`
- Accounts
  - `PATCH /accounts/{id}` (update including `account_max_risk_pct`)

## 4) Web UI entry points (Next.js)
- Playbooks: `/playbooks` — list/create templates (purpose; fields; template max risk)
- Trades
  - List: `/trades` — now with “Grade” filter and column
  - Detail: `/trades/[id]` → Playbook tab (choose template, evaluate, save; evidence panel with trade/journal/URL; copy evidence across fields)
- Daily Journal: `/journal/YYYY-MM-DD` → “Instrument Checklist” section (choose purpose/template, symbol; evaluate/save; evidence panel; previous responses selector; copy evidence across fields; link trade attachments by date)
- Dashboard: `/dashboard` — Calendar shows breach badges; “Legend” button opens breach legend panel; per‑icon tooltips

## 5) How to run (dev quickstart)
1) `docker compose up --build` (or use project Makefile if present)
2) API auto‑migrates on startup when `ENV=dev`; otherwise: exec into API container and run Alembic upgrade → `alembic upgrade head`
3) Sign up via web UI; create a template under `/playbooks` (purpose `post` for trade playbook; `pre` for instrument checklist)
4) Set trading rules via the first‑run modal on `/dashboard` (or Settings API); optionally set per‑account risk caps under Accounts
5) Use `/trades` to create/upload trades; on a trade detail page, open Playbook tab → choose template → fill → Evaluate → Save; add evidence
6) For pre‑session: open `/journal/YYYY-MM-DD`, set symbol, choose a template, Evaluate → Save; link evidence (URL or trade attachments)

## 6) Quick verification checklist
- Create Playbook template → appears under `/playbooks` and is selectable in Trade/Journal flows
- Trade Playbook save → response persists with `computed_grade` + `compliance_score`; evidence add/remove works; copy evidence works
- Instrument Checklist save → response persists; URL evidence add/remove; copy evidence works; can load trade attachments filtered by symbol
- Dashboard calendar → clicking Legend shows the legend; days display badges when rules are breached (seed losing streaks if needed)
- Trades list → Grade column populated after saving playbook responses; filter by grade narrows results

## 7) What’s intentionally out of scope (for M5)
- Enforcement/blocking on caps (M6); currently warnings + badges only
- Repeatable sections; computed formulas in fields; PDF inclusion; advanced analytics on custom fields
- Full typed‑entries backfill for legacy notes/templates (we are aligned for forward‑compat)

## 8) Known gaps / next steps
- Persist/combine intended risk: capture via playbook field and/or explicit `intended_risk_pct` on response; ensure UI prompts for it where relevant
- Evidence UX polish: multi‑select copy; drag‑reorder; preview thumbnails on evidence rows
- Saved views using playbook fields in filters/groups (basic grade done; field filters are backend‑ready via JSONB but not exposed everywhere)
- Tests: expand API unit coverage for evaluate logic and calendar breaches; add Playwright smoke tests for Playbook flows
- Docs: add screenshots (calendar legend; trade playbook panel) under `docs/images` and reference in USAGE.md

## 9) Troubleshooting
- 401/403: sign in; pass Bearer token to API calls
- Migrations not applied: set `ENV=dev` for auto‑upgrade in dev; or run `alembic upgrade head` in API container
- No calendar badges: ensure trading rules are set and there are trades in the selected month; risk‑cap badge requires responses with `intended_risk_pct` and caps configured
- Grade column empty: save a Playbook response for those trades; list page fetches latest grades dynamically

## 10) Security & scope
- All playbooks/templates/responses/evidence are user‑scoped; API guards by `user_id`
- No external network calls; URL evidence is user‑provided and not fetched server‑side

