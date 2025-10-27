# Edge‑Journal — User Guide (Current)

This guide reflects the app as it runs today: Templates for notes, Daily Journal, Trades with attachments, and basic dashboards.

## Quick Start
- Requirements: Docker Desktop (or Compose), ~2 GB free disk.
- Run: `docker compose up --build`
- Web: http://localhost:3000
- API: http://localhost:8000 (health at `/health`)

Sign up in the web UI using any email/password (local dev). Then follow the workflows below.

Tip: Use the 🌙/☀️ button in the top navigation to toggle Catppuccin Mocha dark mode. Your choice persists across sessions.

Fonts: The UI prefers a Nerd Font (e.g., JetBrainsMono Nerd Font). To see the patched glyphs/icons, install a Nerd Font locally (https://www.nerdfonts.com/) and your browser will use it automatically. Otherwise, the app falls back to common monospaced system fonts.

## Workflows

### Dashboard
- Go to `/dashboard` for KPIs, equity curve, and calendar.
- The calendar indicates presence of journal entries (blue dot) and attachment counts (×N), and colors days green/red by PnL.
- Toggle “Hide weekends” to switch between 7‑day and 5‑day calendar views; preference is remembered.

#### Calendar badges legend
- ⚠️: Loss streak exceeded (day)
- 🟨: Losing day streak exceeded (week)
- 🟧: Losing week streak exceeded (month)
- ⛔: Risk cap exceeded (minimum of template/grade/account caps)

### Trades
- Go to `/trades` to view imported or manually created trades.
- Filters: symbol, account, and date range. Sort by time, PnL, symbol, or account.
- Create a trade manually using required fields, or import CSVs (see below).

#### Trade detail and notes
- Open a trade row to view details, notes, and attachments.
- Notes are Markdown and support templates:
  - “Apply Template” dropdown → pick template → check/uncheck sections → “Insert”.
  - Insertion happens at the current cursor position in the textarea.
  - “Create template from these notes” builds a template from `##`/`###` headings.
- Save with the button or keyboard shortcut (see Shortcuts).

#### Trade attachments
- Upload images (PNG/JPG/JPEG/WebP) and PDFs. The server strips EXIF and generates thumbnails for images.
- Optional metadata per attachment: timeframe, state, view, caption, reviewed.
- Reorder: toggle "Reorder", then drag cards; press Esc to exit reorder mode.
- Multi‑select: use checkboxes to select attachments and then:
  - "Delete Selected" — removes files and DB rows.
  - "Download Selected" — downloads a ZIP file of the chosen attachments.
- Inline edit: click "Edit" on a card to change metadata inline, then Save.

### Saved Views

Save and recall filter combinations with meaningful names for quick access to common trade queries.

#### Saving a View

1. Navigate to `/trades`
2. Build your filter using the Filter Builder:
   - Add conditions (e.g., Symbol contains EUR, P&L > 0)
   - Optionally add nested AND/OR groups for complex queries
   - Click "Apply Filters"
3. Click **"💾 Save as View"** button
4. In the modal:
   - **Name**: Enter a descriptive name (e.g., "EUR Winners", "London A-Setups")
   - **Description** (optional): Add context about this view
   - **Set as default**: Check to auto-load this view on Trades page visits
5. Click **"Save View"**

#### Using Saved Views

**Quick Selection:**
- Use the "Saved View" dropdown at the top of the Trades page
- Select a view from the list to automatically apply its filters
- Default view (marked with ⭐) loads automatically when visiting `/trades`
- Select "No view (show all)" to clear the view and show unfiltered trades

**URL Sharing:**
- Share filtered views via URL: `/trades?view=EUR%20Winners`
- View names are case-insensitive for URL matching
- Recipients need an account and must be logged in to access views
- Each user's views are private and isolated

**Default View:**
- One view can be set as default per user
- Default view loads automatically when visiting `/trades` without a view parameter
- Override by selecting a different view from the dropdown or using a URL parameter

#### Managing Views

Navigate to **Settings → Saved Views** (`/settings/views`) to manage your saved views:

**View List:**
- Displays all your saved views with name, description, and default status
- Views are ordered with default view first, then by creation date

**Actions:**
- **Set Default**: Make this view load automatically (unsets any previous default)
- **Delete**: Remove view with confirmation (cannot be undone)

**Constraints:**
- View names must be unique per user
- Only one default view allowed per user
- Views are automatically deleted if the user account is deleted

#### API Usage

**List Views:**
```bash
GET /views
Authorization: Bearer <token>

Response:
[
  {
    "id": 1,
    "name": "EUR Winners",
    "description": "Profitable EUR pairs",
    "filters_json": "{\"operator\":\"AND\",\"conditions\":[...]}",
    "is_default": true,
    "created_at": "2025-10-25T10:00:00Z",
    "updated_at": "2025-10-25T10:00:00Z"
  }
]
```

**Create View:**
```bash
POST /views
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "London A-Setups",
  "description": "A-grade trades during London session",
  "filters_json": "{\"operator\":\"AND\",\"conditions\":[...]}",
  "is_default": false
}
```

**Get View by ID:**
```bash
GET /views/{view_id}
Authorization: Bearer <token>
```

**Get View by Name:**
```bash
GET /views/by-name/{view_name}
Authorization: Bearer <token>
```

**Apply View to Trades:**
```bash
# By ID
GET /trades?view=1

# By name (case-insensitive)
GET /trades?view=London%20A-Setups
GET /trades?view=london%20a-setups  # also works
```

**Update View:**
```bash
PATCH /views/{view_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description",
  "is_default": true
}
```

**Delete View:**
```bash
DELETE /views/{view_id}
Authorization: Bearer <token>
```

#### Tips & Best Practices

- **Naming**: Use descriptive names like "Profitable EUR/USD" instead of "View 1" for better organization
- **Default View**: Set your most frequently used filter as default to save time on each visit
- **URL Sharing**: Great for sharing analysis with team members or bookmarking common queries (requires accounts)
- **Complex Filters**: Combine saved views with additional sorting and pagination parameters
- **Backup**: Views are stored in the database; filters are preserved as JSON for portability
- **Refresh**: If a view doesn't load correctly, refresh the page and try selecting it again

### Daily Journal
- Visit `/journal/YYYY-MM-DD` for that day’s entry. Set a title and write Markdown notes.
- “Apply Template” works like trade notes (insert at cursor, pick sections).
- “Create template from these notes” infers sections from `##`/`###` headings.
- Link trades: the page lists trades for the same day; check trades to link and “Save Links”.
- Journal attachments: same features as trades — upload, metadata, inline edit, multi‑select delete/download, and drag‑reorder.
- Delete journal: use the button to remove the entry and its attachments.
 - Keyboard: Esc exits attachment reorder mode.

### Templates
- Manage templates at `/templates`.
- Create: define a name and add sections with heading, default toggle, and placeholder.
- Reorder sections by dragging.
- Edit existing templates inline and Save or Delete.
- Target: templates can be for `trade` or `daily` and appear in the respective editors.

### CSV Imports
- Upload CSV at `/upload`. Choose/confirm a preset, adjust the mapping, and set timezone used for the CSV timestamps.
- Preview the first rows with inline errors; commit to create/update trades.
- See import history at `/uploads`, download error CSVs, or delete an import (deletes its trades).

## PDF Reports

Edge-Journal can generate professional PDF reports with metrics, charts, and trade details. Reports honor your current filters and saved views, allowing you to analyze specific subsets of your trading data.

### Report Types

| Report Type | Description | Implementation Status |
|-------------|-------------|-----------------------|
| **Monthly** | Full month breakdown with weekly/daily hierarchies | ✅ Fully implemented |
| **Daily** | Single day performance with all trades | 🚧 Stub only |
| **Weekly** | Week performance with daily breakdowns | 🚧 Stub only |
| **Yearly** | Full year with monthly breakdowns | 🚧 Stub only |
| **YTD** | Year-to-date performance | 🚧 Stub only |
| **All-Time** | Complete trading history | 🚧 Stub only |
| **Trade** | Single trade detail report | 🚧 Stub only |

**Note**: Currently only the Monthly report is fully implemented with complete data and visualizations. Other report types exist as API stubs that will throw a "not yet implemented" error.

### Generating Reports (UI)

The easiest way to generate reports is through the web interface:

1. **Navigate to Dashboard** (`/dashboard`)
2. **Click "Generate Report"** button
3. **Configure your report** in the modal:
   - **Report Type**: Choose from Monthly, Weekly, Daily, Yearly, YTD, All-Time
   - **Period Selection**: Varies by report type
     - Monthly: Select year and month
     - Weekly: Select year and ISO week number
     - Daily: Select specific date
     - Yearly/YTD: Select year only
   - **Account Selection**:
     - Use "All" to select all accounts
     - Use "None" to clear selection
     - Or manually select specific accounts from the list
   - **Account Separation Mode**:
     - **Combined**: Single report with all accounts merged into one equity curve
     - **Grouped**: Single report with separate sections per account
     - **Separate**: Generate individual PDF per account (not yet implemented)
   - **Saved View** (optional): Apply a saved filter view to limit trades in the report
   - **Theme**: Choose Light or Dark mode for the PDF styling
   - **Include Screenshots**: Toggle to include/exclude trade attachments
4. **Click "Generate"**: PDF will be generated and automatically downloaded

### Report Contents

A Monthly report includes:

**Cover Page**:
- Report title with period (e.g., "Monthly Report: January 2025")
- Generation timestamp
- Account names included
- Theme indicator

**Executive Summary**:
- **Metrics Grid**: Total P&L, Win Rate, Profit Factor, Average Win/Loss, Max Drawdown, Trade Count
- **Equity Curve**: Line chart showing cumulative equity over the month
- **Calendar Heatmap**: Month view with each day colored by P&L performance

**Weekly/Daily Breakdown**:
- Hierarchical structure: Month → Week 1-5 → Day 1-31 → Individual Trades
- Each level shows relevant metrics
- Trade details include:
  - Symbol, side, entry/exit prices
  - Open/close times
  - Quantity and fees
  - Net P&L (color-coded)
  - Notes (Markdown rendered)
  - Playbook grade and compliance score (if applicable)
  - Screenshots/attachments (inline or appendix reference)

**Screenshot Appendix** (optional):
- For trades with >2 screenshots, full-size images are placed in an appendix
- Trades with ≤2 screenshots show them inline

### Account Separation Modes

Reports can aggregate multiple accounts in different ways:

- **Combined**: All trades treated as a single unified account
  - Single equity curve
  - Single metrics calculation
  - Best for viewing overall performance

- **Grouped**: Separate sections per account within one PDF
  - Each account gets its own metrics and equity curve
  - Allows comparison within one document
  - Still generates a single PDF file

- **Separate**: Individual PDF per selected account (not yet implemented)
  - Would generate multiple PDFs in a ZIP file
  - Useful for sharing account-specific reports

### Report History

Previously generated reports are stored and can be accessed:

1. Navigate to **Settings → Report History** (or use API directly)
2. View list of generated reports with:
   - Filename
   - Report type
   - Generation timestamp
   - File size
3. Actions available:
   - **Download**: Re-download a previous report
   - **Delete**: Remove report from history

Reports are stored at `/data/exports/{user_id}/reports/` with filenames like:
- `monthly_report_2025_01.pdf`
- `daily_report_2025-01-15.pdf`
- `weekly_report_2025_W03.pdf`

### API Usage

Generate reports programmatically via the API:

**Generate Monthly Report**:
```bash
POST /api/reports/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "monthly",
  "period": {
    "year": 2025,
    "month": 1
  },
  "account_ids": [1, 2],
  "account_separation_mode": "combined",
  "view_id": null,
  "theme": "dark",
  "include_screenshots": true
}

Response: PDF file download (application/pdf)
```

**Generate Daily Report**:
```bash
POST /api/reports/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "daily",
  "period": {
    "date": "2025-01-15"
  },
  "account_ids": null,
  "account_separation_mode": "combined",
  "theme": "light",
  "include_screenshots": false
}

Response: 501 Not Implemented (stub only)
```

**Generate Yearly Report**:
```bash
POST /api/reports/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "yearly",
  "period": {
    "year": 2025
  },
  "account_ids": [1],
  "theme": "light"
}

Response: 501 Not Implemented (stub only)
```

**Apply Saved View to Report**:
```bash
POST /api/reports/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "monthly",
  "period": {
    "year": 2025,
    "month": 1
  },
  "view_id": 3,  // Apply saved view filters
  "theme": "dark"
}

Response: PDF with only trades matching the saved view filters
```

**List Report History**:
```bash
GET /api/reports/history
Authorization: Bearer <token>

Response:
[
  {
    "id": 1234567890,
    "filename": "monthly_report_2025_01.pdf",
    "report_type": "monthly",
    "created_at": "2025-10-25T14:30:00Z",
    "file_size_bytes": 2457600
  },
  {
    "id": 987654321,
    "filename": "daily_report_2025-01-15.pdf",
    "report_type": "daily",
    "created_at": "2025-10-24T10:15:00Z",
    "file_size_bytes": 524288
  }
]
```

**Download Report from History**:
```bash
GET /api/reports/download/{filename}
Authorization: Bearer <token>

Example:
GET /api/reports/download/monthly_report_2025_01.pdf

Response: PDF file download (application/pdf)
```

**Delete Report**:
```bash
DELETE /api/reports/{filename}
Authorization: Bearer <token>

Example:
DELETE /api/reports/monthly_report_2025_01.pdf

Response:
{
  "message": "Report deleted successfully",
  "filename": "monthly_report_2025_01.pdf"
}
```

### Theme Customization

Reports support two built-in themes:

**Light Theme**:
- White background
- Dark text (#1e293b)
- Blue accents (#2563eb)
- Professional appearance for printing

**Dark Theme**:
- Dark background (#1e1e2e - Catppuccin Mocha)
- Light text (#cdd6f4)
- Accent colors from Catppuccin palette
- Reduced eye strain for screen viewing

Both themes use CSS variables defined in the report templates, ensuring consistent styling across all report types.

### Tips & Best Practices

- **Start with Monthly**: The monthly report is the most comprehensive and fully implemented
- **Use Saved Views**: Apply filters via saved views to focus reports on specific strategies or instruments
- **Account Separation**: Use "combined" for overall performance, "grouped" for per-account analysis
- **Screenshots**: Disable screenshots for faster generation and smaller file sizes
- **Report History**: Regularly clean up old reports to save disk space
- **Theme Selection**: Use dark theme for screen review, light theme for printing

### Troubleshooting

**Report generation fails with 501 error**:
- You're trying to generate a report type that's not yet implemented
- Currently only monthly reports are fully supported
- Solution: Use `"type": "monthly"` in your request

**PDF is missing trades**:
- Check if a saved view filter is applied (`view_id` in request)
- Verify account selection includes the accounts you expect
- Ensure the period matches when your trades occurred

**Report generation is slow**:
- Large numbers of screenshots increase generation time
- Try setting `include_screenshots: false` for faster generation
- Monthly reports with 100+ trades may take 10-20 seconds

**Screenshot Appendix is huge**:
- Screenshots are embedded as base64 in the PDF
- Consider limiting screenshot uploads or disabling them in reports
- Future versions may add thumbnail-only options

## Keyboard Shortcuts
- Cmd/Ctrl+S: Saves notes on Trade detail and Daily journal pages.
- Esc: Exits attachment reorder mode on the Trade detail page.

## API Highlights

### Health/Auth/Metrics
- `GET /health`, `GET /version`, `GET /me`
- `GET /metrics?start=&end=&symbol=&account=&tz=` → KPIs, equity, and `unreviewed_count`

### Trades
- `GET /trades` — list with filters and optional `?view=<id|name>` parameter; `GET /trades/{id}` — detail with attachments
- `POST /trades` — manual create; `PATCH /trades/{id}` — update notes/fees/net/post_analysis
- Attachments:
  - `GET /trades/{id}/attachments`
  - `POST /trades/{id}/attachments` (multipart; images/PDFs)
  - `GET /trades/{id}/attachments/{att_id}/download|thumb`
  - `DELETE /trades/{id}/attachments/{att_id}`
  - `POST /trades/{id}/attachments/reorder` (body: JSON array of IDs)
  - `POST /trades/{id}/attachments/batch-delete` (body: IDs)
  - `POST /trades/{id}/attachments/zip` (body: IDs → ZIP download)
  - `PATCH /trades/{id}/attachments/{att_id}` (update metadata)

### Daily Journal
- `GET /journal/dates?start=&end=` → available dates
- `GET/PUT/DELETE /journal/{YYYY-MM-DD}` — upsert/delete by date; response includes `id`
- `POST /journal/{journal_id}/trades` — set linked trade IDs
- Attachments:
  - `GET /journal/{journal_id}/attachments`
  - `POST /journal/{journal_id}/attachments` (multipart)
  - `GET /journal/{journal_id}/attachments/{att_id}/download|thumb`
  - `DELETE /journal/{journal_id}/attachments/{att_id}`
  - `POST /journal/{journal_id}/attachments/reorder` (IDs)
  - `POST /journal/{journal_id}/attachments/batch-delete` (IDs)
  - `POST /journal/{journal_id}/attachments/zip` (IDs → ZIP)
  - `PATCH /journal/{journal_id}/attachments/{att_id}` (update metadata)

### Templates
- `GET /templates?target=trade|daily`
- `POST /templates` — create `{ name, target, sections[] }`
- `PATCH /templates/{id}` — update name/sections
- `DELETE /templates/{id}`

### Saved Views
- `GET /views` — list all saved views for current user
- `POST /views` — create new saved view with filters_json
- `GET /views/{view_id}` — get view by ID
- `GET /views/by-name/{view_name}` — get view by name (case-insensitive)
- `PATCH /views/{view_id}` — update view (name, description, filters, is_default)
- `DELETE /views/{view_id}` — delete view

### Reports
- `POST /api/reports/generate` — generate PDF report (returns PDF download)
  - Body: `{ type, period, account_ids, account_separation_mode, view_id, theme, include_screenshots }`
- `GET /api/reports/history` — list previously generated reports
- `GET /api/reports/download/{filename}` — download report from history
- `DELETE /api/reports/{filename}` — delete report from history

## Configuration
- Web
  - `NEXT_PUBLIC_API_BASE` default `http://localhost:8000`
- API
  - `MAX_UPLOAD_MB` — general file limit (used in CSV import flows; default 20)
  - `ATTACH_BASE_DIR` — storage directory for attachments (default `/data/uploads`)
  - `ATTACH_MAX_MB` — per-file attachment size in MB (default 10)
  - `ATTACH_THUMB_SIZE` — generated thumbnail max size in px (default 256)
- Allowed attachment types: `.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`

## Tips
- When applying a template, use the “Insert” button to insert at cursor.
- After upload or delete actions, the UI will refresh and show toasts for success/error.
- For large attachment sets, use multi‑select + ZIP to download in one go.

## Upgrading

- For local development, run `docker compose up --build`. The API runs Alembic migrations automatically on startup.
- For production or managed environments, run `alembic upgrade head` against the API database before deploying a new version.

### Playbooks v1 (M5)

Version v0.5.x introduces Playbooks v1:
- New tables: `playbook_templates`, `playbook_responses`, `playbook_evidence_links`, `user_trading_rules`; optional `breach_events`. `accounts` gains `account_max_risk_pct`.
- New endpoints: `/playbooks/*` for templates, evaluation, responses, and evidence; `/settings/trading-rules`; `/metrics/calendar` returns `breaches` per day.
- Web: Playbooks UI at `/playbooks`; Playbook panel on Trade details; Instrument Checklist on Daily Journal.

Fonts: If you want to self‑host Nerd Fonts, place TTFs under `web/public/fonts/` and add preload links in `web/app/layout.tsx`. By default, the app uses locally installed fonts and avoids network font fetches to keep dev logs clean.
