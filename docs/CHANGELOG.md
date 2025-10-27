# Changelog

All notable changes to Edge‑Journal are documented here. Version is sourced from the root `VERSION` file.

## [0.7.3] - 2025-10-25

### Added - M7 Phase 3: PDF Report Generation

**Backend:**
- WeasyPrint-based PDF generation system with HTML/CSS templates
- New `api/app/reports.py` module with `ReportGenerator` class
- Monthly report type fully implemented with hierarchical breakdown (Month → Weeks → Days → Trades)
- Stub implementations for daily, weekly, yearly, YTD, and all-time report types
- Jinja2 templating system with `base.html` and `monthly.html` report templates
- Light and dark theme support via CSS variables (Catppuccin Mocha for dark theme)
- Equity curve chart generation using matplotlib (SVG base64-encoded)
- Performance metrics calculation: total P&L, win rate, profit factor, average win/loss, max drawdown, trade count
- Account selection and filtering with three separation modes:
  - **Combined**: Single report with all accounts merged
  - **Grouped**: Separate sections per account in one PDF
  - **Separate**: Individual PDFs per account (not yet implemented)
- Integration with saved views: apply filter views to limit trades in reports
- Screenshot/attachment embedding with inline display (≤2) or appendix reference (>2)
- Report history management with storage in `/data/exports/{user_id}/reports/`

**API Endpoints** (`api/app/routes_reports.py`):
- `POST /api/reports/generate` — Generate PDF report with full configuration
  - Supports all report types (monthly fully implemented, others return 501)
  - Returns PDF as direct download with proper Content-Disposition headers
  - Validates period requirements based on report type
- `GET /api/reports/history` — List previously generated reports with metadata
  - Returns filename, report type, creation timestamp, file size
  - Sorted by creation time (newest first)
- `GET /api/reports/download/{filename}` — Download report from history
  - Path traversal protection
  - User isolation (can only access own reports)
- `DELETE /api/reports/{filename}` — Delete report from history
  - Removes file from disk
  - Returns confirmation message

**Schemas** (`api/app/schemas.py`):
- `ReportGenerateRequest`: Full request schema with type, period, filters, theme options
  - `type`: Literal["trade", "daily", "weekly", "monthly", "yearly", "ytd", "alltime"]
  - `period`: Nested object with year, month, week, date, trade_id fields
  - `account_ids`: Optional list for filtering specific accounts
  - `account_separation_mode`: Literal["combined", "grouped", "separate"]
  - `view_id`: Optional saved view ID to apply filters
  - `theme`: Literal["light", "dark"] for PDF styling
  - `include_screenshots`: Boolean flag for attachment inclusion
- `ReportPeriod`: Period specification with conditional fields based on report type
- `ReportHistoryOut`: Report metadata for history listings

**Report Templates** (`api/templates/reports/`):
- `base.html`: Base layout with theme support, header/footer, page breaks
  - CSS variables for theme colors
  - Typography system with proper font stacks
  - Print-optimized styles for page breaks and margins
- `monthly.html`: Monthly report structure
  - Cover page with report metadata
  - Executive summary with metrics grid, equity curve, calendar heatmap
  - Hierarchical weekly/daily breakdown with nested sections
  - Trade detail cards with symbol, times, prices, P&L, notes, playbook data
  - Screenshot appendix for trades with >2 attachments
  - Markdown rendering for notes
- Component includes: metrics cards, equity charts, calendar heatmaps, trade tables

**Frontend:**
- `ReportGenerateModal` component (`web/app/components/ReportGenerateModal.tsx`)
  - Full UI for report configuration with intuitive form controls
  - Report type selector with descriptions
  - Dynamic period picker (changes based on report type)
    - Monthly: year + month dropdowns
    - Weekly: year + ISO week number
    - Daily: date picker
    - Yearly/YTD: year only
  - Account multi-select with "All" and "None" shortcuts
  - Account separation mode selector with radio buttons
  - Saved view selector (optional) to apply filters
  - Theme toggle (light/dark) with preview icons
  - Include screenshots checkbox
  - Loading states during generation with spinner
  - Error handling with user-friendly messages
  - Auto-download on successful generation
- Dashboard integration: "Generate Report" button added to `/dashboard` page
- Modal state management with proper cleanup on close

**Report Features:**
- Monthly reports include:
  - Cover page with title, generation date, account list
  - Executive summary: KPIs, equity curve chart, calendar heatmap
  - Week-by-week breakdown with week-level metrics
  - Day-by-day breakdown with daily metrics
  - Trade-by-trade details with full information
  - Inline screenshots (≤2 per trade) or appendix references
  - Screenshot appendix section with full-size images
  - Markdown-rendered notes
  - Playbook grades and compliance scores
- Equity curves generated as SVG charts with matplotlib
- Calendar heatmaps rendered as HTML tables with color-coded cells
- Metrics calculated from filtered trade data
- File naming convention: `{type}_report_{period}.pdf`
  - Examples: `monthly_report_2025_01.pdf`, `daily_report_2025-01-15.pdf`

**Testing:**
- Report generation endpoints tested for validation and error handling
- PDF binary output verified for proper Content-Type headers
- History listing tested with multiple reports
- Download/delete endpoints tested for security (path traversal, user isolation)

**Dependencies:**
- WeasyPrint 62.3 added to `requirements.txt` for PDF generation
- matplotlib for chart generation (SVG output)
- Jinja2 (already present) for template rendering

**Implementation Status:**
- ✅ Monthly reports: Fully implemented with complete data and visualizations
- 🚧 Daily, Weekly, Yearly, YTD, All-Time reports: Stub implementations (return 501 Not Implemented)
- 🚧 Separate account mode: Returns 501 error (not yet implemented)
- ✅ Report history: Fully functional
- ✅ Theme support: Light and dark themes working
- ✅ Screenshot embedding: Working with inline/appendix logic

**Known Limitations:**
- Only monthly reports generate actual content; other types are stubs
- Separate account mode generates 501 error instead of multiple PDFs
- Large reports (100+ trades) may take 10-20 seconds to generate
- Screenshots embedded as base64 increase file size significantly
- No automatic cleanup of old reports (manual deletion required)

### Fixed
- Report generation error handling improved with specific 501 errors for unimplemented types
- Path traversal security in filename handling for download/delete endpoints

## [0.7.2] - 2025-10-25

### Added - M7 Phase 2: Saved Views

**Backend:**
- New `saved_views` table to persist filter combinations with migration 0018_saved_views.
- `/views` API endpoints for full CRUD operations on saved views (list, create, get by ID/name, update, delete).
- `GET /trades` now accepts `?view=<id|name>` parameter to apply saved view filters.
- Default view support: one view per user can be marked as default and auto-applies on page load.
- User isolation with unique name constraints per user.
- View retrieval by name supports case-insensitive lookup for URL-friendly sharing.

**Frontend:**
- SaveViewModal component to save current filter configuration with name, description, and default flag.
- ViewSelector dropdown component for quick switching between saved views.
- `/settings/views` management page to list, delete, and set default views.
- Trades page integration: auto-loads default view on mount, displays "Save as View" button when filters active.
- URL addressability: share filtered views via `/trades?view=<name>` links.

**Features:**
- ⭐ Set one view as default (automatically loads when visiting Trades page)
- 💾 Save complex filter combinations with meaningful names for quick access
- 🔗 Share views via URL-friendly names (e.g., `/trades?view=EUR%20Winners`)
- ⚙️ Manage all saved views in Settings page (rename, delete, set default)
- 🔒 User isolation ensures views are private to each user account

**Testing:**
- Added 15 comprehensive tests for saved views functionality (89 total tests passing)
- Full coverage of CRUD operations, user isolation, default view logic, and trades integration
- Tests verify view application by both ID and name parameters

### Fixed
- Datetime serialization in Pydantic schemas for SavedView model

## [0.6.0] - 2025-10-25
### M6: Guardrails + Account Lifecycle
**Backend:**
- Add account closure tracking: `closed_at`, `close_reason`, `close_note` fields.
- Add account lifecycle API: `POST /accounts/{id}/close` and `POST /accounts/{id}/reopen`.
- Add `include_closed` query parameter to `GET /accounts` endpoint.
- Implement enforcement mode logic ('off'|'warn'|'block') for risk cap and loss streak violations.
- Risk cap enforcement: playbook responses now check against min cap and enforce based on user's enforcement_mode.
- Loss streak enforcement: trade creation checks daily loss streaks and enforces based on enforcement_mode.
- Import guard: CSV uploads reject trades targeting closed accounts with clear error message.
- Breach logging: create breach events for loss streaks (not just risk caps).
- Migration 0017: add account closure tracking fields.

**Web UI:**
- Settings: enable 'block' enforcement mode option (previously disabled).
- Settings: clarify enforcement mode labels (Off/Warn/Block).

**API Schema:**
- Add `AccountClose` and `AccountReopen` schemas for structured account lifecycle operations.
- Add `warning` field to `PlaybookResponseOut` for enforcement mode warnings.
- Extend `AccountOut` with `closed_at`, `close_reason`, `close_note` fields.

**Enforcement Module:**
- New `api/app/enforcement.py` module with `check_risk_cap_breach()` and `check_loss_streaks()` helpers.
- Supports 'off' (no enforcement), 'warn' (log + warn), 'block' (raise 403) modes.

## [0.5.3] - 2025-10-25
- Web: Enable bundled Nerd Fonts with preload and `@font-face` URLs; fall back to local fonts if not present.
- Web: Add `web/public/fonts/README.md` with placement/licensing guidance; OFL included alongside fonts.
- API: Add tests for Playbook Evidence (add/list/delete) and Instrument Checklist flows.
- Docs: Update M5 Playbooks tech design to Implemented; expand USAGE with upgrading and M5 details.
- Repo hygiene: Ignore `results*.txt` build logs.

## [0.5.2] - 2025-10-21
- Web: Fix duplicate function in Playbooks page; rename drag‑drop mover to `moveEditFieldTo`.

## [0.5.1] - 2025-10-21
- Playbooks v1: core models, API routes, migrations, and web UI.
  - Templates CRUD, quickstarts, export/import, versioned updates.
  - Trade responses + instrument checklist + evidence links.
  - Settings for trading rules; calendar breach badges.

## [0.5.0] - 2025-10-21
- Bump to v0.5.0 to start next feature tranche.

