# Implementation Plan: Editor Profile & Clipboard Enhancements

**Branch**: `005-editor-profile-clipboard` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-editor-profile-clipboard/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Three enhancements to the WYSIWYG editor (editor.py):
1. **Profile selector in main window**: Add dropdown to select email profiles from config.yml; auto-load default_document_path to file browser
2. **Preserve hyperlinks on copy/paste**: Support rich clipboard operations that maintain HTML link markup
3. **Auto-linkify URLs on paste**: Detect plain-text URLs in pasted content and convert to clickable links

Technical approach: Extend PyQt6 main window UI with profile dropdown + config loader; hook into Quill.js paste event handlers via QWebChannel bridge to process clipboard content for link preservation and URL detection.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: PyQt6 (≥6.7.0), PyQt6-WebEngine (≥6.7.0), Quill.js v2 (via HTML5), pyyaml, google-api-python-client  
**Storage**: YAML (config.yml), Markdown/HTML files (documents)  
**Testing**: pytest + mock Qt (no headless GUI), mypy, ruff  
**Target Platform**: macOS/Windows/Linux (via PyInstaller)  
**Project Type**: Desktop application  
**Performance Goals**: UI responsiveness <100ms for profile switch, paste operations <500ms  
**Constraints**: PyQt6 WebEngine must be available; config.yml must be readable; Quill.js paste event support required  
**Scale/Scope**: Single editor window, up to 50 profiles in config

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: Project constitution is template-only (not yet filled). Assuming standard Python/PyQt desktop app conventions. Key checks:
- ✓ Python 3.12+ maintained
- ✓ No new external API dependencies (uses existing google-api, gspread, etc.)
- ✓ UI changes isolated to editor.py (no sendMail.py changes required)
- ✓ Config.yml schema compatibility preserved
- ✓ WYSIWYG editor remains standalone (not imported by CLI)

## Project Structure

### Documentation (this feature)

```text
specs/005-editor-profile-clipboard/
├── spec.md              # Feature specification (user stories, requirements)
├── plan.md              # This file - implementation plan
├── research.md          # Phase 0 - design decisions and unknowns resolved
├── data-model.md        # Phase 1 - entity definitions and state machines
├── quickstart.md        # Phase 1 - step-by-step implementation guide
├── contracts/           # Phase 1 - interface contracts
│   ├── config-profile-schema.md    # Config.yml profile structure
│   ├── qwebchannel-bridge.md       # JS ↔ Python communication
│   └── document-format.md          # Markdown/HTML document format
├── checklists/
│   └── requirements.md   # Quality checklist (all items pass)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── editor.py            # MODIFIED: Add profile selector, clipboard processing
│   ├── ConfigLoader         # NEW: Load profiles from config.yml
│   ├── ClipboardProcessor   # NEW: Analyze clipboard content
│   ├── ClipboardOperation   # NEW: Clipboard data model
│   ├── EditorPasteHandler   # NEW: Handle paste events
│   └── EditorWidget         # MODIFIED: Add profile dropdown + session persistence
├── sendMail.py          # NO CHANGES (profile selector is editor-only)
├── googleDriveLib.py    # NO CHANGES
└── config.yml           # NO CHANGES (backward compatible)

editor_assets/
├── editor.html          # MODIFIED: Add paste event analysis, URL detection
├── quill.js             # NO CHANGES
├── quill.snow.css       # NO CHANGES
└── qwebchannel.js       # NO CHANGES

.claude/
└── editor-session.json  # NEW: Persist active profile across sessions

tests/
├── test_config_loader.py           # NEW
├── test_clipboard_processor.py      # NEW
├── test_editor_paste_handler.py     # NEW
├── test_editor_profile_selector.py  # NEW
└── existing tests/                  # NO CHANGES
```

**Structure Decision**: Single-project desktop app structure. No new packages or modules beyond src/editor.py extensions. All changes localized to editor.py and editor_assets/editor.html. Config.yml and document format backward compatible - no schema changes required.

## Complexity Tracking

**None**: Feature respects existing architecture constraints. No new dependencies, no breaking changes, no additional complexity required.

---

## Phase 0 Complete ✓

**research.md**: All design decisions finalized
- Profile selector: QComboBox in toolbar, session persistence via JSON
- Hyperlink preservation: Leverage Quill native HTML paste
- URL auto-linkify: Regex pattern for http(s)/ftp, applied to plain text only
- No unknowns remaining

---

## Phase 1 Complete ✓

**data-model.md**: Four entities defined
- Profile: Config profiles with optional default_document_path
- EditorSession: Active profile + document state
- ClipboardOperation: Paste event data with URL detection results
- Document: Markdown/HTML roundtrip with frontmatter

**Contracts Defined**:
- `config-profile-schema.md`: Profile structure (backward compatible)
- `qwebchannel-bridge.md`: JS ↔ Python signals for clipboard/profile events
- `document-format.md`: Markdown/HTML export with link preservation guarantee

**quickstart.md**: Implementation guide with code examples and testing checklist

---

## Next Phase: /speckit.tasks

Run `/speckit.tasks` to generate actionable implementation tasks (Phase 2).
Task generation will produce:
- Structured task list with dependencies
- Code snippets for quick reference
- Test cases per feature
- Integration test scenarios
