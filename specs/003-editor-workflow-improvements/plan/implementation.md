# Implementation Plan: Editor Workflow Improvements

**Feature**: `003-editor-workflow-improvements`  
**Created**: 2026-05-18  
**Status**: Ready for Implementation

---

## Overview

This plan breaks down the editor workflow improvements into implementable phases, addressing config persistence, UI responsiveness, dialog renaming, checkbox removal, and template safety.

### Success Metrics

- Config persistence reduces save navigation time by 50%
- Filter field debounce latency <50ms
- Window renaming provides immediate clarity
- Template read-only protection prevents accidental modifications

---

## Phase 1: Configuration & Persistence (Priority: P1)

### 1.1 Extend Config Schema

**Objective**: Add `default_documents_path` key to config file structure

**Tasks**:
- [ ] Update config.yml YAML schema to include optional `default_documents_path` key (profile-level or global)
- [ ] Document default location per OS (Windows: `%USERPROFILE%\Documents`, macOS/Linux: `~`)
- [ ] Update `_ConfigDialog` to display and edit `default_documents_path` in Settings dialog

**Acceptance**:
- Config file can be loaded/saved with the new key
- Settings dialog allows editing the default documents path
- Path validation occurs on save (non-existent paths do not block save, but are logged)

**Estimate**: 3-4 hours

---

### 1.2 Implement Path Persistence in Editor

**Objective**: Read, validate, and update document folder path on startup and file operations

**Tasks**:
- [ ] In `EditorWindow.__init__()`, load `default_documents_path` from config; fall back to OS default
- [ ] Validate loaded path exists; if not, use OS default (log warning)
- [ ] Update `_save_as()` to restore file browser to the stored path
- [ ] On successful save, update `default_documents_path` in config with the save directory
- [ ] On successful open, update `default_documents_path` in config with the file's directory

**Acceptance**:
- Editor starts with correct default folder
- Save As dialog opens in the remembered folder
- After save, folder is updated in config
- After open, folder is updated in config
- Invalid paths do not crash the editor

**Estimate**: 4-5 hours

---

## Phase 2: Filter Field Responsiveness (Priority: P1)

### 2.1 Analyze & Fix Debounce Timing

**Objective**: Eliminate lag in filter text field by adjusting debounce timeout

**Tasks**:
- [ ] Locate debounce timer initialization in `_SendDialog._validation_timer`
- [ ] Analyze current timeout value (currently 200ms per code review)
- [ ] Reduce timeout to <50ms or implement more granular validation (e.g., validate only on non-typing intervals)
- [ ] Test: Type rapidly in filter field and measure perceived latency
- [ ] Consider: Separate validation display from typing interrupt (show validation feedback after typing pauses, not during)

**Acceptance**:
- User can type a full filter expression without perceiving lag
- Validation feedback appears <100ms after typing stops
- No characters are dropped or delayed during rapid typing
- User testing confirms improved responsiveness

**Estimate**: 2-3 hours

---

## Phase 3: UI Clarity & Simplification (Priority: P2)

### 3.1 Rename Send Newsletter Dialog

**Objective**: Change window title from "Send Newsletter" to "Send Mailing"

**Tasks**:
- [ ] In `_SendDialog.__init__()`, change `self.setWindowTitle("Send Newsletter")` to `self.setWindowTitle("Send Mailing")`
- [ ] Update any documentation that references the old dialog name
- [ ] Verify no other code paths reference the old title for testing/automation purposes

**Acceptance**:
- Dialog title displays "Send Mailing" when opened
- No internal references to old title remain in codebase

**Estimate**: 0.5-1 hour

---

### 3.2 Remove Selected Only Checkbox

**Objective**: Simplify Flags section by removing the rarely-used "Selected only" option

**Tasks**:
- [ ] In `_SendDialog.__init__()`, locate the `self.selected_check` widget initialization
- [ ] Remove the checkbox from the Flags row layout
- [ ] Remove the corresponding `self.selected_check.setChecked()` call in `_load_profile_defaults()`
- [ ] Update `build_args()` to handle removal gracefully (default to False or omit)
- [ ] Check for any other code that reads `namespace.selected` and ensure it handles absence

**Acceptance**:
- "Selected only" checkbox does not appear in Flags section
- Dialog renders without visual gaps or layout issues
- Flags section shows exactly 3 checkboxes (Test, Verbose, Do not send)

**Estimate**: 1-2 hours

---

## Phase 4: Template Safety (Priority: P3)

### 4.1 Detect & Open Templates Read-Only

**Objective**: Identify template files and enforce read-only mode

**Tasks**:
- [ ] Add template detection logic in `EditorWindow.open_file()`: check if filename contains `.template` or matches `template.*`
- [ ] When template detected, set internal flag `self._is_template = True`
- [ ] In `EditorWindow._load_editor_page()`, pass template flag to editor and apply read-only CSS styling
- [ ] Disable Save action (Ctrl+S, File → Save menu) when `_is_template == True`; Save As remains enabled
- [ ] Update title bar to indicate read-only status (e.g., "[Read-Only Template]")

**Acceptance**:
- Template files open with visual read-only indicator
- Save (Ctrl+S) is disabled for templates
- Save As works normally, allowing template-based workflows
- User can make edits in memory without saving to the template

**Estimate**: 3-4 hours

---

## Phase 5: Integration & Testing (Priority: P1)

### 5.1 End-to-End Testing

**Objective**: Validate all improvements work together without side effects

**Tasks**:
- [ ] Test config path persistence across editor restarts
- [ ] Test filter field responsiveness with profile switching
- [ ] Test template open-as-read-only workflow
- [ ] Test window title rename in multi-profile scenarios
- [ ] Test removed checkbox in all flag states
- [ ] Test edge cases: missing config, corrupted path, non-existent template

**Acceptance**:
- All user stories pass acceptance scenarios
- No regressions in existing functionality
- Edge cases handled gracefully

**Estimate**: 3-4 hours

---

## Implementation Order

**Week 1**:
1. Phase 1.1: Config schema extension
2. Phase 1.2: Path persistence implementation
3. Phase 2.1: Debounce responsiveness fix

**Week 2**:
4. Phase 3: UI clarity (rename dialog, remove checkbox)
5. Phase 4: Template safety
6. Phase 5: Integration & testing

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Config file corruption on path update | High | Add file locking, validation, rollback on error |
| Debounce change affects other validations | Medium | Test all validator-dependent fields after change |
| Template detection too broad | Medium | Use precise regex for template filename matching |
| Path persistence breaks on network drives | Medium | Catch exceptions, fall back to OS default, log |

---

## Testing Checklist

- [ ] Config path persists across sessions
- [ ] Invalid paths don't crash editor
- [ ] Filter field latency <50ms during typing
- [ ] Window title shows "Send Mailing"
- [ ] Selected checkbox removed from UI
- [ ] Template files open read-only
- [ ] Save As works for templates
- [ ] All scenarios from spec pass acceptance tests
- [ ] No regressions in existing features

---

## Deliverables

1. Updated config.yml with `default_documents_path` key
2. Modified `EditorWindow` class with path persistence logic
3. Optimized debounce timeout in `_SendDialog`
4. Renamed dialog title and removed selected checkbox
5. Template detection and read-only enforcement in editor
6. Test coverage for all new functionality
7. Updated documentation (CLAUDE.md, user guides)

