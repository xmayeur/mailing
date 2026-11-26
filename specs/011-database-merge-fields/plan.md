# Implementation Plan: Database Merge Fields in Mailing Content

**Branch**: `011-database-merge-fields` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-database-merge-fields/spec.md`

## Summary

Insert database merge fields (`${FIELDNAME}`) into the mailing content from the editor and substitute personal values when the mailing goes to one recipient at a time, blank values when one message covers several recipients. The send pipeline already contains a `${field}` substitution engine (`sendMail.format_message`) applied per batch in `send_campaign`; the plan reuses and hardens it (per-marker unknown-field blanking, blank value for multi-recipient batches, subject-line replacement) and adds the editor UX: a field picker populated from the existing database schema cache, inserting the marker at the Quill.js cursor through the existing Python↔JS bridge.

## Technical Context

**Language/Version**: Python 3.12–3.14 (`requires-python = ">=3.12, <3.15"`)
**Primary Dependencies**: PySide6 ≥6.12 (Qt6 desktop UI, QWebEngineView + Quill.js rich text editor), python-calamine (Excel), gspread/google-api-python-client (Google Sheets), beautifulsoup4, pytest ≥9, pyright, ruff
**Storage**: config.yml (profiles/config), subscriber databases as CSV / XLSX / Google Sheets (read at send time; schema via `SchemaCacheProvider` + `DatabaseSchemaProvider`)
**Testing**: pytest (unit + integration), pytest-mock, pytest-asyncio; behave for BDD scenarios; pyright type checking
**Target Platform**: macOS desktop app (signed bundle, Nuitka/onefile builds); cross-platform Qt
**Project Type**: desktop-app
**Performance Goals**: Insertion and picker refresh <1 s for databases with ~100 fields; send-time substitution adds no measurable overhead over current `format_message` (regex over message text per batch)
**Constraints**: No changes to stored mailing content; no new send modes; substitution must never leak a subscriber's data into a message addressed to other recipients
**Scale/Scope**: Subscriber lists already handled today (thousands of rows); feature touches `src/editor.py`, `src/sendMail.py`, `src/editor_assets/editor.html` (~10 screens/1 dialog equivalent)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution (`.specify/memory/constitution.md`) is the unfilled template — no ratified principles or gates are defined. Check result: no active gates to enforce. The feature itself aligns with the workflow implied by the repo (test-first via pytest, no complexity added: reuse of `format_message` avoids a second substitution engine).

**Post-Phase 1 re-check**: No changes; design reuses existing send pipeline and schema cache, no new modules beyond one editor helper + tests.

## Project Structure

### Documentation (this feature)

```text
specs/011-database-merge-fields/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── sendMail.py                    # format_message, send_campaign/_build_and_send/_flush_batch, build_email
├── editor.py                      # RichTextEditor (Quill.js in QWebEngineView), schema cache wired per profile
└── editor_assets/
    └── editor.html                # Quill editor page (JS bridge functions)

tests/
├── unit/
│   ├── test_sendmail_core.py      # extend: format_message behavior (blanking, unknown fields, subject)
│   └── test_editor.py             # extend: field picker + insert marker unit paths
└── integration/
    └── test_sendmail_integration.py  # extend: batch semantics (1 vs N recipients)
```

**Structure Decision**: Single existing project; all changes land in the current modules. No new packages.

## Complexity Tracking

> No constitution violations — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
