Edge‑Journal M2 — Continuation Notes

Context: We’ve delivered CSV preview + commit, presets, accounts, per‑upload timezone parsing, user scoping for data, uploads history, and a trades list UI. Next we’ll tighten correctness and UX around timezones, idempotency, and error reporting.

1) Timezone correctness (priority)
- Problem: Trades display time may look “off”. Today we:
  - Parse CSV timestamps using `tz` (IANA, e.g., Australia/Sydney) at commit → store UTC
  - UI renders `open_time_utc` with `new Date(iso).toLocaleString()` (browser timezone)
- Likely causes:
  - CSV timestamps already in UTC but `tz` provided (double-shift)
  - Browser/system timezone differs from expected display timezone
- Plan:
  - UI: Add “Display timezone” selector on /trades (default browser), options: UTC, Australia/Sydney, America/New_York, Europe/London, etc.
  - Persist preferred display tz in localStorage.
- Optionally show the stored upload tz beside imports to verify.
  - Implemented: upload tz is stored at commit and shown in the /uploads table.
  - Docs: Clarify “CSV tz vs display tz”: CSV tz applies at commit (conversion to UTC). Display tz is a view choice.
  - Acceptance: Given CSV with Sydney local times, and `tz=Australia/Sydney`, /trades shows the expected local clock when display tz = Australia/Sydney.

2) Error CSV export (imports)
- API: `GET /uploads/{id}/errors.csv` returns `line,reason` for all errors captured.
- UI: On /uploads, show “Download errors” when `error_count > 0`.
- Acceptance: Upload with one bad line exposes a CSV link and correct counts.

3) Auto‑run Alembic (dev)
- On API startup when `ENV=dev`, attempt `alembic upgrade head` once.
- Acceptance: Fresh compose up works without a manual migration step.

4) Upload size limit
- API: Enforce 20 MB limit with a friendly 413 error; configurable by env.
- UI: Warn when file exceeds limit before upload.
  - Env: `MAX_UPLOAD_MB` (API), `NEXT_PUBLIC_MAX_UPLOAD_MB` (Web). Defaults to 20.

5) Idempotency + numbers
- Done: number normalization and stable trade_key rounding.
- Add tests: partial updates (later exit/fees), mixed changes.

6) Preset UX
- List user presets in /upload with autocomplete, “apply on preview” toggle.
- Optional “save_as” on commit (preset name) upon success.

7) Docs
- Add FTMO header mapping notes (duplicate Price columns), timezone guidance, and a quickstart (login → upload → preset → trades).

Debugging the timezone now
- If your CSV timestamps were already UTC, commit with `tz=UTC`.
- Verify browser timezone (System Preferences) vs expected; current UI shows browser‑local time.
- To re‑test quickly: commit one trade (unique symbol), then compare /trades time with expected local clock.

Timezone guidance
- CSV tz vs display tz: CSV tz applies at commit (source timestamps are converted to UTC and stored). Display tz is a view preference on /trades and never changes stored data.
- If your CSV timestamps are already UTC, set `tz=UTC` on commit to avoid double shifting.
- You can switch display timezone on `/trades` via the selector; it persists in `localStorage`.

Quickstart
- Login or register from the top bar.
- Go to `/upload`, choose your CSV. Optionally select a preset (autocomplete) and toggle “Apply on preview”.
- Pick the CSV timezone for the source file. Click Re‑Preview to validate mapping and times. Click Commit to import.
- Visit `/uploads` to see import summaries. If errors exist, use “Download errors” to export `line,reason` and “Delete” to remove a mistaken import (which removes its trades).
- Open `/trades` and set your preferred display timezone from the dropdown.

Commands
- Run tests: `make test`
- Migrate Postgres in compose: `make migrate`
- Start stack: `docker compose up --build`

Checklist for next session
- [ ] Add display timezone selector on /trades
- [ ] Expose upload tz and show on /uploads table
- [ ] Implement `GET /uploads/{id}/errors.csv` + UI link
- [ ] Add API startup migration in dev
- [ ] Enforce 20 MB file size (API + UI)
- [ ] Extend idempotency tests for partial updates
- [ ] Update docs: FTMO + tz quickstart
