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
