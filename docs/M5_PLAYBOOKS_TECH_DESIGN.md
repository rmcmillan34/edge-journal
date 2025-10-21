# Milestone 5 — Playbooks v1: Technical Design & Migrations Outline

Status: Proposal (for review)
Owner: Edge-Journal
Updated: 21 Oct 2025

## 1) Overview
Playbooks v1 introduces schema-driven, versioned checklists/forms that attach to trades and can be used as an instrument checklist inside the Daily Journal. Users configure required rules, weights, and max risk. The system computes compliance and a grade (A/B/C/D), displays a risk cap, and supports field-level evidence links (trade/journal attachments or URLs). Calendar badges highlight rule breaches. Enforcement of caps/guardrails is deferred to M6.

## 2) Goals & Non-goals
- Goals:
  - Versioned playbook templates with basic field types (boolean, select, number, text, rating, rich-text) and validation.
  - Responses attached to a trade or a daily instrument checklist record.
  - Per-field comments and evidence (attachments/URLs), reusable across criteria.
  - Compute compliance score and grade; derive risk cap from template grade schedule and template/account caps.
  - Filters/grouping by playbook fields; calendar badges for rule breaches.
  - First-run prompt to configure trading rules and default caps.
- Non-goals:
  - Repeatable sections, computed formulas, PDF/report sections, and strict enforcement of risk caps (M6).

## 3) Architecture Summary
The API is FastAPI + SQLAlchemy + Alembic. We add playbook tables, user trading rules, evidence links, optional breach audit, and extend accounts. We expose new routers for templates/responses/settings and extend metrics calendar to include breaches. The web app (Next.js/app router) gains pages for Playbooks, in-place forms on Trades, and an instrument checklist mode in Daily Journal.

## 4) Data Model & Migrations

### 4.1 New Tables
1) playbook_templates
   - id INT PK
   - user_id INT (FK users.id, index)
   - name VARCHAR(128) NOT NULL
   - purpose VARCHAR(16) NOT NULL CHECK in ('pre','in','post','generic')
   - strategy_bindings_json TEXT NULL (JSON array of strategy strings)
   - schema_json TEXT NOT NULL (JSON: [{ key, label, type, required?, weight?, allow_comment?, validation?, rich_text? }])
   - version INT NOT NULL DEFAULT 1
   - is_active BOOL NOT NULL DEFAULT true
   - grade_scale VARCHAR(16) NOT NULL DEFAULT 'A_B_C_D'
   - grade_thresholds_json TEXT NULL (JSON: {"A":0.9,"B":0.75,"C":0.6})
   - risk_schedule_json TEXT NULL (JSON: {"A":1.0,"B":0.5,"C":0.25,"D":0})
   - template_max_risk_pct NUMERIC(5,2) NULL
   - created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   - UNIQUE(user_id, name, version)

2) playbook_responses
   - id INT PK
   - user_id INT NOT NULL INDEX
   - trade_id INT NULL FK trades.id ON DELETE CASCADE (null for daily instrument checklist)
   - journal_id INT NULL FK daily_journal.id ON DELETE CASCADE (for instrument checklist)
   - template_id INT NOT NULL FK playbook_templates.id
   - template_version INT NOT NULL
   - entry_type VARCHAR(32) NOT NULL CHECK in ('trade_playbook','instrument_checklist')
   - values_json TEXT NOT NULL (flat key→value map; types reflected in schema)
   - comments_json TEXT NULL (per field key optional comment/rich-text)
   - computed_grade CHAR(1) NULL
   - compliance_score NUMERIC(5,2) NULL
   - intended_risk_pct NUMERIC(5,2) NULL  -- optional, can be captured via playbook field too
   - created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   - INDEX(template_id, template_version)
   - INDEX(trade_id)

3) playbook_evidence_links
   - id INT PK
   - response_id INT NOT NULL FK playbook_responses.id ON DELETE CASCADE
   - field_key VARCHAR(128) NOT NULL
   - source_kind VARCHAR(16) NOT NULL CHECK in ('trade','journal','url')
   - source_id INT NULL  -- attachment id when trade/journal
   - url TEXT NULL       -- for URL evidence
   - note TEXT NULL
   - created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   - INDEX(response_id)

4) user_trading_rules
   - id INT PK
   - user_id INT UNIQUE NOT NULL
   - max_losses_row_day INT NOT NULL DEFAULT 3
   - max_losing_days_streak_week INT NOT NULL DEFAULT 2
   - max_losing_weeks_streak_month INT NOT NULL DEFAULT 2
   - alerts_enabled BOOL NOT NULL DEFAULT true
   - created_at TIMESTAMPTZ NOT NULL DEFAULT now()

5) breach_events (optional v1, recommended)
   - id INT PK
   - user_id INT NOT NULL
   - account_id INT NULL FK accounts.id
   - scope VARCHAR(16) NOT NULL CHECK in ('day','week','month','trade')
   - date_or_week VARCHAR(16) NOT NULL  -- e.g., '2025-10-21' or '2025-W43'
   - rule_key VARCHAR(48) NOT NULL  -- e.g., 'loss_streak_day','losing_days_week','losing_weeks_month','risk_cap_exceeded'
   - details_json TEXT NULL
   - created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   - INDEX(user_id, date_or_week)

### 4.2 Table Extensions
- accounts: add `account_max_risk_pct NUMERIC(5,2) NULL`

### 4.3 Alembic Outline
- Revision 1: create playbook_templates, playbook_responses, playbook_evidence_links
- Revision 2: create user_trading_rules, breach_events (optional)
- Revision 3: alter accounts add column account_max_risk_pct

Note: Use server_default and indices as above; ensure downgrade drops indices then tables/columns.

## 5) ORM Models (SQLAlchemy)
- Add classes: PlaybookTemplate, PlaybookResponse, PlaybookEvidenceLink, UserTradingRules, BreachEvent
- Extend Account model with `account_max_risk_pct`
- Ensure `__table_args__` for unique constraints and indexes.

## 6) API Design (FastAPI)

### 6.1 Routers
- routes_playbooks.py
  - GET /playbooks/templates?purpose=&active=
  - POST /playbooks/templates
  - PATCH /playbooks/templates/{id}
  - POST /playbooks/templates/{id}/export
  - POST /playbooks/templates/import
  - POST /playbooks/evaluate

- routes_playbook_responses.py
  - GET /trades/{trade_id}/playbook-responses
  - POST /trades/{trade_id}/playbook-responses (upsert for a template)
  - GET /journal/{journal_id}/instrument/{symbol}/playbook-response (optional; or by date route)
  - POST /journal/{journal_id}/instrument/{symbol}/playbook-response
  - PATCH /playbook-responses/{id}
  - Evidence subroutes:
    - POST /playbook-responses/{id}/evidence
    - DELETE /playbook-responses/{id}/evidence/{evidence_id}

- routes_settings.py
  - GET /settings/trading-rules
  - PUT /settings/trading-rules

- routes_metrics.py
  - Extend GET /metrics/calendar to include `breaches: string[]` per day; badge keys among:
    - loss_streak_day, losing_days_week, losing_weeks_month, risk_cap_exceeded

### 6.2 Schemas (Pydantic v2)
- Playbook fields
  - PlaybookField: { key: str, label: str, type: 'boolean'|'select'|'number'|'text'|'rating'|'rich_text', required?: bool, weight?: float, allow_comment?: bool, validation?: { min?, max?, regex?, options?[] }, rich_text?: bool }
  - PlaybookTemplateCreate: name, purpose, strategy_bindings?: str[], schema: PlaybookField[], grade_thresholds?: dict, risk_schedule?: dict, template_max_risk_pct?: float
  - PlaybookTemplateOut: id, version, is_active, created_at, ...
  - PlaybookTemplateUpdate: name?, purpose?, strategy_bindings?, schema?, grade_thresholds?, risk_schedule?, template_max_risk_pct?

- Responses
  - PlaybookResponseCreate: template_id, template_version?, values: dict[str, Any], comments?: dict[str, str], intended_risk_pct?: float
  - PlaybookResponseOut: id, template_id, template_version, values, comments, computed_grade?, compliance_score?, intended_risk_pct?, created_at
  - EvidenceCreate: { field_key: str, source_kind: 'trade'|'journal'|'url', source_id?: int, url?: str, note?: str }
  - EvidenceOut: id, field_key, source_kind, source_id?, url?, note?

- Settings
  - TradingRules: { max_losses_row_day: int, max_losing_days_streak_week: int, max_losing_weeks_streak_month: int, alerts_enabled: bool }

- Evaluate
  - PlaybookEvaluateIn: { template_id?: int, schema?: PlaybookField[], values: dict[str, Any], grade_thresholds?: dict, risk_schedule?: dict, template_max_risk_pct?: float, account_max_risk_pct?: float }
  - PlaybookEvaluateOut: { compliance_score: float, grade: 'A'|'B'|'C'|'D', risk_cap_pct: float, cap_breakdown: { template?: float, grade?: float, account?: float } }

### 6.3 Validation & Evaluation Logic
- Validation: server validates `values` against schema: required, type, select options, min/max.
- Compliance score: sum(weights of satisfied fields) / sum(weights of configured fields considered). Default weight = 1.0. Boolean considered satisfied when true; select/number/text/rich-text considered satisfied if present and passes validation.
- Grade: thresholds mapping (default {A:0.9,B:0.75,C:0.6}).
- Risk cap: min(template_max_risk_pct, risk_schedule[grade], account_max_risk_pct if provided). If intended_risk_pct present and > min cap, include `risk_cap_exceeded` in evaluation result.

## 7) Metrics & Calendar Badges
- Add a lightweight rules evaluator used by calendar service:
  - Day loss streak: within a day (tz-adjusted to user), order trades by close_time_utc and count consecutive net_pnl < 0. If max streak > threshold: return badge.
  - Weekly losing-day streak: ISO week; count consecutive days with daily_net_pnl < 0; if exceeded: badge each day in the streak.
  - Monthly losing-week streak: calendar month; compute weekly sums; count consecutive weeks with sum < 0; badge each day belonging to those losing weeks.
  - Risk cap exceeded: if any trade’s intended_risk_pct > min cap (considering its playbook grade and caps) then badge that trade’s close date.
- Response shape: calendar API returns days: [{ date, trades, net_pnl, breaches: string[] }]. Tooltips list friendly labels for each breach and brief reasons.

## 8) Web App (Next.js) Changes
- New page `/playbooks`: CRUD builder for templates; configure fields, required, weights, grade thresholds, risk schedule, template_max_risk_pct; export/import JSON.
- Trades detail `/trades/[id]`: add Playbook panel: select template (auto-suggest by strategy), render fields, per-field comment editor (rich-text ok), evidence picker (trade/journal attachments, URLs), show computed grade and risk cap; warning chip if exceeded.
- Daily instrument checklist `/journal/[date]?symbol=...`: render playbook checklist form; include final `trade_entered` checkbox; evidence links to journal attachments/URLs; on saving a trade with same date+symbol, show prompt to link.
- First-run modal (Dashboard/Trades): prompt to set trading rules defaults and per-account `account_max_risk_pct` (or link to Accounts page).

## 9) Phased Implementation Plan
1) DB migrations & ORM models
2) Templates API (CRUD, import/export)
3) Responses API + evaluation
4) Evidence linking API
5) Trading rules settings + calendar breaches in metrics API
6) Web: templates page, trade detail panel, journal checklist mode, first-run modal
7) Filters/grouping by playbook fields in trades list (basic: boolean/select/number range)
8) QA & tests (API + basic UI flows)

## 10) Tests (API)
- Templates CRUD + versioning; import/export round-trip
- Responses create/upsert; validation errors; evaluate returns expected compliance, grade, caps
- Evidence add/delete; shared evidence across multiple field_keys
- Trading rules save/load; calendar includes breaches given seeded trades/days
- Risk cap flag appears when intended_risk_pct exceeds min cap

## 11) Migrations Outline (Alembic stubs)
```python
def upgrade():
    op.create_table('playbook_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('purpose', sa.String(16), nullable=False),
        sa.Column('strategy_bindings_json', sa.Text(), nullable=True),
        sa.Column('schema_json', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('grade_scale', sa.String(16), nullable=False, server_default='A_B_C_D'),
        sa.Column('grade_thresholds_json', sa.Text(), nullable=True),
        sa.Column('risk_schedule_json', sa.Text(), nullable=True),
        sa.Column('template_max_risk_pct', sa.Numeric(5,2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id','name','version', name='uq_playbook_templates_user_name_version')
    )

    op.create_table('playbook_responses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('trade_id', sa.Integer(), nullable=True),
        sa.Column('journal_id', sa.Integer(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('template_version', sa.Integer(), nullable=False),
        sa.Column('entry_type', sa.String(32), nullable=False),
        sa.Column('values_json', sa.Text(), nullable=False),
        sa.Column('comments_json', sa.Text(), nullable=True),
        sa.Column('computed_grade', sa.String(1), nullable=True),
        sa.Column('compliance_score', sa.Numeric(5,2), nullable=True),
        sa.Column('intended_risk_pct', sa.Numeric(5,2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_playbook_responses_template', 'playbook_responses', ['template_id','template_version'])
    op.create_index('ix_playbook_responses_trade', 'playbook_responses', ['trade_id'])

    op.create_table('playbook_evidence_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('response_id', sa.Integer(), nullable=False),
        sa.Column('field_key', sa.String(128), nullable=False),
        sa.Column('source_kind', sa.String(16), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_playbook_evidence_response', 'playbook_evidence_links', ['response_id'])

def downgrade():
    op.drop_index('ix_playbook_evidence_response', table_name='playbook_evidence_links')
    op.drop_table('playbook_evidence_links')
    op.drop_index('ix_playbook_responses_trade', table_name='playbook_responses')
    op.drop_index('ix_playbook_responses_template', table_name='playbook_responses')
    op.drop_table('playbook_responses')
    op.drop_table('playbook_templates')
```

```python
def upgrade():
    op.create_table('user_trading_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('max_losses_row_day', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('max_losing_days_streak_week', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('max_losing_weeks_streak_month', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('alerts_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_table('breach_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('scope', sa.String(16), nullable=False),
        sa.Column('date_or_week', sa.String(16), nullable=False),
        sa.Column('rule_key', sa.String(48), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_breach_events_user_date', 'breach_events', ['user_id','date_or_week'])

def downgrade():
    op.drop_index('ix_breach_events_user_date', table_name='breach_events')
    op.drop_table('breach_events')
    op.drop_table('user_trading_rules')
```

```python
def upgrade():
    op.add_column('accounts', sa.Column('account_max_risk_pct', sa.Numeric(5,2), nullable=True))

def downgrade():
    op.drop_column('accounts', 'account_max_risk_pct')
```

## 12) Security & Privacy
- All endpoints require auth; scope data by user_id.
- No network calls; evidence URLs are user-supplied.
- Import validates template schema and strips unknown keys.

## 13) Open Points (tracked)
- None blocking; defaults and manual linking behavior agreed.

