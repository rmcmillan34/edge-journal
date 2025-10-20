# Modular Journaling Templates — Feature Spec (Extended)

**Last updated:** 20 Oct 2025  
**Owner:** Trading Journal Team  
**Status:** Draft (Ready for implementation)

---

## 1) Overview
This document specifies a **modular, drag‑and‑drop templating system** for the trading journal app. Users can compose entries (Daily Market Analysis, Trade Review, Weekly Reflection, etc.) from reusable **blocks** (aka *sections/cards*). Templates are **data‑driven** and **versioned**, enabling export/import as JSON.

### Goals
- Flexible, re-usable blocks for different journal entry types.
- Drag-and-drop UI to compose templates and to reorder blocks within an entry.
- Schema-driven rendering so the frontend stays decoupled from content.
- Fast authoring with checklists, ratings, text areas, tags, screenshots, and computed stats.
- Safe migrations via versioned schemas and per-template versions.

### Non-Goals
- WYSIWYG rich text editing beyond simple markdown (phase 2).
- Real-time collaborative editing (phase 2+).

---

## 15) Structured Data Capture & Render-to-Markdown/PDF
To power robust analytics, journal inputs must be stored as **structured fields** (not only free text). Blocks can expose **form fields** that bind to typed values, while still supporting markdown/PDF rendering for human-friendly output.

### 15.1 Block Form Fields
Extend the block schema with a `fields` array describing typed inputs. Each field is addressable via `blockId.fieldKey` for analytics and computed formulas.

```json
{
  "id": "b-meta",
  "type": "key_value",
  "title": "Trade Metadata",
  "fields": [
    { "key": "symbol", "label": "Symbol", "type": "string", "required": true },
    { "key": "risk_pct", "label": "Risk %", "type": "number", "min": 0, "max": 5, "unit": "%" },
    { "key": "planned_rr", "label": "Planned R:R", "type": "number", "min": 0.1 },
    { "key": "session", "label": "Session", "type": "enum", "options": ["Asia","London","New York"] },
    { "key": "entry_time", "label": "Entry Time", "type": "datetime" }
  ]
}
```

> Rendering: the UI shows inputs according to `type` and `options`, while markdown/PDF renderers use the same values to print a clean table or sentence-form summary.

### 15.2 Validation & Computed Fields
- **Validation** per field (required, min/max, regex).
- **Computed** values via the existing `metric` block or `fields[i].formula` (read-only in UI). Example: `r_multiple`, `position_size` given balance, risk % and stop distance.

```json
{ "key": "r_multiple", "label": "R Multiple", "type": "number", "readonly": true, "formula": "(exit - entry) / (entry - stop)" }
```

### 15.3 Content Model (Entries)
Each saved entry persists both the **template snapshot** and a flat map of **field values** for analytics.

```json
{
  "entryId": "uuid",
  "templateId": "uuid",
  "templateVersion": 1,
  "entryType": "trade_analysis",
  "values": {
    "b-meta.symbol": "GBPUSD",
    "b-meta.risk_pct": 0.5,
    "b-meta.session": "London",
    "b-price.entry": 1.2712,
    "b-price.stop": 1.2697,
    "b-price.exit": 1.2752,
    "b-metrics.r_multiple": 2.67
  }
}
```

---

## 16) Database Schema for Analytics
A **hybrid** model: keep the full JSON for fidelity, and maintain **normalized, queryable fields** for stats.

### 16.1 Core Tables (DDL sketch)
```sql
CREATE TABLE templates (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  entry_type TEXT NOT NULL,
  version INT NOT NULL,
  schema_version TEXT NOT NULL,
  blocks JSONB NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entries (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  template_id UUID NOT NULL,
  template_version INT NOT NULL,
  entry_type TEXT NOT NULL,
  content JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entry_fields (
  entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  field_key TEXT NOT NULL,
  field_type TEXT NOT NULL,
  string_val TEXT,
  number_val DOUBLE PRECISION,
  bool_val BOOLEAN,
  datetime_val TIMESTAMPTZ,
  enum_val TEXT,
  PRIMARY KEY (entry_id, field_key)
);

CREATE TABLE entry_metrics (
  entry_id UUID PRIMARY KEY REFERENCES entries(id) ON DELETE CASCADE,
  r_multiple DOUBLE PRECISION,
  expectancy DOUBLE PRECISION,
  drawdown DOUBLE PRECISION,
  pnl NUMERIC,
  tags TEXT[]
);

CREATE TABLE dim_date (
  d DATE PRIMARY KEY,
  y INT, q INT, m INT, dow INT
);

CREATE TABLE fact_trades (
  entry_id UUID PRIMARY KEY REFERENCES entries(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  d DATE NOT NULL REFERENCES dim_date(d),
  symbol TEXT NOT NULL,
  session TEXT,
  risk_pct DOUBLE PRECISION,
  r_multiple DOUBLE PRECISION,
  pnl NUMERIC,
  strategy TEXT,
  setup TEXT
);
```

### 16.2 Indexing
```sql
CREATE INDEX ON entry_fields(field_key);
CREATE INDEX ON entry_fields(number_val);
CREATE INDEX ON fact_trades(symbol);
CREATE INDEX ON fact_trades(d);
CREATE INDEX ON fact_trades(session);
```

---

## 17) Rendering Pipeline (Markdown → PDF)
1. **Load entry** by `id` including `content` and `values`.
2. **Render blocks** to markdown using block renderers.
3. **Assemble document** with a front-matter header.
4. **Export**:
   - Markdown download as `.md`
   - PDF via Chromium/wkhtmltopdf.

---

## 18) Example Queries & KPIs
### Win Rate and Avg R by Session
```sql
SELECT session,
       AVG(CASE WHEN r_multiple > 0 THEN 1 ELSE 0 END)::float AS win_rate,
       AVG(r_multiple) AS avg_r
FROM fact_trades
WHERE user_id = $1
GROUP BY session;
```

### Expectancy by Symbol
```sql
SELECT symbol,
       AVG(CASE WHEN r_multiple > 0 THEN r_multiple ELSE 0 END) * win_rate
         - ABS(AVG(CASE WHEN r_multiple <= 0 THEN r_multiple ELSE 0 END)) * (1 - win_rate) AS expectancy
FROM (
  SELECT symbol,
         r_multiple,
         AVG(CASE WHEN r_multiple > 0 THEN 1 ELSE 0 END) OVER (PARTITION BY symbol) AS win_rate
  FROM fact_trades
  WHERE user_id = $1 AND d >= CURRENT_DATE - INTERVAL '90 days'
) t
GROUP BY symbol;
```

### Rule Adherence
```sql
SELECT e.id AS entry_id,
       AVG(CASE WHEN f.field_key LIKE 'b-premarket.%' AND f.bool_val IS NOT NULL THEN (f.bool_val::int) END) AS adherence
FROM entries e
JOIN entry_fields f ON f.entry_id = e.id
WHERE e.user_id = $1 AND e.entry_type = 'daily_journal'
GROUP BY e.id;
```

---

## 19) Backward Compatibility & Migrations
- `fields` array optional.
- Analytics worker ignores untyped entries.
- Template upgrader tool maps text → fields.

---

## 20) Privacy & Export
- Analytics are local to user.
- Export raw entries, flattened fields, derived metrics as CSV/JSON.
- PDF exports include template/version footer.

---
