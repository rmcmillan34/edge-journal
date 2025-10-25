# Changelog

All notable changes to Edge‑Journal are documented here. Version is sourced from the root `VERSION` file.

## [0.6.0] - 2025-10-25
### M6: Guardrails + Account Lifecycle
**Backend:**
- Add account closure tracking: `closed_at`, `close_reason`, `close_note` fields.
- Add account lifecycle API: `POST /accounts/{id}/close` and `POST /accounts/{id}/reopen`.
- Add `include_closed` query parameter to `GET /accounts` endpoint.
- Implement enforcement mode logic ('off'|'warn'|'block') for risk cap and loss streak violations.
- Risk cap enforcement: playbook responses now check against min cap and enforce based on user's enforcement_mode.
- Loss streak enforcement: trade creation checks daily loss streaks and enforces based on enforcement_mode.
- Import guard: CSV uploads reject trades targeting closed accounts with clear error message.
- Breach logging: create breach events for loss streaks (not just risk caps).
- Migration 0017: add account closure tracking fields.

**Web UI:**
- Settings: enable 'block' enforcement mode option (previously disabled).
- Settings: clarify enforcement mode labels (Off/Warn/Block).

**API Schema:**
- Add `AccountClose` and `AccountReopen` schemas for structured account lifecycle operations.
- Add `warning` field to `PlaybookResponseOut` for enforcement mode warnings.
- Extend `AccountOut` with `closed_at`, `close_reason`, `close_note` fields.

**Enforcement Module:**
- New `api/app/enforcement.py` module with `check_risk_cap_breach()` and `check_loss_streaks()` helpers.
- Supports 'off' (no enforcement), 'warn' (log + warn), 'block' (raise 403) modes.

## [0.5.3] - 2025-10-25
- Web: Enable bundled Nerd Fonts with preload and `@font-face` URLs; fall back to local fonts if not present.
- Web: Add `web/public/fonts/README.md` with placement/licensing guidance; OFL included alongside fonts.
- API: Add tests for Playbook Evidence (add/list/delete) and Instrument Checklist flows.
- Docs: Update M5 Playbooks tech design to Implemented; expand USAGE with upgrading and M5 details.
- Repo hygiene: Ignore `results*.txt` build logs.

## [0.5.2] - 2025-10-21
- Web: Fix duplicate function in Playbooks page; rename drag‑drop mover to `moveEditFieldTo`.

## [0.5.1] - 2025-10-21
- Playbooks v1: core models, API routes, migrations, and web UI.
  - Templates CRUD, quickstarts, export/import, versioned updates.
  - Trade responses + instrument checklist + evidence links.
  - Settings for trading rules; calendar breach badges.

## [0.5.0] - 2025-10-21
- Bump to v0.5.0 to start next feature tranche.

