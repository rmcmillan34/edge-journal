Edge‑Journal — Next Session Context (M4 Templates + Journal)

Version: 0.4.1 (M4 in progress)

Delivered in M4 so far
- Attachments: EXIF strip + PNG/JPEG thumbnails; trade attachments list/reorder/batch delete; journal attachments CRUD.
- Daily Journal: `/journal/YYYY-MM-DD` with title + Markdown notes, link trades, delete journal; calendar shows 📝 + blue dot; configurable week start (Mon default).
- Templates: backend CRUD (`/templates`), storage with sections; apply templates in Trade and Daily editors; Templates management UI at `/templates`.
- Metrics: includes `unreviewed_count`; Dashboard shows KPI.

Key API Endpoints (current)
- Health/version: `GET /health`, `GET /version`, `GET /me`
- Metrics: `GET /metrics?start=&end=&symbol=&account=&tz=` returns KPIs + equity + `unreviewed_count`.
- Trades: `GET /trades`, `POST /trades`, `PATCH /trades/{id}`, `DELETE /trades/{id}`, `GET /trades/{id}`
  - Attachments: `POST/GET /trades/{id}/attachments`, `GET /trades/{id}/attachments/{att_id}/download`, `GET /trades/{id}/attachments/{att_id}/thumb`, `DELETE /trades/{id}/attachments/{att_id}`, `POST /trades/{id}/attachments/reorder`, `POST /trades/{id}/attachments/batch-delete`.
- Journal: `GET /journal/dates?start&end`, `GET/PUT/DELETE /journal/{YYYY-MM-DD}`
  - Journal attachments: `GET/POST /journal/{jid}/attachments`, `GET /journal/{jid}/attachments/{att_id}/download|thumb`, `DELETE /journal/{jid}/attachments/{att_id}`.
- Templates: `GET /templates?target=trade|daily`, `POST /templates`, `PATCH /templates/{id}`, `DELETE /templates/{id}`.

Web Routes (current)
- `/dashboard`: KPIs, equity curve, calendar (Mon default, configurable Mon/Sun), journal indicators.
- `/trades` and `/trades/[id]`: list and detail; notes editor supports applying templates; attachments UI with thumbs, reorder, batch delete.
- `/journal/[date]`: daily notes editor, link trades, attachments, delete journal; apply templates (daily target).
- `/templates`: manage templates (create/edit/delete; drag-reorder sections; placeholders; defaults).

Environment / Config
- Web: `NEXT_PUBLIC_API_BASE` (default http://localhost:8000).
- API: `ATTACH_BASE_DIR` (/data/uploads), `ATTACH_MAX_MB` (10), `ATTACH_THUMB_SIZE` (256), `MAX_UPLOAD_MB` (20).

Data & Storage
- Migrations up to `0012_note_templates`. Attachments now include optional `journal_id` and `sort_order`; `trade_id` nullable.
- Storage layout: `/data/uploads/{trade_id}/...` and `/data/uploads/journal/{journal_id}/...`; thumbs under `thumbs/`.

UX Conventions (Editors)
- Apply Template: choose template → toggle sections → inserts Markdown: `## {heading}\n\n{placeholder}`.
- Create Template from Notes: parses `##`/`###` headings to build sections; falls back to single “Notes” section.
- Toasts: success/error toasts for save/delete/upload/reorder actions.

Next Tasks (M4, prioritized)
1) Templates polish
   - Reordering sections persisted on save for both new and existing templates.
   - Improve parse-to-template: support deeper headings and code blocks; strip trailing whitespace.
   - Add minimal validation (non-empty name; at least one section with non-empty heading).
2) Editor UX polish
   - Add “Insert at cursor” (currently appends to end).
   - Keyboard shortcuts: Cmd/Ctrl+S to save notes; Esc to cancel reordering.
3) Attachments quality of life
   - Inline rename/caption edits for trade and journal attachments.
   - Multi-select download (zip) endpoint (server-side streaming zip of selected ids).
4) Calendar + Journal
   - Option to hide weekends; indicate journal exists with count of attachments.
   - Day cell: link to trades and journal with clearer affordances.

Acceptance for this tranche
- Templates: create/edit/delete, reorder sections (drag), apply to Trade and Daily; create-from-notes handles `##`/`###` reliably; toasts shown on actions.
- Editors: notes save via button and keyboard; toasts confirm; apply insert works as expected.
- Attachments: reorder and batch delete for trades; journal delete clears indicator on calendar.

How to Run
- Dev: `docker compose up --build` and visit `/dashboard` → `/templates`.
- Tests: `make test` (SQLite migrations compatible via batch mode). Ensure Pillow present for thumb tests (optional fallback supported).

