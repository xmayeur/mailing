# Phase 0: Research & Design Decisions

**Feature**: Editor Profile & Clipboard Enhancements  
**Branch**: `005-editor-profile-clipboard`  
**Date**: 2026-05-19

## Decisions Made

### 1. Profile Selector Implementation

**Decision**: Store selected profile in persistent editor session file (e.g., `.claude/editor-session.json`)

**Rationale**: 
- PyQt6 QSettings provides cross-platform registry/config persistence
- Simple JSON file allows manual inspection and testing
- Avoids modifying config.yml structure (immutable design principle)

**Alternatives Considered**:
- Store in config.yml: Would require careful YAML formatting to preserve comments/structure
- QSettings registry: Platform-specific, harder to debug/test

### 2. Clipboard Link Preservation

**Decision**: Leverage Quill.js native rich paste support via HTML clipboard format

**Rationale**:
- Quill v2 (already in use) handles HTML → Delta conversion automatically
- QMimeData.html() provides direct HTML clipboard access in PyQt6
- No custom HTML parsing needed - Quill's paste event handles markup preservation

**Alternatives Considered**:
- Custom regex link detection: Would miss malformed links, harder to maintain
- Plain text fallback only: Loses link semantics that browsers/editors already copy

### 3. URL Auto-Linkification

**Decision**: Detect URLs in pasted plain text only; use regex pattern `https?://[^\s<>\"{}|\\^`\[\]]*` and similar for ftp://

**Rationale**:
- Regex sufficient for standard URLs (http, https, ftp schemes)
- Apply ONLY to plain-text pastes (not rich HTML that already has links)
- Avoid double-conversion: check if content is already markdown/HTML link syntax before applying

**Alternatives Considered**:
- Full URI RFC 3986 regex: Overkill, rarely encountered in practice
- JavaScript-side detection: Already handling in Quill via QWebChannel, keep centralized

### 4. Config Profile Loading

**Decision**: Read config.yml at editor startup; parse profiles list and extract `default_document_path` field; store in memory dict with profile name as key

**Rationale**:
- config.yml already in use by sendMail.py, format is stable
- No database needed - YAML parsing via `yaml.safe_load()` is sufficient
- default_document_path is optional field (graceful degradation if missing)

**Alternatives Considered**:
- Dynamic config reload on profile select: Unnecessary, profiles static during session
- Config validation schema: Would require schema versioning; YAML schema separate concern

### 5. UI Component: Profile Dropdown

**Decision**: Add QComboBox to editor main window toolbar (horizontal layout); populate from config profiles on startup

**Rationale**:
- Minimal UI footprint (single combo box)
- QComboBox provides dropdown UX users expect
- Toolbar consistent with other editor controls
- Connected to slot that updates active profile and file browser path

**Alternatives Considered**:
- Menu item (File → Select Profile): Less discoverable, buried deeper
- Dialog window: Too heavy for frequent profile switching

## Technical Feasibility

✓ **Config parsing**: yaml module already in pyproject.toml  
✓ **Clipboard access**: PyQt6.QtGui.QClipboard available  
✓ **Rich paste support**: Quill v2 handles HTML → Delta via paste event  
✓ **Session persistence**: QSettings cross-platform, or JSON in .claude/  
✓ **URL detection**: Standard regex patterns, tested in production systems  

## Unknowns Resolved

- **Quill.js paste event access**: Via QWebChannel JS bridge in editor_assets/editor.html. Existing `qtBridge.pasteDetected()` slot can be extended to include clipboard content analysis.
- **Config.yml default_document_path presence**: Assumed optional field; handled gracefully with fallback to None or last known directory.
- **Profile persistence location**: Will use Python's `configparser` or JSON in `.claude/editor-session.json` to avoid config.yml conflicts.

## Implementation Readiness

All decisions are reversible and low-risk:
- Profile selector is UI-only; no data model changes
- Clipboard processing uses standard libraries (no new dependencies)
- Quill.js integration leverages existing QWebChannel bridge
- Config.yml remains immutable

**Ready for Phase 1: Design & Contracts**
