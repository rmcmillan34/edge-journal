# Prompt: Implementation Delta Analysis — Modular Journaling Feature

**Purpose:**  
Guide GPT/Codex/Claude agents to perform an in-depth *implementation delta analysis* between the current trading journal system and the new modular journaling & analytics feature spec.

---

## 🧭 Context
You are an experienced **software systems analyst and architect** tasked with evaluating the implementation gap between the current application and a new journaling feature specification.

The current system is a **trading journal application** implemented in a modern full-stack environment (e.g., Next.js, TypeScript, Prisma ORM, PostgreSQL, and Tailwind).  
The new specification (`docs/journaling_templates_modular_drag_and_drop_spec.md`) introduces a **modular, drag-and-drop journaling system** with form-based data capture, analytics persistence, and markdown/PDF export.

---

## 🎯 Objective
Identify and document the **delta** between the existing implementation and the new specification.  
Highlight what is already implemented, what is missing, and what must change.

---

## 🧩 Analysis Requirements

For each of the following layers, perform a **gap analysis** and summarise what must be added, changed, or refactored:

| Layer | Description |
|-------|--------------|
| **Database Schema** | Tables, relations, migrations, Prisma models. Identify new entities (e.g., `entry_fields`, `entry_metrics`, `fact_trades`) and changes to existing ones. |
| **API & Data Models** | Required endpoints (`/api/templates`, `/api/entries`), DTOs, JSON schema integration, and validation. |
| **Frontend UI/UX** | Changes to accommodate drag-and-drop editor, block builder, and data entry forms. Specify affected components or new views. |
| **State Management** | Identify new stores or contexts (e.g., `useTemplateBuilder`, `useEntryForm`). |
| **Form & Rendering Logic** | How typed fields, validation, and computed metrics integrate with markdown/PDF rendering. |
| **Analytics Pipeline** | Data ingestion, flattening, metrics computation, and query layer for dashboards. |
| **Exporting & Reporting** | Markdown/PDF generation pipeline, headless browser integration, and user export flow. |

---

## 🧱 Output Format

Provide the analysis in **Markdown**, using the following structure:

```markdown
# Implementation Delta — Modular Journaling Feature

## 🔍 Current Architecture Summary
Describe current modules, schemas, and journaling functionality as implemented today.

## ⚙️ New Requirements Overview
Summarise major capabilities introduced by the new spec (form-fields, analytics DB, markdown exports, etc.).

## 🧩 Gap Analysis by Layer
### Database Schema
[List differences and proposed new entities.]
### API Layer
### Frontend Components
### State & Hooks
### Analytics & Metrics
### Rendering/Exports

## 🪜 Implementation Plan & Milestones
Break the rollout into sequential phases (e.g., schema migration, backend APIs, frontend builder, analytics dashboards).

## 🧠 Risks & Recommendations
Note dependencies, backward-compatibility issues, and complexity areas.
```

---

## ⚙️ Usage Example (Codex CLI or GPT CLI)

**Codex CLI:**
```bash
codex analyze --doc ./docs/journaling_templates_modular_drag_and_drop_spec.md --compare ./src   --prompt ./prompts/implementation_delta_analysis.md   --output ./analysis/journaling_feature_gap.md
```

**ChatGPT CLI:**
```bash
cat docs/journaling_templates_modular_drag_and_drop_spec.md | gpt5 --prompt "./prompts/implementation_delta_analysis.md"
```

---

## 🧩 Optional Context Injection
To improve analysis accuracy, provide the following (if available):
- `schema.prisma` or SQL schema dump
- `src/pages/api/` directory or route list
- `frontend/components/` directory structure
- any existing journaling-related JSON schema or frontend form code

---

## 📁 Recommended Repo Structure
```
/docs/
  journaling_templates_modular_drag_and_drop_spec.md
/prompts/
  implementation_delta_analysis.md
/analysis/
  journaling_feature_gap.md
```

---

**Created:** 20 Oct 2025  
**Author:** Ryan McMillan  
**Version:** v1.0  
**Intent:** Consistent agentic analysis prompt for journaling system upgrades.
