# M7 Phase 3: PDF Report Generation - Implementation Plan

**Status**: Planning
**Version**: 0.7.3
**Last Updated**: 2025-10-25

## Overview

Phase 3 adds comprehensive PDF report generation to Edge-Journal. Users can:
- Generate multi-granularity reports (Trade → Daily → Weekly → Monthly → Yearly → All-Time)
- Include metrics, equity curves, calendar heatmaps, and screenshots
- Apply saved views/filters to reports
- **Select specific accounts** (one, some, or all) to include in reports
- **Configure account separation** (combined, grouped, or separate sections)
- Choose light/dark themes
- Download or access report history

---

## Goals

1. **Multi-Granularity Reports**: Trade, Daily, Weekly, Monthly, Yearly, YTD, All-Time
2. **Hierarchical Breakdown**: Month → Weeks → Days → Trades with KPIs at each level
3. **Rich Content**: Metrics, charts, calendars, playbook data, journal entries, screenshots
4. **Honor Filters**: Apply saved views or custom filters to report data
5. **Account Selection**: Choose one, multiple, or all accounts to include
6. **Account Separation**: Configurable display modes for multi-account reports
7. **Professional Output**: Clean PDF with headers/footers, page breaks, themes

---

## Technology Stack

### PDF Generation: **WeasyPrint**
- Pure Python library (no Chromium dependency)
- Renders HTML+CSS to PDF
- Supports page breaks, headers/footers, SVG charts
- Easy deployment in Docker

**Dependencies to Add**:
```python
# Add to api/requirements.txt
weasyprint==60.1
matplotlib==3.8.2
pillow==10.1.0
```

### Template Engine: **Jinja2** (already installed)
- Already used in FastAPI
- Familiar template syntax
- Good performance

### Chart Generation: **matplotlib**
- Generate equity curves as SVG
- Embed inline in HTML
- Alternative: plotly for interactive features (future)

---

## Report Types & Structure

| Type | Scope | Hierarchy | Key Sections |
|------|-------|-----------|--------------|
| **Trade** | Single trade | Flat | Trade details, playbook, notes, screenshots |
| **Daily** | Single day | Day → Trades | Day KPIs, trade list, journal entry |
| **Weekly** | Single week | Week → Days → Trades | Week KPIs, daily breakdowns |
| **Monthly** | Single month | Month → Weeks → Days → Trades | Month KPIs, weekly/daily breakdowns, appendix |
| **Yearly** | Calendar year | Year → Months → Weeks | Year KPIs, monthly summaries |
| **YTD** | Year-to-date | Same as Yearly (incomplete) | Current year progress |
| **All-Time** | All data | Flat | Aggregate KPIs, top performers |

---

## Account Selection & Separation

Users can control which accounts appear in reports and how they're organized.

### Account Selection

**Options**:
- **All Accounts**: Include all user's trading accounts (default)
- **Specific Accounts**: Select one or more accounts via multi-select
- **Single Account**: Focus report on single account performance

**UI**: Multi-select dropdown in report generation modal

### Account Separation Modes

When multiple accounts are selected, users can choose how to display the data:

#### 1. **Combined** (Default)
- Aggregate all accounts together
- Single set of metrics (total P&L, combined win rate, etc.)
- Single equity curve showing combined performance
- Trades listed chronologically regardless of account
- Account name shown in each trade row
- **Use Case**: Overall portfolio performance view

**Example Structure**:
```
Monthly Report: January 2025
├─ Executive Summary (Combined Metrics)
│  ├─ Total P&L: $5,450 (Demo: $2,100 + Live: $3,350)
│  ├─ Combined Win Rate: 62%
│  ├─ Combined Equity Curve
│  └─ Calendar (all accounts merged)
├─ Week 1
│  ├─ Day 1
│  │  ├─ Trade 1 (Demo) - EURUSD +$100
│  │  ├─ Trade 2 (Live) - GBPUSD +$150
│  │  └─ Trade 3 (Demo) - USDJPY -$50
```

#### 2. **Grouped**
- Show combined metrics at top
- Separate sections per account below
- Each account gets its own breakdown with individual metrics
- Separate equity curves per account
- **Use Case**: Compare account performance side-by-side

**Example Structure**:
```
Monthly Report: January 2025
├─ Executive Summary (Combined Overview)
│  ├─ Total P&L: $5,450
│  ├─ Accounts: Demo ($2,100), Live ($3,350)
│
├─ Account: Demo
│  ├─ Account Metrics (Win Rate: 58%, P&L: $2,100)
│  ├─ Demo Equity Curve
│  ├─ Week 1 → Days → Trades
│  └─ Week 2 → Days → Trades
│
├─ Account: Live
│  ├─ Account Metrics (Win Rate: 65%, P&L: $3,350)
│  ├─ Live Equity Curve
│  ├─ Week 1 → Days → Trades
│  └─ Week 2 → Days → Trades
```

#### 3. **Separate**
- Generate separate report for each selected account
- Returns multiple PDFs (one per account)
- Each PDF is self-contained with full breakdown
- **Use Case**: Detailed analysis of individual accounts, separate record-keeping

**Example Output**:
```
report_monthly_2025-01_Demo.pdf
report_monthly_2025-01_Live.pdf
```

### Implementation Notes

- **Single Account**: Always uses "Combined" mode (no separation needed)
- **Multiple Accounts**: User selects separation mode
- **Default**: Combined mode (simplest, most common use case)
- **Grouped Mode**: Best for 2-5 accounts (readable)
- **Separate Mode**: Best for detailed analysis or regulatory requirements

---

## Backend Implementation

### Task 1: Install Dependencies

**File**: `api/requirements.txt`

Add:
```
weasyprint==60.1
matplotlib==3.8.2
pillow==10.1.0
```

**Dockerfile Update** (if needed):
```dockerfile
# Install WeasyPrint system dependencies
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
```

### Task 2: Create Report Generator Module

**File**: `api/app/reports.py` (NEW)

```python
"""
PDF Report Generation Module

Generates multi-granularity PDF reports from trade data using WeasyPrint.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import io
import base64

from .models import Trade, User, DailyJournal, PlaybookResponse, Attachment, SavedView
from .filters import FilterCompiler

class ReportGenerator:
    """Generate PDF reports from trade data"""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.jinja_env = Environment(
            loader=FileSystemLoader("api/templates/reports"),
            autoescape=True
        )
        # Add custom filters
        self.jinja_env.filters['currency'] = self._format_currency
        self.jinja_env.filters['percent'] = self._format_percent
        self.jinja_env.filters['format_date'] = self._format_date

    def generate_trade_report(
        self,
        trade_id: int,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> bytes:
        """Generate single trade report"""
        # Fetch trade with relationships
        # Render template
        # Convert to PDF
        pass

    def generate_daily_report(
        self,
        report_date: date,
        view_id: Optional[int] = None,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> bytes:
        """Generate daily report"""
        pass

    def generate_weekly_report(
        self,
        year: int,
        week: int,
        view_id: Optional[int] = None,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> bytes:
        """Generate weekly report"""
        pass

    def generate_monthly_report(
        self,
        year: int,
        month: int,
        account_ids: Optional[List[int]] = None,
        account_separation_mode: str = "combined",
        view_id: Optional[int] = None,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> bytes:
        """
        Generate monthly report with hierarchical breakdown.

        Args:
            year: Report year
            month: Report month (1-12)
            account_ids: List of account IDs to include (None = all accounts)
            account_separation_mode: How to display multiple accounts:
                - "combined": Merge all accounts together
                - "grouped": Show combined overview + per-account sections
                - "separate": Generate separate PDF per account (not implemented here)
            view_id: Optional saved view ID to apply filters
            theme: "light" or "dark"
            include_screenshots: Whether to include trade screenshots

        Structure:
        - Cover page
        - Executive summary (month KPIs, equity curve, calendar)
        - Week-by-week breakdown
        - Day-by-day breakdown within each week
        - Trade-by-trade details
        - Screenshot appendix (if >2 screenshots per trade)
        """
        # 1. Fetch data (filtered by accounts)
        trades = self._fetch_trades(year, month, account_ids, view_id)

        # 2. Calculate metrics based on separation mode
        if account_separation_mode == "combined":
            # Single combined metrics
            metrics = self._calculate_metrics(trades)
            weeks = self._group_by_weeks(trades, year, month)
            account_sections = None
        elif account_separation_mode == "grouped":
            # Combined + per-account sections
            metrics = self._calculate_metrics(trades)  # Combined overview
            account_sections = self._group_by_accounts(trades, year, month)
        else:
            # "separate" mode should be handled at router level
            raise ValueError("Separate mode should be handled at router level")

        # 3. Generate charts
        equity_chart_svg = self._generate_equity_chart(trades)
        calendar_html = self._generate_calendar(trades, year, month)

        # 4. Render template
        template = self.jinja_env.get_template("monthly.html")
        html_content = template.render(
            year=year,
            month=month,
            month_name=self._get_month_name(month),
            metrics=metrics,
            weeks=weeks,
            equity_chart_svg=equity_chart_svg,
            calendar_html=calendar_html,
            theme=theme,
            generation_date=datetime.utcnow().isoformat(),
            include_screenshots=include_screenshots
        )

        # 5. Convert to PDF
        css_file = f"api/templates/reports/styles/{theme}.css"
        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(filename=css_file)]
        )

        return pdf_bytes

    def generate_yearly_report(
        self,
        year: int,
        view_id: Optional[int] = None,
        theme: str = "light"
    ) -> bytes:
        """Generate yearly report"""
        pass

    def generate_ytd_report(
        self,
        view_id: Optional[int] = None,
        theme: str = "light"
    ) -> bytes:
        """Generate year-to-date report"""
        pass

    def generate_alltime_report(
        self,
        view_id: Optional[int] = None,
        theme: str = "light"
    ) -> bytes:
        """Generate all-time report"""
        pass

    # Helper methods
    def _fetch_trades(self, year: int, month: int, view_id: Optional[int]) -> List[Trade]:
        """Fetch trades for period, honoring view filters"""
        pass

    def _calculate_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """Calculate KPIs from trades"""
        # Total PnL, Win Rate, Expectancy, Max Drawdown, etc.
        pass

    def _group_by_weeks(self, trades: List[Trade], year: int, month: int) -> List[Dict]:
        """Group trades by calendar weeks"""
        pass

    def _generate_equity_chart(self, trades: List[Trade]) -> str:
        """Generate equity curve as SVG"""
        equity = [0]
        for trade in sorted(trades, key=lambda t: t.open_time_utc):
            equity.append(equity[-1] + (trade.net_pnl or 0))

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(equity, color='#2563eb', linewidth=2)
        ax.set_xlabel('Trade Number')
        ax.set_ylabel('Equity ($)')
        ax.set_title('Equity Curve')
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        fig.savefig(buf, format='svg')
        plt.close(fig)
        buf.seek(0)
        return buf.read().decode('utf-8')

    def _generate_calendar(self, trades: List[Trade], year: int, month: int) -> str:
        """Generate calendar heatmap as HTML table"""
        pass

    def _format_currency(self, value: float) -> str:
        """Format as currency"""
        return f"${value:,.2f}"

    def _format_percent(self, value: float) -> str:
        """Format as percentage"""
        return f"{value * 100:.1f}%"

    def _format_date(self, dt: datetime) -> str:
        """Format datetime"""
        return dt.strftime("%Y-%m-%d %H:%M")

    def _get_month_name(self, month: int) -> str:
        """Get month name"""
        return datetime(2000, month, 1).strftime("%B")
```

### Task 3: Create Pydantic Schemas

**File**: `api/app/schemas.py`

Add:
```python
from datetime import date

class ReportPeriod(BaseModel):
    """Period specification for reports"""
    year: Optional[int] = None
    month: Optional[int] = None
    week: Optional[int] = None
    date: Optional[str] = None  # YYYY-MM-DD
    trade_id: Optional[int] = None

class ReportGenerateRequest(BaseModel):
    """Request schema for report generation"""
    type: Literal["trade", "daily", "weekly", "monthly", "yearly", "ytd", "alltime"]
    period: ReportPeriod
    view_id: Optional[int] = None
    account_ids: Optional[List[int]] = None  # If None, includes all accounts
    account_separation_mode: Literal["combined", "grouped", "separate"] = "combined"
    theme: Literal["light", "dark"] = "light"
    include_screenshots: bool = True

class ReportHistoryItem(BaseModel):
    """Report history item"""
    id: int
    filename: str
    report_type: str
    created_at: datetime
    file_size: int

    model_config = ConfigDict(from_attributes=True)
```

### Task 4: Create Reports Router

**File**: `api/app/routes_reports.py` (NEW)

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os

from .db import get_db
from .deps import get_current_user
from .models import User
from .schemas import ReportGenerateRequest, ReportHistoryItem
from .reports import ReportGenerator

router = APIRouter(prefix="/reports", tags=["reports"])

REPORTS_BASE_DIR = "/data/exports"

@router.post("/generate")
def generate_report(
    body: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
) -> FileResponse:
    """
    Generate PDF report and return as download.

    Supports multiple report types: trade, daily, weekly, monthly, yearly, ytd, alltime
    """
    generator = ReportGenerator(db, current.id)

    # Generate PDF based on type
    try:
        if body.type == "trade":
            if not body.period.trade_id:
                raise HTTPException(400, detail="trade_id required for trade report")
            pdf_bytes = generator.generate_trade_report(
                body.period.trade_id,
                body.theme,
                body.include_screenshots
            )
        elif body.type == "daily":
            if not body.period.date:
                raise HTTPException(400, detail="date required for daily report")
            pdf_bytes = generator.generate_daily_report(
                body.period.date,
                body.view_id,
                body.theme,
                body.include_screenshots
            )
        elif body.type == "monthly":
            if not body.period.year or not body.period.month:
                raise HTTPException(400, detail="year and month required for monthly report")
            pdf_bytes = generator.generate_monthly_report(
                body.period.year,
                body.period.month,
                body.view_id,
                body.theme,
                body.include_screenshots
            )
        # ... other types
        else:
            raise HTTPException(400, detail=f"Unsupported report type: {body.type}")

    except Exception as e:
        raise HTTPException(500, detail=f"Report generation failed: {str(e)}")

    # Save to disk
    user_reports_dir = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports")
    os.makedirs(user_reports_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{body.type}_{timestamp}.pdf"
    filepath = os.path.join(user_reports_dir, filename)

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/history")
def list_report_history(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
) -> List[ReportHistoryItem]:
    """List previously generated reports"""
    user_reports_dir = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports")

    if not os.path.exists(user_reports_dir):
        return []

    reports = []
    for filename in os.listdir(user_reports_dir):
        if filename.endswith(".pdf"):
            filepath = os.path.join(user_reports_dir, filename)
            stat = os.stat(filepath)
            reports.append({
                "id": hash(filename),
                "filename": filename,
                "report_type": filename.split("_")[1] if "_" in filename else "unknown",
                "created_at": datetime.fromtimestamp(stat.st_mtime),
                "file_size": stat.st_size
            })

    return sorted(reports, key=lambda r: r["created_at"], reverse=True)


@router.get("/download/{filename}")
def download_report(
    filename: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
) -> FileResponse:
    """Download previously generated report"""
    # Security: ensure filename doesn't escape directory
    if ".." in filename or "/" in filename:
        raise HTTPException(400, detail="Invalid filename")

    filepath = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports", filename)

    if not os.path.exists(filepath):
        raise HTTPException(404, detail="Report not found")

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/pdf"
    )


@router.delete("/{filename}")
def delete_report(
    filename: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Delete report from history"""
    if ".." in filename or "/" in filename:
        raise HTTPException(400, detail="Invalid filename")

    filepath = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports", filename)

    if not os.path.exists(filepath):
        raise HTTPException(404, detail="Report not found")

    os.remove(filepath)
    return {"message": "Report deleted successfully"}
```

### Task 5: Create Jinja2 Templates

**Directory Structure**:
```
api/templates/reports/
├── base.html              # Base layout with header/footer
├── monthly.html           # Monthly report
├── weekly.html            # Weekly report
├── daily.html             # Daily report
├── trade.html             # Single trade
├── components/
│   ├── metrics_card.html  # KPI display
│   ├── trade_table.html   # Trade list table
│   └── screenshot.html    # Screenshot embed
└── styles/
    ├── light.css          # Light theme
    └── dark.css           # Dark theme
```

**File**: `api/templates/reports/base.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "{{ title }}";
                font-size: 10pt;
                color: #666;
            }
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
    </style>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

**File**: `api/templates/reports/monthly.html`

```html
{% extends "base.html" %}

{% block content %}
<!-- Cover Page -->
<div class="cover-page">
    <h1>Monthly Trading Report</h1>
    <h2>{{ month_name }} {{ year }}</h2>
    <p class="generated">Generated: {{ generation_date }}</p>
</div>

<!-- Executive Summary -->
<div class="executive-summary page-break">
    <h2>Month Overview</h2>
    {% include "components/metrics_card.html" %}

    <div class="equity-chart">
        <h3>Equity Curve</h3>
        {{ equity_chart_svg | safe }}
    </div>

    <div class="calendar">
        <h3>Trading Calendar</h3>
        {{ calendar_html | safe }}
    </div>
</div>

<!-- Weekly Breakdowns -->
{% for week in weeks %}
<div class="week-section page-break">
    <h2>Week {{ week.number }} ({{ week.start_date }} - {{ week.end_date }})</h2>
    {% include "components/metrics_card.html" with {"metrics": week.metrics} %}

    {% for day in week.days %}
    <div class="day-section">
        <h3>{{ day.date | format_date }} - {{ day.weekday }}</h3>

        {% if day.trades %}
        {% include "components/trade_table.html" with {"trades": day.trades} %}
        {% else %}
        <p class="no-trades">No trades on this day</p>
        {% endif %}

        {% if day.journal %}
        <div class="journal-entry">
            <h4>Daily Journal</h4>
            <p>{{ day.journal.notes }}</p>
        </div>
        {% endif %}
    </div>
    {% endfor %}
</div>
{% endfor %}

<!-- Screenshot Appendix -->
{% if appendix_screenshots %}
<div class="appendix page-break">
    <h2>Screenshot Appendix</h2>
    {% for screenshot in appendix_screenshots %}
    <div class="screenshot-entry">
        <h4>Trade #{{ screenshot.trade_id }} - Screenshot {{ screenshot.index }}</h4>
        {% include "components/screenshot.html" with {"screenshot": screenshot} %}
    </div>
    {% endfor %}
</div>
{% endif %}
{% endblock %}
```

**File**: `api/templates/reports/styles/light.css`

```css
body {
    font-family: Arial, sans-serif;
    color: #333;
    background: white;
    line-height: 1.6;
}

h1, h2, h3, h4 {
    color: #2c3e50;
    margin-top: 1em;
}

.cover-page {
    text-align: center;
    padding: 4cm 0;
}

.cover-page h1 {
    font-size: 36pt;
    margin-bottom: 0.5em;
}

.cover-page h2 {
    font-size: 24pt;
    color: #3498db;
}

.page-break {
    page-break-before: always;
}

.metrics-card {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1cm;
    margin: 1cm 0;
}

.metric {
    text-align: center;
    padding: 0.5cm;
    border: 1px solid #ddd;
    border-radius: 4px;
}

.metric-label {
    font-size: 10pt;
    color: #666;
    text-transform: uppercase;
}

.metric-value {
    font-size: 18pt;
    font-weight: bold;
    margin-top: 0.5em;
}

.metric-value.positive {
    color: #27ae60;
}

.metric-value.negative {
    color: #e74c3c;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}

th, td {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

th {
    background-color: #f8f9fa;
    font-weight: bold;
}

.trade-profit {
    color: #27ae60;
}

.trade-loss {
    color: #e74c3c;
}
```

### Task 6: Update Main App

**File**: `api/app/main.py`

Add:
```python
from .routes_reports import router as reports_router

app.include_router(reports_router)
```

### Task 7: Create Tests

**File**: `api/tests/test_reports.py` (NEW)

```python
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def register_and_login():
    email = f"reporttest_{hash(str(__file__))}@example.com"
    pwd = "TestPwd123!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    r = client.post("/auth/login", data={"username": email, "password": pwd})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_generate_monthly_report():
    """Test generating a monthly report"""
    auth = register_and_login()

    # Create some trades first (via CSV upload or manual creation)
    # ...

    payload = {
        "type": "monthly",
        "period": {
            "year": 2025,
            "month": 1
        },
        "theme": "light",
        "include_screenshots": False
    }

    r = client.post("/reports/generate", json=payload, headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"

def test_list_report_history():
    """Test listing report history"""
    auth = register_and_login()

    # Generate a report first
    # ...

    r = client.get("/reports/history", headers=auth)
    assert r.status_code == 200
    reports = r.json()
    assert isinstance(reports, list)

def test_report_with_saved_view():
    """Test generating report with saved view filter"""
    auth = register_and_login()

    # Create saved view
    view_payload = {
        "name": "Test View",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }
    r = client.post("/views", json=view_payload, headers=auth)
    view_id = r.json()["id"]

    # Generate report with view
    payload = {
        "type": "monthly",
        "period": {"year": 2025, "month": 1},
        "view_id": view_id
    }

    r = client.post("/reports/generate", json=payload, headers=auth)
    assert r.status_code == 200
```

---

## Frontend Implementation

### Task 8: Create Report Modal Component

**File**: `web/app/components/reports/ReportGenerateModal.tsx` (NEW)

```tsx
"use client";

import { useState } from "react";

interface ReportGenerateModalProps {
  onGenerate: (config: ReportConfig) => void;
  onClose: () => void;
}

interface ReportConfig {
  type: string;
  period: any;
  viewId?: number;
  theme: string;
  includeScreenshots: boolean;
}

export default function ReportGenerateModal({ onGenerate, onClose }: ReportGenerateModalProps) {
  const [type, setType] = useState("monthly");
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [theme, setTheme] = useState("light");
  const [includeScreenshots, setIncludeScreenshots] = useState(true);
  const [selectedAccounts, setSelectedAccounts] = useState<number[]>([]);  // Empty = all accounts
  const [accountSeparationMode, setAccountSeparationMode] = useState("combined");
  const [accounts, setAccounts] = useState<Array<{id: number, name: string}>>([]);

  // Load user's accounts on mount
  useEffect(() => {
    async function loadAccounts() {
      const token = localStorage.getItem("ej_token");
      if (!token) return;
      const r = await fetch(`${API_BASE}/accounts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (r.ok) {
        const data = await r.json();
        setAccounts(data);
      }
    }
    loadAccounts();
  }, []);

  const handleAccountToggle = (accountId: number) => {
    setSelectedAccounts(prev =>
      prev.includes(accountId)
        ? prev.filter(id => id !== accountId)
        : [...prev, accountId]
    );
  };

  const handleGenerate = () => {
    const period: any = {};
    if (type === "monthly") {
      period.year = year;
      period.month = month;
    }
    // ... other types

    onGenerate({
      type,
      period,
      accountIds: selectedAccounts.length > 0 ? selectedAccounts : undefined,  // undefined = all
      accountSeparationMode,
      theme,
      includeScreenshots
    });
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Generate Report</h2>

        <div className="form-group">
          <label>Report Type</label>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="trade">Single Trade</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
            <option value="ytd">Year-to-Date</option>
            <option value="alltime">All-Time</option>
          </select>
        </div>

        {type === "monthly" && (
          <>
            <div className="form-group">
              <label>Year</label>
              <input type="number" value={year} onChange={(e) => setYear(parseInt(e.target.value))} />
            </div>
            <div className="form-group">
              <label>Month</label>
              <select value={month} onChange={(e) => setMonth(parseInt(e.target.value))}>
                {Array.from({length: 12}, (_, i) => (
                  <option key={i+1} value={i+1}>{new Date(2000, i).toLocaleString('default', {month: 'long'})}</option>
                ))}
              </select>
            </div>
          </>
        )}

        <div className="form-group">
          <label>Accounts (leave empty for all)</label>
          <div style={{ maxHeight: "150px", overflowY: "auto", border: "1px solid #ccc", padding: "8px" }}>
            {accounts.map(account => (
              <label key={account.id} style={{ display: "block", marginBottom: "4px" }}>
                <input
                  type="checkbox"
                  checked={selectedAccounts.includes(account.id)}
                  onChange={() => handleAccountToggle(account.id)}
                />
                {account.name}
              </label>
            ))}
          </div>
          <small style={{ color: "#666" }}>
            {selectedAccounts.length === 0 ? "All accounts selected" : `${selectedAccounts.length} account(s) selected`}
          </small>
        </div>

        {selectedAccounts.length > 1 && (
          <div className="form-group">
            <label>Account Separation</label>
            <select value={accountSeparationMode} onChange={(e) => setAccountSeparationMode(e.target.value)}>
              <option value="combined">Combined (merge all together)</option>
              <option value="grouped">Grouped (combined + per-account sections)</option>
              <option value="separate">Separate (individual PDFs per account)</option>
            </select>
            <small style={{ color: "#666", display: "block", marginTop: "4px" }}>
              {accountSeparationMode === "combined" && "All accounts merged into single overview"}
              {accountSeparationMode === "grouped" && "Combined metrics + breakdown per account"}
              {accountSeparationMode === "separate" && "Generate separate PDF for each account"}
            </small>
          </div>
        )}

        <div className="form-group">
          <label>Theme</label>
          <select value={theme} onChange={(e) => setTheme(e.target.value)}>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>

        <div className="form-group">
          <label>
            <input type="checkbox" checked={includeScreenshots} onChange={(e) => setIncludeScreenshots(e.target.checked)} />
            Include Screenshots
          </label>
        </div>

        <div className="button-group">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleGenerate} className="primary">Generate PDF</button>
        </div>
      </div>
    </div>
  );
}
```

### Task 9: Add Report Button to Dashboard/Trades

**File**: `web/app/dashboard/page.tsx` (or trades page)

Add "Generate Report" button that opens ReportGenerateModal.

### Task 10: Report History Page

**File**: `web/app/reports/page.tsx` (NEW)

List previously generated reports with download links.

---

## Implementation Timeline

### Week 1: Backend Foundation
- **Day 1**: Install WeasyPrint, create ReportGenerator module skeleton
- **Day 2**: Implement monthly report generation (metrics calculation, data fetching)
- **Day 3**: Create Jinja2 templates (base, monthly, components)
- **Day 4**: Implement chart generation (equity curve, calendar heatmap)
- **Day 5**: Create reports router, test manually

### Week 2: Complete All Report Types
- **Day 1**: Implement daily and weekly reports
- **Day 2**: Implement yearly, YTD, all-time reports
- **Day 3**: Implement trade report (single trade detail)
- **Day 4**: Add report history endpoint
- **Day 5**: Write comprehensive backend tests

### Week 3: Frontend Integration
- **Day 1**: Create ReportGenerateModal component
- **Day 2**: Integrate modal with dashboard/trades page
- **Day 3**: Create report history page
- **Day 4**: Add loading states, error handling
- **Day 5**: End-to-end testing, polish UI

**Total Estimate**: 2-3 weeks

---

## Testing Checklist

### Backend Tests
- [ ] Monthly report generation (with/without filters)
- [ ] Weekly report generation
- [ ] Daily report generation
- [ ] Trade report generation
- [ ] Report honors saved view filters
- [ ] Report honors account filters
- [ ] Equity chart generation
- [ ] Calendar heatmap generation
- [ ] Report history listing
- [ ] Report download
- [ ] Report deletion

### Frontend Tests
- [ ] Modal opens and closes
- [ ] Period selection works for each type
- [ ] Theme selection works
- [ ] Screenshot toggle works
- [ ] Generate button triggers download
- [ ] Report history displays correctly
- [ ] Download from history works

### Performance Tests
- [ ] Monthly report with 100 trades < 10s
- [ ] Report with 50 screenshots < 15s
- [ ] Large equity chart (1000+ trades) renders

---

## Success Metrics

- [ ] Monthly report generation completes in <10s for 100 trades
- [ ] PDF reports include all sections (metrics, calendar, trades, screenshots)
- [ ] Reports honor filters/saved views correctly
- [ ] Generated PDFs are professional and readable
- [ ] Users can access report history and re-download

---

## Future Enhancements (Post-Phase 3)

- Scheduled report generation (weekly email digest)
- Report templates (customizable sections)
- Multi-currency support in reports
- Playbook field aggregation (performance by grade)
- Compare reports (Jan 2025 vs Jan 2024)
- Export to CSV/Excel in addition to PDF
- Interactive charts (plotly) with drill-down

---

## Dependencies

**Python Packages**:
- weasyprint==60.1
- matplotlib==3.8.2
- pillow==10.1.0

**System Libraries** (Dockerfile):
- libpango-1.0-0
- libpangocairo-1.0-0
- libgdk-pixbuf2.0-0
- libffi-dev
- shared-mime-info

---

## Notes

- WeasyPrint renders on the server (no browser needed)
- Reports are saved to `/data/exports/{user_id}/reports/`
- Auto-cleanup of old reports can be added as background task
- Large reports (>100 trades with screenshots) may take 10-15s
- Consider background jobs for large reports (Celery) in future

---

## Status: Ready for Implementation

All prerequisites complete (Phases 1 & 2). Ready to begin Phase 3 implementation.
