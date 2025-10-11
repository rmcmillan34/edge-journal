# Edge‑Journal — Requirements Specification (MVP v0.1)

> A CSV‑first, broker‑agnostic trading journal with prop‑firm guardrails, built for fast daily use and deep post‑trade review. **Open‑source, self‑hosted, local‑first**, and privacy‑respecting.

---

## 1) Product vision & goals
**Vision:** Help discretionary and systematic traders make better decisions by turning raw trade exports into clean insights and repeatable habits — without broker integrations.

**Open‑source stance:** Users can run locally (single‑machine Docker) or in a homelab, keep full control of data, and easily back up/restore.

**Primary goals (MVP)**
- Import trades from CSV files (cTrader, MT4/5, DXTrade, OANDA; **custom mapping**).
- **Support both Forex and Futures** (correct PnL math, fees, sessions, prop‑firm rules).
- Normalise, de‑duplicate, and store trades across **multiple accounts** (incl. prop‑firm accounts).
- Dashboards: PnL, win rate, RR, expectancy, drawdowns, streaks, **calendar heatmap**.
- Journal layer: per‑trade tags, notes, **multiple screenshots**, and checklist compliance.
- Prop‑firm guardrails: daily/max loss checks with clear flags; **account lifecycle** (close/reopen).
- **Portable data:** one‑click backup/export + simple restore/import into a fresh install.

**Secondary goals (MVP+)**
- Strategy views and filterable exports.
- Equity curve, PnL by weekday/session, top instruments.
- Sessionisation by Australia/Sydney and exchange session day for futures.

**Non‑goals (MVP)**
- Live broker connections, real‑time execution, automated syncing.

---

## 2) Personas
- **Owner/Trader**: uploads CSVs, reviews dashboards, writes notes.
- **Coach/Reviewer (optional)**: read‑only review of reports/trades.
- **Contributor**: helps maintain presets and features.

---

## 3) User stories (MVP)
- Upload CSV → preview mapping/errors → dry‑run → commit.
- Re‑upload safely; de‑dup and idempotent updates.
- Journal each trade with notes/tags/screenshots and playbook.
- Filter & analyse trades; click calendar day to see trades for that day.
- Detect guardrail breaches; prompt to close account; allow reopen.
- Backup/restore entire workspace.
- Generate weekly/monthly **PDF** reports for one/all accounts with metrics + per‑trade details.
- **Pre‑session analysis & reflections** with local notifications.
- **Notion‑style filter builder** and saved views.

---

## 4) Scope (MVP)
### In scope
CSV import + presets + custom mapping; validation & dry‑run; core dashboards; journal & attachments; playbooks (v1) + versioning; prop‑firm guardrails + account lifecycle; backup/restore; self‑hosting; **Forex & Futures**.

### Out of scope
Complex multi‑tenant roles; advanced analytics (MAE/MFE, regime) — later; mobile app (responsive web only).

---

## 5) Functional requirements

### 5.1 Import & mapping
- **FR‑I1:** Upload CSV up to 20 MB.
- **FR‑I2:** Auto‑detect preset by headers; allow override.
- **FR‑I3:** **Custom mapping** UI; save as preset.
- **FR‑I4:** Preview grid (20 rows); inline errors.
- **FR‑I5:** Dry‑run summary (insert/update/skip + reasons).
- **FR‑I6:** Upsert rules: `(file_hash, row_hash)`; composite `trade_key = account_id + symbol + side + open_time + quantity + entry_price` prevents duplicates.

### 5.2 Normalisation & storage
- **FR‑N1:** Store timestamps as **UTC**; display in user TZ (Australia/Sydney) or exchange session day (futures).
- **FR‑N2:** Quantities → **units** (lots→units); **futures** quantity = contracts.
- **FR‑N3:** NetPnL = GrossPnL − Fees (commission + swap + other).

#### 5.2.1 Accounts lifecycle
- **FR‑AC1:** **Close account** (blown/retired). Closed accounts excluded from default dashboards and imports.
- **FR‑AC2:** Import guard: reject trades targeting **closed** accounts (offer remap).
- **FR‑AC3:** **Reopen** closed account (audit‑logged).
- **FR‑AC4:** Filters: toggle to show/include closed accounts.
- **FR‑AC5:** Metadata: `closed_at`, `close_reason` (breach/retired/merged/other), notes + badge.
- **FR‑AC6:** **Breach→Close prompt** on daily/max loss breach (optional auto‑close).

### 5.3 Journal
- **FR‑J1:** Per‑trade: tags[], strategy, notes (Markdown), **attachments** (multi‑file), chart URL.
- **FR‑J2:** Checklist fields from playbooks.
- **FR‑J3:** Basic edit history.

#### 5.3.1 Playbooks & custom forms
- **FR‑PB1:** No‑code form builder (boolean, select, number, text, rich‑text, URL, attachment, rating, derived fields).
- **FR‑PB2:** **Versioning**; trade stores `template_id + version`.
- **FR‑PB3:** Optional **strategy binding** (auto‑suggest template).
- **FR‑PB4:** Required/optional + validation (regex/min/max).
- **FR‑PB5:** Repeatable sections (partials/scale‑ins/outs).
- **FR‑PB6:** **Analytics** on custom fields (filter/group/chart).
- **FR‑PB7:** Template export/import (JSON).
- **FR‑PB8:** Privacy: local‑only by default.
- **FR‑PB9: Setup grades (A/B/C/D)** — define grade criteria from fields (required/optional) + **risk schedule** (e.g., A=1.0%, B=0.5%, C=0.25%, D=0). Compute grade from answers; allow manual override with audit.
- **FR‑PB10:** **Grade‑aware risk caps** — enforce per‑grade caps before account guardrails (warn/block).
- **FR‑PB11:** **Instrument/day checklist mode** — open a template for a symbol/day; save pre‑trade record; link later trades automatically.

#### 5.3.2 Attachments & screenshots
- **FR‑AT1:** Many images (PNG/JPG/WebP) + PDFs; per‑file cap 5–10 MB.
- **FR‑AT2:** Metadata: **timeframe** (M1…D1), **state** (marked/unmarked), **view** (entry/management/exit/post), caption.
- **FR‑AT3:** Drag‑sort + grouped gallery.
- **FR‑AT4:** Thumbnails; **strip EXIF**.
- **FR‑AT5:** Paste/drag‑drop.
- **FR‑AT6:** Link‑only entries (e.g., TradingView).
- **FR‑AT7:** Included in backups with manifest mapping.

### 5.4 Analytics & dashboards
- **FR‑A1:** KPIs: gross/net PnL, win rate, avg RR, expectancy, max DD, streaks.
- **FR‑A2:** Charts: equity curve; daily PnL bar; PnL by weekday/session; top instruments.
- **FR‑A3:** Filters: date range, account(s), instrument(s), **asset class (Forex/Futures)**, session(s), strategy/tags.
- **FR‑A4:** Trades table with inline link to detail.
- **FR‑A5:** **Calendar heatmap** — day colored by net PnL (green/red/grey); tooltip (trades, net PnL, W/L); click → filtered trades. Respect user TZ or **exchange session day** (e.g., CME 17:00–17:00 CT).
- **FR‑A6:** Optional breach badges on calendar days.
- **FR‑A7:** **Notion‑style filter builder** — nested AND/OR; equals/≠; contains; in/not‑in; ≥/≤ (numbers/dates); tags; **playbook field filters**. Drives tables and charts.
- **FR‑A8:** **Saved views** — persist filters/columns/sort/group/date. URL‑addressable.
- **FR‑A9:** **Group & summarise** — aggregates by any field (incl. playbook fields).
- **FR‑A10:** **Grade analytics** — performance by A/B/C/D (PnL, win%, expectancy, compliance %).

### 5.5 Prop‑firm guardrails
- **FR‑P1:** Daily loss vs daily limit (configurable).
- **FR‑P2:** Cumulative loss vs max loss.
- **FR‑P3:** Breach flags with explanations + links.
- **FR‑P4:** **Breach→Close prompt** (ties into FR‑AC6).
- **FR‑P5:** Profiles: fixed/static and **trailing drawdown** (params: trail_amount, trail_basis = realized | intraday_equity | EOD, start_equity, optional stop_trailing_at stage). Optional per‑trade **max risk %**.
- **FR‑P6:** Honour **asset class** and session boundaries.
- **FR‑P7:** **Grade‑aware risk caps** enforced before account rules.

### 5.6 Export & backup
- **FR‑E1:** One‑click **.edgejournal.zip** backup (DB dump + attachments + config JSON).
- **FR‑E2:** Restore/import archive into fresh install (version‑aware).
- **FR‑E3:** Data exports (CSV/Parquet) respect current filters/saved view.
- **FR‑E4:** Optional scheduled local backups.
- **FR‑E5:** SHA‑256 checks for integrity.

### 5.7 Self‑hosting & deployment
- **FR‑D1:** `docker-compose.yml` for single host (app + Postgres; filesystem or MinIO for attachments).
- **FR‑D2:** **Local‑only** mode (no network calls out).
- **FR‑D3:** Homelab mode with reverse proxy/TLS.
- **FR‑D4:** **CLI** inside container: create user, reset password, backup/restore, migrations, verify archive, **close/reopen account**.
- **FR‑D5:** Host‑mounted volumes: `/data/db`, `/data/uploads`, `/data/backups`, `/config`.

### 5.8 Reporting & PDF exports
- **FR‑R1:** Weekly/Monthly PDF for period + scope (one account/all/broker).
- **FR‑R2:** Sections: (1) **Metrics** (KPIs + equity), (2) **Trade‑by‑trade** (instrument, timestamps, net PnL, tags, **notes**, **playbook responses**, **screenshots** inline or appendix).
- **FR‑R3:** Themed light/dark; header/footer with page # + date range.
- **FR‑R4:** Include up to N screenshots inline (default 2); rest in appendix.
- **FR‑R5:** Local server‑side rendering (headless Chromium/HTML‑to‑PDF); no external calls.
- **FR‑R6:** Deterministic filenames; archive under `/data/exports`.
- **FR‑R7:** Reports honour current filters/saved view.

### 5.9 Pre‑session technical analysis & reflections
- **FR‑PS1:** **Daily pre‑session analysis**: watchlist, bias/scenarios per symbol, key levels, screenshots, notes.
- **FR‑PS2:** Auto‑link trades from that day/symbol; manual override allowed.
- **FR‑PS3:** **Reflection** task after session: plan vs outcome, misses, action items.
- **FR‑PS4:** **Local notifications** (desktop/in‑app) for pending reflections.
- **FR‑PS5:** Calendar badges for analysis days; dashboard shows pending reflections.
- **FR‑PS6:** Reports can include **Pre‑session** + **Reflections** sections.

### 5.10 Asset‑class support (Forex & Futures)
- **FR‑AS1:** Support **Forex** and **Futures** instruments.
- **FR‑AS2:** Metadata\n  - Forex: `base_ccy`, `quote_ccy`, `pip_size`, `lot_size`.\n  - Futures: `root_symbol` (ES/MES/NQ…), `contract_code` (ESZ5), `contract_month`, `exchange`, `tick_size`, `tick_value`, `multiplier`, `currency`, `session_tz`, `session_hours`.\n
- **FR‑AS3:** PnL normalisation\n  - Forex: PnL in quote ccy; convert to account/base if configured.\n  - Futures: `PnL = ((exit - entry) / tick_size) * tick_value * contracts − fees`; show **ticks** + currency; per‑contract fees.\n
- **FR‑AS4:** CSV presets add **NinjaTrader/Tradovate/IBKR**; auto‑parse `MESZ5` into metadata.\n
- **FR‑AS5:** Option to group by **exchange session day** (e.g., CME 17:00–17:00 CT) for calendar/daily metrics.\n
- **FR‑AS6:** Aggregate analytics across contracts of same root (continuous‑style view).

### 5.11 Insight Coach (**Stretch goal**)
- **FR‑IC1:** Local, **explainable** insights (contingency tables, bootstrapped CIs, simple decision trees per grade) to surface patterns:\n  - “**London** A‑setups: +1.4R; **NY** B‑setups: −0.6R — skip?”\n  - “Stop‑outs cluster when **HTF≠LTF bias** and news <30m.”\n  - “After **3 losses** in a day, expectancy −0.8R — enable cool‑down?”\n
- **FR‑IC2:** Each card explains **why** (n, delta, CI) + button to **open filtered view**.\n
- **FR‑IC3:** Weekly digest (3 lean‑into, 3 avoid) + one‑click **Action Items**.\n
- **FR‑IC4:** Hypothesis tracking (forward‑test N trades and report outcome).\n
- **FR‑IC5:** Private & testable; heavier models opt‑in.\n

---

## 6) Non‑functional requirements (NFR)
- **Security:** JWT auth (local) or provider; all endpoints protected; presigned uploads; **Argon2** password hashing; OWASP Top‑10 hygiene.
- **Privacy:** No telemetry. PII minimised; optional hashing for broker IDs. Local‑only mode.
- **Reliability:** Import is transactional; partial failures rollback.
- **Performance:** 10k‑row import <5s on modest machine; cached dashboards <1s.
- **Observability:** Structured logs; import audit trail; correlation IDs.
- **Portability:** Dockerised; dev SQLite; prod Postgres + FS/S3‑compatible storage. Backups versioned with schema migrations.
- **Accessibility:** Keyboard‑friendly; light/dark themes included.
- **TDD:** Unit + property tests (CSV/timezones); E2E for import→dashboard; fuzzing malformed CSV; security tests; CI gate ≥80% coverage.
- **Theme safety:** Themes are declarative (colour/spacing/fonts); no arbitrary code execution.

---

## 7) Data model (initial)
```
users(id, email, tz="Australia/Sydney", created_at)

accounts(id, user_id, name, broker_label, base_ccy,
        daily_loss_limit, max_loss_limit,
        status ENUM('active','closed') DEFAULT 'active',
        closed_at, close_reason, close_note,
        asset_class ENUM('forex','futures') DEFAULT 'forex',
        use_exchange_session_day BOOL DEFAULT false)

instruments(id, symbol, asset_class,
           root_symbol, exchange, contract_month,
           tick_size, tick_value, multiplier,
           session_tz, session_hours,
           pip_size, lot_size, quote_ccy, base_ccy)

uploads(id, user_id, filename, file_hash, uploaded_at, status, preset)

playbook_templates(id, user_id, name, purpose ENUM('pre','in','post','generic'),
                   strategy_bindings[], schema_json, version, is_active, created_at,
                   grade_scale ENUM('none','A_B_C_D') DEFAULT 'A_B_C_D',
                   risk_schedule_json)

playbook_responses(id, trade_id, template_id, template_version,
                   values_json, created_at,
                   computed_grade CHAR(1) NULL,
                   compliance_score DECIMAL(5,2) NULL)

trades(id, account_id, instrument_id, external_trade_id,
       side, qty_units, entry_price, exit_price,
       open_time_utc, close_time_utc,
       gross_pnl, fees, net_pnl,
       strategy, tags[], notes_md, chart_url,
       source_upload_id, trade_key, version,
       intended_risk_pct DECIMAL(5,2) NULL,
       applied_risk_cap_pct DECIMAL(5,2) NULL)

trade_attachments(id, trade_id, filename, file_hash, mime, bytes,
                  stored_path, caption, timeframe,
                  state ENUM('marked','unmarked'),
                  view ENUM('entry','management','exit','post'),
                  position_index, created_at)

days(id, account_id, date, daily_net_pnl,
     max_intraday_drawdown, daily_loss_breach_bool)

saved_views(id, user_id, name, view_json, created_at, updated_at)
```
> `risk_schedule_json` maps grades to risk caps (e.g., `{"A":1.0,"B":0.5,"C":0.25,"D":0}`).

---

## 8) CSV presets (starter)
- **cTrader (Forex)**, **MT4/MT5**, **DXTrade**, **OANDA**.
- **NinjaTrader (Futures)**, **Tradovate (Futures)**, **IBKR TWS**.
- Required normalised fields: Account, Symbol/Contract, Side, Open/Close Time, Quantity (units or contracts), Entry/Exit, Fees, (Gross/Realized)PnL, NetPnL, Notes, ExternalTradeID.

---

## 9) Metrics & formulas
- NetPnL = Gross − Fees
- Win rate = wins / total
- Avg RR = mean(|win|/|loss|) or per‑trade RR\n- Expectancy = win_rate × avg_win − (1 − win_rate) × avg_loss\n- Max drawdown on equity curve\n- Futures ticks from `tick_size` × `tick_value`

---

## 10) UI/UX slices (MVP)
1) Upload page (preset auto‑detect, mapping editor, preview, dry‑run, commit).
2) Overview dashboard (KPIs, equity, **calendar**, filters), recent trades table.
3) Trades table (pagination, column picker, export, URL‑synced filters).
4) Trade detail (journal, **attachments gallery**, guardrail badges, **playbook** with grade + risk cap).
5) Playbooks (builder, versioning, export/import, **grade criteria + risk schedule**).
6) Pre‑session analysis (composer) + **checklist mode**; pending reflections widget.
7) Settings (accounts, sessions, rule profiles, grade enforcement, **backup/restore**, account lifecycle).

---

## 11) API sketch
- `POST /api/uploads` → create upload (presigned URL/metadata)\n- `POST /api/uploads/{id}/commit` → parse/map/validate/dry‑run/commit\n- `GET /api/trades` → list/filter (supports date & **filter DSL JSON**)\n- `GET /api/trades/{id}` → detail; `PATCH /api/trades/{id}` → update journal\n- `GET /api/metrics/overview` → KPIs + charts\n- `GET /api/metrics/calendar?start=YYYY-MM-01&end=YYYY-MM-31`\n- `POST /api/reports/pdf` → generate PDF (period/scope + current filters)\n- Attachments: `POST/PATCH/DELETE /api/trades/{id}/attachments`\n- Playbooks: list/create/export/import; `POST /api/playbooks/evaluate` → compute grade & risk cap\n- Accounts: `POST /api/accounts/{id}/close`, `POST /api/accounts/{id}/reopen`\n- Views: list/create/delete saved views\n- Backup/Restore: `POST /api/backup`, `POST /api/restore`\n- Admin CLI: `edgejournal backup|restore|create-user|migrate|verify|close-account|reopen-account|report|evaluate`

---

## 12) Acceptance criteria (MVP)
- 5k‑row cTrader CSV import <5s; dashboards update; re‑import de‑dups.
- NinjaTrader **Futures** CSV imports; PnL ticks & currency correct; per‑contract fees applied.
- Mapping override works; custom preset saved.
- Notes/tags edits persist and filter correctly.
- Daily loss breach flagged when daily NetPnL < −daily_limit; **Breach→Close** prompt appears.
- Exports match filtered dataset; sums reconcile with dashboard.
- **Playbooks**: create template → attach to trade → later edit template (new version) without altering past responses; custom fields are filterable/groupable; template export/import works.
- **Setup grades**: compute grade + enforce risk schedule (warn/block). Grade & compliance display in analytics.
- **Attachments**: add multiple screenshots, label/reorder; backups include and restore correctly.
- **Calendar**: heatmap by daily NetPnL; day click filters to that date; respects user TZ or futures session day.
- **Accounts lifecycle**: close/reopen; closed accounts excluded by default; import guard active.
- **Filter builder & saved views**: nested filters incl. playbook fields & grade; exports/PDFs respect active view.
- **Reports**: weekly/monthly PDF (one/all accounts) with metrics + trade pages + screenshots appendix; generated locally.

---

## 13) Risks & mitigations
- CSV heterogeneity → presets + mapping UX + tests.
- Timezone/session confusion → UTC storage + clear controls + tooltips.
- Prop‑firm rules variance → configurable rule profiles.
- PDF size → cap inline images + appendix; size warnings.
- Performance → streaming parser + chunked upserts + indexes/materialised views.

---

## 14) Roadmap
- **M0**: Docker + CI + blank app + `/health` + tests ✅
- **M1**: Auth + Postgres + migrations
- **M2**: CSV import (dry‑run → commit) + presets
- **M3**: Dashboards (KPIs, equity, **calendar**) + trades table
- **M4**: Journal + **multi‑screenshot** attachments
- **M5**: Playbooks v1 + analytics on fields
- **M6**: Guardrails + **account lifecycle**
- **M7**: Reports (PDF) + Notion‑style filters + saved views
- **M8**: Forex & Futures polish (tick math, sessions)
- **M9 (Stretch)**: **Insight Coach** + MAE/MFE + Hypothesis Lab

---

## 15) Definition of Done (MVP v0.1)
- All acceptance criteria met; CI green with ≥80% coverage.
- Dockerised dev/prod, reproducible builds.
- Minimal user guide (upload → dashboard → journal → export) with screenshots.
- **Backup/restore** verified end‑to‑end on a fresh machine.
