Edge‑Journal — Next Session Context (M4 kickoff)

Version: v0.3.0 (M3 complete, starting M4)

What’s Done (high level)
- M2: CSV import (preview/commit), presets, per‑upload timezone, imports history, error CSV, user scoping.
- M3: Dashboard KPIs + equity, calendar (by day), tz-aware metrics, Trades filters/date presets/sorting/pagination/page size, typable dropdowns (symbol/account), manual add, journal notes, delete + undo, CSV export, sticky headers.

Key Web Routes
- `/upload` → CSV preview/commit (tz, mapping, presets, save_as)
- `/uploads` and `/uploads/[id]` → history + error CSV + delete
- `/trades` → list with filters (symbol/account/start/end), date presets, sort, pagination, add, journal inline
- `/trades/[id]` → Trade Detail (Overview, Notes, Attachments)
- `/dashboard` → KPIs, all‑time equity curve (tooltip), month calendar (click → trades day)

Key API Endpoints
- Health/version: `GET /health`, `GET /version`, `GET /me`
- Metrics: `GET /metrics?start=YYYY-MM-DD&end=YYYY-MM-DD&symbol=&account=&tz=` (tz is IANA)
- Trades:
  - `GET /trades?start=&end=&symbol=&account=&limit=&offset=&sort=`
  - `POST /trades` (manual create; fields: account_id|account_name, symbol, side, open_time, close_time?, qty_units, entry_price, exit_price?, fees?, net_pnl?, notes_md?, tz?)
  - `PATCH /trades/{id}` (notes_md, post_analysis_md, fees, net_pnl, reviewed)
  - `DELETE /trades/{id}` → returns `{ restore_payload: {...} }` for undo
  - `GET /trades/{id}` → TradeDetailOut (attachments included)
  - Attachments:
    - `POST /trades/{id}/attachments` (multipart: file, timeframe, state, view, caption, reviewed)
    - `GET /trades/{id}/attachments` (list)
    - `GET /trades/{id}/attachments/{att_id}/download`
    - `DELETE /trades/{id}/attachments/{att_id}`
  - `GET /trades/symbols?account=` → distinct symbols for user
- Uploads:
  - `POST /uploads` (initial header parse)
  - `POST /uploads/preview` (mapping/preset/tz)
  - `POST /uploads/commit` (mapping/preset/account/tz/save_as)
  - `GET /uploads`, `DELETE /uploads/{id}`, `GET /uploads/{id}/errors.csv`
- Accounts/Presets: `GET/POST /accounts`, `GET/POST /presets`

Environment / Config
- Web: `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`), `NEXT_PUBLIC_MAX_UPLOAD_MB` (default 20)
- API: `MAX_UPLOAD_MB` (default 20), `ATTACH_MAX_MB` (default 10), `ATTACH_BASE_DIR` (default `/data/uploads`)

Data & Storage
- DB migrations up to `0007_trade_journal_attachments`: adds `trades.reviewed`, `trades.post_analysis_md`; creates `attachments`.
- Attachments saved under `/data/uploads/{trade_id}/` with metadata (timeframe, state, view, caption, reviewed).

Timezones
- CSV tz (commit time) converts timestamps → UTC for storage.
- Display tz (dashboard/trades) is a view preference and doesn’t mutate data.
- If CSV is already UTC, commit with `tz=UTC` to avoid double shift.

UI Notes
- Next App Router: `useSearchParams()` wrapped in `<Suspense>` (see `/trades/page.tsx`).
- Typable dropdowns use `<input list=...>` with datalist options for Symbols/Accounts.
- Trades supports Undo for deletes via restore payload.
- Dashboard equity curve has a simple hover tooltip; calendar click drills into day.

Open Items (M4)
1) Trade Attachments polish
   - Generate thumbnails for images; strip EXIF metadata on upload.
   - UI previews (thumbs), drag-sort (optional), batch delete.
2) Daily Journal page
   - Route `/journal/YYYY-MM-DD` with Markdown editor, attachments, and linked trades list.
   - API: DailyEntry model (date, account?, title, notes_md, reviewed?), CRUD + attachments + link/unlink trades.
   - Calendar integration: indicator if journal exists; button to open journal for day.
3) Note Templates (for both Trade and Daily editors)
   - Model: `{ id, user_id, name, target: 'trade'|'daily', sections: [{ heading, default_included, placeholder? }] }`
   - API: `GET/POST/PATCH/DELETE /templates`
   - UI: “Apply Template” → choose sections (checkboxes) → inserts Markdown headings/placeholder text.

Stretch (deferred)
- Dashboard month CSV export honoring filters/timezone.
- Loading skeletons across Dashboard KPIs/Calendar.
- Sticky headers in more tables (e.g., uploads) and CSV export for wider datasets.

How to Run
- Tests: `make test`
- Dev stack: `docker compose up --build`
- Login via Web → `/upload` → `/uploads` → `/trades` → `/dashboard`

Acceptance (so far)
- Trade Detail: edit notes + post‑analysis; upload attachments ≤10MB (png/jpg/jpeg/webp/pdf) with metadata; list/download/delete.
- Dashboard/Trades features per M3 operate with filters and tz as expected.

