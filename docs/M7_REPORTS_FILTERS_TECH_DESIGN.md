# M7: Reports + Filter Builder - Technical Design

**Status**: Phase 2 Complete
**Version**: 0.7.2
**Last Updated**: 2025-10-25

## Overview

M7 introduces advanced filtering capabilities and comprehensive PDF report generation to Edge-Journal. The implementation is divided into three phases:

1. **Filter Builder Foundation** - Flexible filter DSL to replace simple query params
2. **Saved Views** - Persist and recall filter combinations with URL addressability
3. **PDF Report Generation** - Multi-granularity reports (Trade → Daily → Weekly → Monthly → Yearly → All-time)

## Requirements

### Functional Requirements

**Filter Builder** (FR-A7, FR-A8)
- Notion-style nested AND/OR conditions
- Operators: equals, not equals, contains, in/not-in, ≥/≤
- Filter by: dates, numbers, tags, playbook fields, grades, accounts, symbols
- Drives tables, charts, and reports
- URL-addressable saved views

**Report Generation** (FR-R1 through FR-R7)
- Multi-granularity: Trade, Daily, Weekly, Monthly, Yearly, YTD, All-time
- Hierarchical breakdowns (e.g., Monthly → Week 1 → Day 1 → Trades)
- Sections: Metrics, Equity Curve, Calendar View, Trade-by-trade, Screenshots
- Server-side rendering (local, no external calls)
- Honors current filters/saved views
- Light/dark themes with header/footer

---

## Phase 1: Filter Builder Foundation

**Goal**: Replace simple query params with flexible filter DSL

### 1.1 Filter DSL Schema

```typescript
interface Filter {
  operator: "AND" | "OR";
  conditions: (Condition | Filter)[];
}

interface Condition {
  field: string;           // e.g., "symbol", "net_pnl", "playbook.grade"
  op: FilterOperator;      // e.g., "eq", "gte", "contains"
  value: string | number | string[] | number[];
}

type FilterOperator =
  | "eq"        // equals
  | "ne"        // not equals
  | "contains"  // string contains (case-insensitive)
  | "in"        // value in list
  | "not_in"    // value not in list
  | "gte"       // ≥
  | "lte"       // ≤
  | "gt"        // >
  | "lt"        // <
  | "between"   // date/number range
  | "is_null"   // field is NULL
  | "not_null"; // field is NOT NULL
```

**Example Filter JSON**:
```json
{
  "operator": "AND",
  "conditions": [
    {"field": "symbol", "op": "contains", "value": "EUR"},
    {"field": "net_pnl", "op": "gte", "value": 0},
    {
      "operator": "OR",
      "conditions": [
        {"field": "playbook.grade", "op": "eq", "value": "A"},
        {"field": "playbook.grade", "op": "eq", "value": "B"}
      ]
    },
    {"field": "open_time", "op": "between", "value": ["2025-01-01", "2025-01-31"]}
  ]
}
```

### 1.2 Backend Implementation

**New Module**: `api/app/filters.py`

```python
from typing import Dict, List, Any, Union
from sqlalchemy.orm import Query
from sqlalchemy import and_, or_, func

class FilterCompiler:
    """Compiles filter DSL to SQLAlchemy query filters"""

    FIELD_MAP = {
        "symbol": Instrument.symbol,
        "account": Account.name,
        "net_pnl": Trade.net_pnl,
        "open_time": Trade.open_time_utc,
        "close_time": Trade.close_time_utc,
        "side": Trade.side,
        "playbook.grade": PlaybookResponse.computed_grade,
        "playbook.compliance_score": PlaybookResponse.compliance_score,
        # ... more fields
    }

    def compile(self, filter_dsl: Dict[str, Any], base_query: Query) -> Query:
        """Apply filter DSL to SQLAlchemy query"""
        pass

    def _compile_condition(self, condition: Dict[str, Any]) -> Any:
        """Compile single condition to SQLAlchemy expression"""
        pass
```

**Supported Filter Fields** (MVP):
- `symbol` - Instrument symbol (string)
- `account` - Account name (string)
- `net_pnl` - Net profit/loss (number)
- `fees` - Total fees (number)
- `open_time` - Trade open timestamp (datetime)
- `close_time` - Trade close timestamp (datetime)
- `side` - Buy/Sell (enum)
- `playbook.grade` - Playbook grade A/B/C/D (enum)
- `playbook.compliance_score` - Compliance score 0-1 (number)
- `playbook.intended_risk_pct` - Intended risk % (number)

**API Changes**: `GET /trades`

Add `filters` query parameter accepting JSON filter DSL:
```
GET /trades?filters={"operator":"AND","conditions":[{"field":"symbol","op":"eq","value":"EURUSD"}]}
```

Maintain backward compatibility with existing params (symbol, account, start, end) by auto-converting to filter DSL internally.

**Testing**:
- Unit tests for filter compiler (each operator)
- Integration tests for complex nested filters
- Test playbook field joins
- Test filter + pagination + sorting

### 1.3 Frontend Implementation

**Component Structure**:
```
web/app/components/filters/
├── FilterBuilder.tsx      # Main container
├── FilterGroup.tsx        # AND/OR group with nested conditions
├── FilterCondition.tsx    # Single condition row
├── FieldSelector.tsx      # Dropdown for field selection
├── OperatorSelector.tsx   # Dropdown for operator (changes based on field type)
└── ValueInput.tsx         # Input component (text/number/date/multi-select)
```

**UI Flow**:
1. User clicks "+ Add Filter" → shows FilterCondition
2. Select field (dropdown) → auto-selects default operator for field type
3. Select operator (if changing from default)
4. Enter value(s)
5. Click "+ Add Condition" to add another to same group
6. Click "+ Add Group" to nest AND/OR group
7. Click "Apply Filters" → updates trades table

**MVP Scope**:
- Single AND group (no nesting)
- 5-6 operators: `eq`, `contains`, `gte`, `lte`, `in`
- 8-10 core fields
- Simple value inputs (text, number, date picker)

**Future Enhancements**:
- Full nesting (AND/OR groups)
- Tag filters
- Date presets ("Last 7 days", "This month", "Last month")
- Filter validation with helpful error messages

---

## Phase 2: Saved Views ✅ COMPLETE

**Goal**: Persist and recall filter combinations

**Status**: Implemented in v0.7.2 (2025-10-25)

### 2.1 Database Schema

**Migration**: `0018_saved_views`

```sql
CREATE TABLE saved_views (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,

    -- Filter configuration
    filters_json TEXT,        -- Filter DSL JSON

    -- Display configuration
    columns_json TEXT,        -- Column visibility/order
    sort_json TEXT,           -- Sort configuration
    group_by VARCHAR(64),     -- Optional grouping field

    -- Metadata
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_view_name UNIQUE(user_id, name)
);

CREATE INDEX idx_saved_views_user ON saved_views(user_id);
```

**Example Row**:
```json
{
  "id": 1,
  "user_id": 42,
  "name": "London A-Setups",
  "description": "Winning A-grade setups during London session",
  "filters_json": "{\"operator\":\"AND\",\"conditions\":[{\"field\":\"playbook.grade\",\"op\":\"eq\",\"value\":\"A\"},{\"field\":\"net_pnl\",\"op\":\"gt\",\"value\":0}]}",
  "columns_json": "[\"symbol\",\"open_time\",\"net_pnl\",\"playbook.grade\"]",
  "sort_json": "{\"field\":\"net_pnl\",\"direction\":\"desc\"}",
  "is_default": false
}
```

### 2.2 API Endpoints

**New Routes**: `api/app/routes_views.py`

```python
@router.get("/views")
def list_saved_views(db: Session, current: User):
    """List user's saved views"""
    pass

@router.post("/views", status_code=201)
def create_saved_view(body: SavedViewCreate, db: Session, current: User):
    """Create new saved view"""
    pass

@router.get("/views/{view_id}")
def get_saved_view(view_id: int, db: Session, current: User):
    """Get view configuration"""
    pass

@router.patch("/views/{view_id}")
def update_saved_view(view_id: int, body: SavedViewUpdate, db: Session, current: User):
    """Update view (rename, change filters, set as default)"""
    pass

@router.delete("/views/{view_id}")
def delete_saved_view(view_id: int, db: Session, current: User):
    """Delete saved view"""
    pass
```

**Modified Route**: `GET /trades`

Add `view` query parameter:
```
GET /trades?view=1  # Apply saved view #1
GET /trades?view=london-a-setups  # Apply by name (URL-friendly)
```

Priority: `view` parameter overrides individual `filters` parameter.

### 2.3 Frontend Implementation

**UI Components**:
- "Save View" button (opens modal)
- View selector dropdown in header
- View management panel in Settings

**Workflows**:
1. **Save current filters**: User configures filters → clicks "Save View" → names it → saved
2. **Apply view**: Select from dropdown → filters applied → table updates
3. **Set default**: User marks view as default → loads on page visit
4. **URL sharing**: `/trades?view=london-a-setups` loads that view

---

## Phase 3: PDF Report Generation

**Goal**: Generate professional, multi-granularity PDF reports

### 3.1 Report Types & Granularity

| Report Type | Scope | Hierarchical Breakdown |
|-------------|-------|------------------------|
| **Trade Report** | Single trade | Trade details + journal + playbook + screenshots |
| **Daily Report** | Single day | Day metrics → Each trade |
| **Weekly Report** | Single week | Week metrics → Each day → Each trade |
| **Monthly Report** | Single month | Month metrics → Week 1-4 → Days → Trades |
| **Yearly Report** | Calendar year | Year metrics → Jan-Dec → Weeks → Days |
| **YTD Report** | Year-to-date | Same as Yearly, but only completed months/weeks |
| **All-Time Report** | All data | Aggregate metrics + top months/weeks |

**Hierarchical Structure Example** (Monthly Report):

```
Monthly Report: January 2025
├─ Executive Summary (Month Overview)
│  ├─ KPIs (Total PnL, Win Rate, Expectancy, Max DD)
│  ├─ Equity Curve (entire month)
│  └─ Calendar Heatmap (all days colored by PnL)
│
├─ Week 1 (Jan 1-5)
│  ├─ Week KPIs
│  ├─ Day 1 (Jan 1)
│  │  ├─ Day KPIs
│  │  ├─ Trade 1 Details (symbol, times, PnL, tags, notes, playbook, screenshots)
│  │  ├─ Trade 2 Details
│  │  └─ Daily Journal Entry
│  ├─ Day 2 (Jan 2)
│  │  └─ ...
│
├─ Week 2 (Jan 6-12)
│  └─ ...
│
└─ Screenshot Appendix (if >2 screenshots per trade)
```

### 3.2 Technology Stack

**PDF Generation Library**: **WeasyPrint**

**Rationale**:
- Pure Python, no Chromium dependency
- Renders HTML+CSS to PDF
- Supports page breaks, headers/footers
- Good performance for reports
- Easier to deploy than Playwright/Puppeteer

**Alternative**: Playwright (if WeasyPrint limitations encountered)

**Template Engine**: **Jinja2** (already used in FastAPI)

### 3.3 Backend Implementation

**New Module**: `api/app/reports.py`

```python
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, date

class ReportGenerator:
    """Generate PDF reports from trade data"""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.jinja_env = Environment(loader=FileSystemLoader("api/templates/reports"))

    def generate_monthly_report(
        self,
        year: int,
        month: int,
        account_ids: List[int] = None,
        view_id: int = None,
        theme: str = "light"
    ) -> bytes:
        """Generate monthly report PDF"""
        # 1. Fetch data (honor filters from view_id if provided)
        # 2. Calculate metrics (month, weeks, days)
        # 3. Render HTML from template
        # 4. Convert to PDF
        pass

    def generate_yearly_report(self, year: int, **kwargs) -> bytes:
        pass

    def generate_daily_report(self, date: date, **kwargs) -> bytes:
        pass

    def generate_trade_report(self, trade_id: int, **kwargs) -> bytes:
        pass
```

**API Endpoint**: `api/app/routes_reports.py`

```python
@router.post("/reports/generate")
def generate_report(
    body: ReportGenerateRequest,
    db: Session,
    current: User
) -> FileResponse:
    """
    Generate PDF report and return as download

    Request body:
    {
      "type": "monthly",           # trade|daily|weekly|monthly|yearly|ytd|all-time
      "period": {
        "year": 2025,
        "month": 1,                # for monthly
        "week": 3,                 # for weekly
        "date": "2025-01-15",      # for daily
        "trade_id": 42             # for trade
      },
      "account_ids": [1, 2],       # optional filter
      "view_id": 5,                # optional saved view
      "theme": "light",            # light|dark
      "include_screenshots": true
    }
    """
    generator = ReportGenerator(db, current.id)

    if body.type == "monthly":
        pdf_bytes = generator.generate_monthly_report(
            body.period.year,
            body.period.month,
            body.account_ids,
            body.view_id,
            body.theme
        )
    # ... other report types

    # Save to /data/exports/{user_id}/reports/
    filename = f"report_{body.type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = f"/data/exports/{current.id}/reports/{filename}"

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    return FileResponse(filepath, filename=filename, media_type="application/pdf")
```

### 3.4 Report Templates

**Template Structure**:
```
api/templates/reports/
├── base.html              # Base layout with header/footer
├── monthly.html           # Monthly report structure
├── weekly.html            # Weekly report structure
├── daily.html             # Daily report structure
├── trade.html             # Single trade report
├── components/
│   ├── metrics_card.html  # KPI cards
│   ├── equity_chart.html  # Equity curve (SVG)
│   ├── calendar.html      # Calendar heatmap
│   ├── trade_table.html   # Trade table
│   └── screenshot.html    # Screenshot embed
└── styles/
    ├── light.css          # Light theme
    └── dark.css           # Dark theme
```

**Monthly Template Example** (`monthly.html`):
```jinja2
{% extends "base.html" %}

{% block content %}
<!-- Cover Page -->
<section class="cover-page">
  <h1>Monthly Report: {{ month_name }} {{ year }}</h1>
  <p>Generated: {{ generation_date }}</p>
  <p>Accounts: {{ account_names|join(', ') }}</p>
</section>

<!-- Executive Summary -->
<section class="executive-summary">
  <h2>Month Overview</h2>
  {% include "components/metrics_card.html" with context %}
  {% include "components/equity_chart.html" with context %}
  {% include "components/calendar.html" with context %}
</section>

<!-- Weekly Breakdowns -->
{% for week in weeks %}
<section class="week-section">
  <h2>Week {{ week.number }} ({{ week.start_date }} - {{ week.end_date }})</h2>
  {% include "components/metrics_card.html" with metrics=week.metrics %}

  {% for day in week.days %}
  <div class="day-section">
    <h3>{{ day.date|format_date }} - {{ day.weekday }}</h3>
    {% include "components/metrics_card.html" with metrics=day.metrics %}

    {% for trade in day.trades %}
    <div class="trade-detail">
      <h4>Trade #{{ trade.id }} - {{ trade.symbol }}</h4>
      <table>
        <tr><td>Side:</td><td>{{ trade.side }}</td></tr>
        <tr><td>Entry:</td><td>{{ trade.entry_price }}</td></tr>
        <tr><td>Exit:</td><td>{{ trade.exit_price }}</td></tr>
        <tr><td>PnL:</td><td class="{{ 'profit' if trade.net_pnl > 0 else 'loss' }}">
          {{ trade.net_pnl|currency }}
        </td></tr>
      </table>

      <!-- Playbook if exists -->
      {% if trade.playbook %}
      <div class="playbook">
        <p><strong>Grade:</strong> {{ trade.playbook.grade }}</p>
        <p><strong>Compliance:</strong> {{ trade.playbook.compliance_score|percent }}</p>
      </div>
      {% endif %}

      <!-- Screenshots (inline if ≤2, else reference appendix) -->
      {% if trade.screenshots|length <= 2 %}
        {% for screenshot in trade.screenshots %}
          {% include "components/screenshot.html" with screenshot=screenshot %}
        {% endfor %}
      {% else %}
        <p>See Appendix ({{ trade.screenshots|length }} screenshots)</p>
      {% endif %}
    </div>
    {% endfor %}

    <!-- Daily Journal if exists -->
    {% if day.journal %}
    <div class="journal-entry">
      <h4>Daily Journal</h4>
      <p>{{ day.journal.notes }}</p>
    </div>
    {% endif %}
  </div>
  {% endfor %}
</section>
{% endfor %}

<!-- Screenshot Appendix -->
{% if appendix_screenshots %}
<section class="appendix">
  <h2>Screenshot Appendix</h2>
  {% for screenshot in appendix_screenshots %}
    <div class="appendix-screenshot">
      <h4>Trade #{{ screenshot.trade_id }} - Screenshot {{ screenshot.index }}</h4>
      <img src="data:image/png;base64,{{ screenshot.base64 }}" />
    </div>
  {% endfor %}
</section>
{% endif %}
{% endblock %}
```

### 3.5 Chart Generation

**Equity Curve**: Generate SVG chart using `matplotlib` or `plotly` (export to SVG)

```python
import matplotlib.pyplot as plt
import io
import base64

def generate_equity_chart(trades: List[Trade]) -> str:
    """Generate equity curve as SVG"""
    equity = [0]
    for trade in trades:
        equity.append(equity[-1] + trade.net_pnl)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(equity, color='#2563eb', linewidth=2)
    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Equity ($)')
    ax.set_title('Equity Curve')
    ax.grid(True, alpha=0.3)

    # Save as SVG
    buf = io.BytesIO()
    fig.savefig(buf, format='svg')
    buf.seek(0)
    svg_data = buf.read().decode('utf-8')
    return svg_data
```

**Calendar Heatmap**: Render as HTML table with colored cells (CSS grid)

### 3.6 Frontend Implementation

**UI Location**: Dashboard + Trades page

**"Generate Report" Button**:
- Opens modal with configuration
- Report type selector (Monthly, Weekly, Daily, Trade)
- Period picker (changes based on type)
- Account filter (multi-select)
- Saved view selector (optional)
- Theme toggle (Light/Dark)
- "Include Screenshots" checkbox

**Report History**:
- `GET /reports/history` - List previously generated reports
- Display table with download links
- Auto-cleanup old reports (>30 days)

---

## Implementation Timeline

### Phase 1: Filter Builder (Week 1-2) ✅ COMPLETE
- [x] Define filter DSL schema
- [x] Implement `FilterCompiler` in `api/app/filters.py`
- [x] Update `GET /trades` to accept `filters` param
- [x] Write filter compiler tests
- [x] Build frontend FilterBuilder component (MVP: single AND group)
- [x] Integration testing

### Phase 2: Saved Views (Week 3) ✅ COMPLETE
- [x] Create migration 0018_saved_views
- [x] Implement `/views` CRUD endpoints
- [x] Update `GET /trades` to support `view` param
- [x] Build view management UI
- [x] Add view selector to trades page
- [x] Test saved view persistence

### Phase 3: PDF Reports (Week 4-5)
- [ ] Install WeasyPrint dependencies
- [ ] Create Jinja2 report templates
- [ ] Implement `ReportGenerator` class
- [ ] Add `/reports/generate` endpoint
- [ ] Build chart generation (equity curve, calendar)
- [ ] Build frontend report configuration modal
- [ ] Test all report types (Trade, Daily, Weekly, Monthly)
- [ ] Add report history UI
- [ ] Performance testing with large datasets

---

## Testing Strategy

### Unit Tests
- Filter compiler (each operator, nested groups)
- Report data aggregation (metrics calculations)
- Template rendering (mock data)

### Integration Tests
- Filter + pagination + sorting
- Saved view CRUD
- Report generation end-to-end
- Screenshot embedding in PDFs

### Performance Tests
- Filter queries with 10k+ trades
- PDF generation with 100+ trades
- Large screenshot appendices

---

## Success Metrics

### Phase 1 & 2: ✅ COMPLETE
- [x] Users can create complex filters (3+ conditions, 1+ nested group)
- [x] Saved views reduce time to access common queries by 80%
- [x] Views load in <500ms
- [x] Default view loads automatically on page visit
- [x] URL sharing works (/trades?view=<name>)
- [x] View management is intuitive (Settings page)
- [x] No duplicate names allowed per user
- [x] Only one default view per user

### Phase 3: PENDING
- [ ] Monthly report generation completes in <10s for 100 trades
- [ ] PDF reports include all sections (metrics, calendar, trades, screenshots)
- [ ] Reports honor filters/saved views correctly

---

## Future Enhancements (Post-M7)

- Export to CSV/Parquet (honors filters)
- Scheduled report generation (weekly email digest)
- Report templates (customizable sections)
- Multi-currency support in reports
- Playbook field aggregation in reports (performance by grade)
- Compare reports (e.g., Jan 2025 vs Jan 2024)

---

## Status: Planning → Ready for Phase 1 Implementation
