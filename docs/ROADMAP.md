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
  - Phase 3: PDF Report Generation ✅ (v0.7.4 - All 7 report types, account separation modes, screenshot embedding)
- M8: Forex & Futures ✅
  - Phase 1: Foundation - Asset Class Support ✅ (v0.8.1)
  - Phase 2: Forex Support - Pips, Lot Sizes, FTMO Import ✅ (v0.8.1)
  - Phase 3: Futures Support - Ticks, Contracts, Tradovate Import ✅ (v0.8.1)
- M9 (Stretch): Insight Coach

## M7 Stretch Goals (Advanced Reporting)

- **Quarterly reports** - Q1/Q2/Q3/Q4 performance summaries with month-by-month breakdown
  - Similar structure to yearly reports but scoped to 3-month periods
  - Quarter selection in report generation modal
  - Comparison metrics vs previous quarter
- **Scheduled report generation** - Weekly/monthly email digest with automated PDF delivery
- **Report templates** - Customizable report sections and layouts
- **Multi-currency support** - Currency conversion and display in reports
- **Playbook field aggregation** - Performance analysis by playbook grades and compliance scores
- **Compare reports** - Side-by-side comparison (e.g., Jan 2025 vs Jan 2024, Q1 vs Q4)
- **Export to CSV/Excel** - Additional export formats beyond PDF
- **Interactive charts** - Plotly-based charts with drill-down capabilities

## M8 Stretch Goals (Forex & Futures Enhancements)

- **Configurable dashboard widgets** - User-customizable dashboard with drag-and-drop widget layout
  - Widget library: KPI tiles (win rate, profit factor, expectancy, pip stats, tick stats)
  - Forex-specific widgets: Total pips, avg pips/trade, pip win rate, avg lot size
  - Futures-specific widgets: Total ticks, avg ticks/trade, tick win rate, contracts traded
  - Asset class filter widgets: Performance by forex/futures/equity
  - Chart widgets: Equity curve by asset class, monthly pip/tick breakdown
  - User preferences: Save widget layouts per user, reset to defaults
  - Mobile-responsive widget grid
- **Multi-currency P&L conversion** - Display P&L in user's preferred base currency with historical FX rates
- **Swap/rollover calendar** - Visual calendar showing swap charges by day for swing traders
- **Contract expiration alerts** - Notifications and dashboard warnings for expiring futures contracts
- **Symbol-level analytics** - Deep dive by currency pair (EURUSD vs GBPJPY) or futures contract (ES vs NQ)

## General Stretch Ideas

- Dashboard data export: one-click CSV for the currently selected month (date, daily net PnL, equity), honoring symbol/account/tz filters.
- Trades export polish: export full result set via streaming when filters exceed client limit.
- UI niceties: loading skeletons for KPI tiles/calendar; sticky headers for long tables across the app.
- CI test improvements: Mock file system operations for report generation tests instead of gracefully catching permission errors. Currently CI tests pass by degrading functionality (skipping disk saves), but proper mocking would validate full feature behavior including attachment embedding and report history storage.
