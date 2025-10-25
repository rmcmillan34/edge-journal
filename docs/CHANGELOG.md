# Changelog

All notable changes to Edge‑Journal are documented here. Version is sourced from the root `VERSION` file.

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

