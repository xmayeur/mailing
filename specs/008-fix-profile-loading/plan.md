# Implementation Plan: Fix Profile Loading and Configuration

**Branch**: `008-fix-profile-loading` | **Date**: 2026-05-21 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/008-fix-profile-loading/spec.md`

## Summary

Fix profile loading issues where selected email profile settings (SMTP, styling) are not being applied in editor.py and sendMail.py. Root cause: vault key for SMTP parameters not loaded when profile selected. Also replace debug-level log.info calls with log.debug for cleaner production logs, and add optional filter persistence to profile config.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: google-api-python-client, gspread, beautifulsoup4, markdown2, pillow, pyyaml, get-hc-secrets, PyQt6, PyQt6-WebEngine  
**Storage**: YAML config files (config.yml), Google Sheets, Google Drive, local filesystem  
**Testing**: pytest, pytest-cov, mypy, ruff, behave  
**Target Platform**: macOS, Linux, Windows (cross-platform CLI + GUI editor)  
**Project Type**: CLI tool with WYSIWYG GUI editor  
**Performance Goals**: Editor opens in <2s, profile loads in <500ms, SMTP connects within standard timeouts  
**Constraints**: Support multiple email backends (SMTP + Gmail API), handle vault integration (get-hc-secrets)  
**Scale/Scope**: ~3000 LOC existing, 5-10 email profiles typical, 100-10k subscribers per campaign

## Constitution Check

*GATE: Template-only (no enforced gates defined). No violations.*

## Project Structure

### Documentation (this feature)

```text
specs/008-fix-profile-loading/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command) - N/A (no unknowns)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command) - N/A (no external interfaces)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── sendMail.py          # MAIN: CLI entry, email logic, subscriber filtering
├── editor.py            # GUI: WYSIWYG editor with profile style loading
├── googleDriveLib.py    # Google Drive integration
├── schema_provider.py   # Database schema for subscriber filtering
├── schema_cache.py      # Caching layer
├── filter_matcher.py    # Filter logic
├── filter_validator.py  # Filter validation
└── visual_filter_builder.py # Filter UI

tests/
├── test_*.py            # Unit/integration tests
└── step_impl/           # Behave step definitions

config.yml              # Email profiles, SMTP, vault keys
editor_assets/          # Quill.js, HTML/CSS for editor GUI
data/                   # Templates, newsletters
```

**Changes for this feature**: 
- `sendMail.py`: Ensure vault key loaded when profile selected
- `editor.py`: Apply profile styling when opening files
- `config.yml`: Add optional filter persistence structure (Profile.filters)
- Tests: Add profile loading + SMTP configuration tests
- Logging: Replace debug-level log.info → log.debug across all modules

## Phase 0: Research

No unknowns in specification. All requirements are clear and technology stack is established:
- Vault integration: existing (get-hc-secrets)
- Profile config: existing (YAML in config.yml)
- Logging framework: existing (Python logging module)
- GUI framework: existing (PyQt6)

**Research artifacts**: None required.

## Phase 1: Design & Contracts

### Design Decisions

**Profile Loading Flow**:
1. User selects profile in sendMail.py or editor.py
2. Profile name → vault key lookup (e.g., "artscroises" → "mailconfig: artscroisesmailing")
3. get-hc-secrets retrieves SMTP host/port/auth from vault
4. SMTP parameters cached in profile object for session
5. Editor applies profile's HTML template/styling to document

**Logging Migration**:
- Scan all modules for log.info calls
- Identify which are diagnostic (debug-level) vs. operational (info-level)
- Replace diagnostic calls with log.debug
- Keep info-level for user-relevant events (send started, filters applied, etc.)

**Filter Persistence**:
- Extend Profile object with optional `filters` field
- User can request "save filters" → serialize to config.yml
- On profile load, restore saved filters to active state
- No UI for filter saving in this phase (P3 / "on request" = minimal implementation)
