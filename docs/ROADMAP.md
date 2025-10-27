# Roadmap

- M0: Docker + CI + blank web + /health + tests ✅
- M1: Auth + Postgres + migrations ✅
- M2: CSV import + dry-run ✅
- M3: Dashboards + trades table ✅
- M4: Journal + screenshots ✅
- M5: Playbooks v1 ✅
- M6: Guardrails + account lifecycle ✅
- M7: Reports + filter builder ✅
  - Phase 1: Filter Builder Foundation ✅ (v0.7.1)
  - Phase 2: Saved Views ✅ (v0.7.2)
  - Phase 3: PDF Report Generation ✅ (v0.7.3 - Monthly reports fully implemented, other types as stubs)
- M8: Forex & Futures
- M9 (Stretch): Insight Coach

## Stretch Ideas

- Dashboard data export: one-click CSV for the currently selected month (date, daily net PnL, equity), honoring symbol/account/tz filters.
- Trades export polish: export full result set via streaming when filters exceed client limit.
- UI niceties: loading skeletons for KPI tiles/calendar; sticky headers for long tables across the app.
