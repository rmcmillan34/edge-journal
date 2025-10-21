# Modular Journaling — Typed Entries (M4 Continuation)

Context: M4 delivered a strong “note templates” first pass (sections; apply; create‑from‑notes; editor UX; attachments QoL; calendar). To realize the full modular, typed, analytics‑driven system described in `docs/journaling_templates_modular_drag_and_drop_spec.md`, we will continue this work as M4 expansion (prior to M5 Playbooks) with the following phases.

## 1) Current Status vs Spec
- Aligned (partial):
  - Templates: CRUD, drag‑reorder, apply to Trade/Daily, create‑from‑notes; parsing supports `##+` and preserves code fences.
  - Editors: insert‑at‑cursor; Cmd/Ctrl+S; Esc exits reorder (trade+journal).
  - Journal: daily CRUD + trade linking; attachments upload/thumbs/metadata; reorder; batch delete; multi‑select ZIP.
  - Calendar: green/red PnL; hide‑weekends; journal presence dot; attachment count pill.
- Gaps:
  - No typed blocks (field types, validation, computed formulas).
  - No versioned, schema‑driven templates; no template import/export JSON.
  - No `entries`, `entry_fields`, `entry_metrics` tables; no snapshot/versioning of templates on save.
  - No `/entries` API or server‑side validation/formula evaluation.
  - No analytics over typed fields; no query layer for block data.
  - No render/export pipeline (markdown/pdf) for entries.

## 2) Risks & Considerations
- Schema complexity and back‑compat (migrations; data upgrade paths).
- Validation surface (server‑side schema; formulas; errors UX).
- Query performance/indices for `entry_fields`.
- UI scope: block palette, builder, typed form renderer, drag‑drop.

## 3) Phased Plan

### Phase 1 — Data Foundations
- Migrations:
  - `templates_v2` (uuid id, name, entry_type, version, schema_version, blocks JSONB, metadata JSONB, created_at/updated_at).
  - `entries` (uuid id, user_id, template_id, template_version, entry_type, content JSONB, created_at/updated_at).
  - `entry_fields` (entry_id, field_key, field_type, string_val, number_val, bool_val, datetime_val, enum_val) with PK(entry_id, field_key) and indices on field_key, number_val, datetime_val.
  - Optional `entry_metrics` (entry_id, r_multiple, expectancy, etc.).
- API:
  - `/templates/v2` CRUD (block schema; import/export JSON; versioning).
  - `/entries` CRUD:
    - Validate values against template block schema.
    - Evaluate computed fields/formulas (read‑only in UI).
    - Persist entry snapshot + flatten into `entry_fields` (and `entry_metrics` if configured).
- Validation:
  - Server‑side JSON schema for blocks and fields; clear error DTOs.

### Phase 2 — Frontend Builder & Entry Form
- Template Builder UI:
  - Block palette: text, key_value, select, number, boolean, rating, datetime, attachment, computed.
  - Drag‑drop reorder; per-field config (label, required, options, min/max, regex).
  - Version bumping on edits (store template_version).
- Entry Editor UI:
  - Render form from block schema; validate inputs; compute read‑only fields; save → `/entries`.

### Phase 3 — Analytics & Queries
- Populate `entry_fields` (and `entry_metrics`) during `/entries` save.
- Extend `/metrics` or add `/entry-metrics` for field‑based KPIs (e.g., adherence, session stats).
- Indices for common queries; provide example SQL per spec (win rate by session, expectancy by symbol, rule adherence).

### Phase 4 — Rendering & Export
- Block renderers → Markdown document (+ optional front‑matter) → PDF (Chromium/wkhtmltopdf).
- Endpoints: `/entries/{id}/export.md` and `/entries/{id}/export.pdf`, with batch export support.
- Backups: CSV/JSON export of entries + flattened fields + derived metrics (privacy defaults).

### Phase 5 — Back‑Compat & Migration Tools
- Template upgrader: old → v2 schema.
- Conversion helpers: parse existing notes (markdown sections) into entry content where feasible.
- Feature flag to run typed entries alongside current notes until parity/confidence.

## 4) Quick Wins (Near‑Term)
- Template import/export JSON for current templates.
- Minimal version metadata on current templates to pave upgrade path.
- Optional: basic entry snapshot (content JSON) tied to current templates even before full typed blocks.

## 5) Acceptance (Initial Tranche)
- Data: tables created; indices in place; migrations safe.
- API: `/templates/v2` + `/entries` with server‑side validation and formula evaluation.
- Frontend: builder can create a simple typed template; entry editor can render it and save; data flattens into `entry_fields`.
- Analytics: at least one field‑based KPI surfaced from `entry_fields`.
- Export: markdown export for an entry; pdf is a nice‑to‑have if not in first slice.

## 6) References
- Spec: `docs/journaling_templates_modular_drag_and_drop_spec.md`
- Current implementation notes: `docs/USAGE.md`, `README.md`
