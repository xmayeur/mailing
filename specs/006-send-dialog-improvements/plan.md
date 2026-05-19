# Implementation Plan: Send Dialog Improvements

**Branch**: `006-send-dialog-improvements` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-send-dialog-improvements/spec.md`

## Summary

Extend the PyQt6-based Send Mailing dialog (in `src/sendMail.py`) with three enhancements: (1) auto-populate Subject field from HTML `<h1>` heading or filename, (2) add file attachment widget with add/remove controls, and (3) enforce Test mode checkbox (locked until test email sent, resets per campaign). All work within existing PyQt6 dialog, no new dependencies.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: PyQt6 (≥6.7.0), pyyaml, google-api-python-client  
**Storage**: N/A (state tracked in dialog instance, not persisted)  
**Testing**: pytest, PyQt6 mocking (existing pattern from `tests/`)  
**Target Platform**: Desktop (Windows, macOS, Linux)  
**Project Type**: Desktop GUI application (PyQt6) + CLI tool  
**Performance Goals**: Subject extraction <200ms, UI responsiveness maintained  
**Constraints**: Dialog must not block editor; no external file size limits (user responsible)  
**Scale/Scope**: Single dialog in `src/sendMail.py` (existing `_SendDialog` class)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **No violations** — Feature is a UI enhancement to existing dialog, no new libraries, no architectural changes.

## Project Structure

### Documentation (this feature)

```text
specs/006-send-dialog-improvements/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (UI component contract)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── editor.py            # WYSIWYG editor (contains _SendDialog class)
├── sendMail.py          # Main entry point (unrelated to this feature)
└── [other modules...]

tests/
├── test_sendMail.py     # Existing tests for sendMail CLI
└── [other tests...]
```

**Structure Decision**: Single-file enhancement to `src/editor.py`. Dialog lives in existing `_SendDialog` PyQt6 class. No new files or directories needed for core feature. Tests added to `tests/test_sendMail.py` (mocking PyQt6 dialog as existing tests do).

## Phase Breakdown

### Phase 0: Research

Tasks:
- Locate existing `_SendDialog` implementation in `src/editor.py`
- Identify HTML file loading mechanism (extract `<h1>` from current document)
- Review how test mode currently works in sendMail CLI
- Document file attachment passing to email backend

**Output**: `research.md` with implementation references

### Phase 1: Design & Contracts

1. **Data Model** (`data-model.md`):
   - DialogState entity (subject, attachments list, test_mode_locked)
   - Subject extraction logic (first `<h1>` or filename)
   - Attachment entity (file path, display name)

2. **UI Component Contract** (`contracts/send-dialog-component.md`):
   - Subject input behavior (auto-populate on open, user-editable)
   - Attachment list widget interface (add, remove, display)
   - Test checkbox state machine (locked → send test → unlocked → reset on close)

3. **Quickstart** (`quickstart.md`): Example of new dialog behavior in action

4. **Agent Context Update**: Run update script to document new features

### Phase 2: Implementation (via `/speckit.tasks`)

Task groups:
1. **Subject extraction**: Parse HTML, extract `<h1>`, fallback to filename
2. **Attachment widget**: File picker, list display, deletion
3. **Test mode state machine**: Lock/unlock logic tied to test send success
4. **Integration & testing**: Wire into existing dialog, add PyQt mocks

---

## Phase 1 Completion Summary

**Documents created**:
- ✅ `research.md` — Implementation references, no blockers
- ✅ `data-model.md` — Entities, state machines, validation
- ✅ `contracts/send-dialog-component.md` — UI component interface & testing contract
- ✅ `quickstart.md` — User journey documentation
- ✅ Agent context updated (`CLAUDE.md`)

**Constitution re-check**: ✅ Passed (no violations)

**Ready for Phase 2**: `/speckit.tasks` to generate implementation task list
