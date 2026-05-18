# Quickstart: Test Scenarios for Editor Workflow Improvements

**Feature**: `003-editor-workflow-improvements`  
**Created**: 2026-05-18  
**Purpose**: Rapid validation of all user stories without full feature build

---

## User Story 1: Persistent Document Folder

### Setup
1. Create test folder: `/tmp/sendmail-test/newsletters/`
2. Verify `config.yml` has empty `default_documents_path` for test profile

### Test Scenario 1.1: First Save Creates Memory
1. Open editor
2. File → Save As → Navigate to `/tmp/sendmail-test/newsletters/` → Save as `test-doc.md`
3. Close editor
4. Verify `config.yml`: `default_documents_path: /tmp/sendmail-test/newsletters`
5. Reopen editor
6. File → Save As → Verify dialog opens in `/tmp/sendmail-test/newsletters/` ✅

### Test Scenario 1.2: Missing Folder Fallback
1. Delete `/tmp/sendmail-test/newsletters/`
2. Restart editor
3. Verify no error; editor loads normally
4. File → Save As → Verify dialog opens in OS default (Documents/home) ✅

### Test Scenario 1.3: Path Persistence Across Profiles
1. Select profile A, save file to `/path/a/`
2. Select profile B, save file to `/path/b/`
3. Switch back to profile A
4. File → Save As → Verify opens in `/path/a/` ✅

**Acceptance**: Save As remembers folder per profile without navigation

---

## User Story 2: Responsive Filter Editing

### Setup
1. Open Send Mailing dialog
2. Select profile with sample data

### Test Scenario 2.1: No Typing Lag
1. Click filter field
2. Type rapidly: `email: is not empty AND region: equals NY AND...` (10+ words)
3. Verify all characters appear immediately, no stuttering ✅
4. Wait 200ms, verify validation feedback appears after pause

### Test Scenario 2.2: Validation Non-Intrusive
1. Type filter expression slowly
2. Verify validation doesn't interrupt next keystroke
3. Continue typing after pause without re-entering characters ✅

### Test Scenario 2.3: Debounce Timing
1. Type first condition, pause 100ms
2. Type second condition immediately
3. Verify only one validation run (not two) ✅

**Acceptance**: <50ms perceived latency during typing, validation silent until pause

---

## User Story 3: Send Mailing Window Clarity

### Test Scenario 3.1: Window Title
1. Open Send Mailing dialog (File → Send)
2. Verify window title bar displays: "Send Mailing" (not "Send Newsletter") ✅

### Test Scenario 3.2: User Comprehension
1. Show title "Send Mailing" to 5 test users
2. Ask: "What is this dialog for?"
3. Verify ≥4 of 5 correctly identify as mailing/newsletter sending ✅

**Acceptance**: Title unambiguously indicates mailing operations

---

## User Story 4: Simplified Send Mailing Dialog

### Test Scenario 4.1: Checkbox Removal
1. Open Send Mailing dialog
2. Look at Flags section
3. Count checkboxes:
   - ✅ Test
   - ✅ Verbose
   - ✅ Do not send
   - ❌ Selected (should NOT exist)
4. Verify count = 3 ✅

### Test Scenario 4.2: Layout Integrity
1. Open Send Mailing dialog
2. Verify no visual gaps or misalignment in Flags section
3. Dialog layout remains clean and balanced ✅

**Acceptance**: Flags section shows exactly 3 checkboxes, no layout regressions

---

## User Story 5: Template Safety Enforcement

### Setup
1. Create test template: `data/sample-template.html`
2. Create data: `data/sample-draft.html` (non-template)

### Test Scenario 5.1: Template Read-Only Detection
1. File → Open → Select `sample-template.html`
2. Verify title bar shows: "[Read-Only Template]" ✅
3. File → Open → Select `sample-draft.html`
4. Verify title bar shows normal name (no template indicator) ✅

### Test Scenario 5.2: Save Disabled for Templates
1. Open `sample-template.html`
2. Make edits
3. Try Ctrl+S or File → Save
4. Verify Save As dialog opens (NOT direct save) ✅

### Test Scenario 5.3: Save As Preserves Original
1. Open `sample-template.html`
2. Edit content
3. File → Save As → Save as `sample-draft.html`
4. Verify:
   - `sample-draft.html` created with edits ✅
   - `sample-template.html` unchanged (original content intact) ✅

**Acceptance**: Templates open read-only, Save disabled, Save As creates copy safely

---

## Integration Test: All Stories Together

### Test Scenario 6.1: Config Atomicity
1. Open 3 profiles in rapid succession
2. Save files to different folders for each profile
3. Trigger config write error (e.g., disk full simulation)
4. Verify:
   - No config corruption ✅
   - Previous valid state preserved ✅
   - Error logged (no user-facing crash) ✅

### Test Scenario 6.2: End-to-End Workflow
1. Create 2 profiles with different save folders
2. Profile A: Save template file → Read-only enforced
3. Profile B: Open file → Path remembered
4. Switch to Profile A, open Send Mailing → Filter typing responsive
5. Verify all 5 user stories working without conflicts ✅

---

## Success Metrics

| Story | Test | Pass/Fail | Notes |
|-------|------|-----------|-------|
| US1 | Path persistence | TBD | Folder memory per profile |
| US1 | Fallback to OS default | TBD | No crashes on missing path |
| US2 | Typing latency | TBD | <50ms perceived delay |
| US2 | Validation non-intrusive | TBD | Pauses typing flow |
| US3 | Title clarity | TBD | "Send Mailing" visible |
| US4 | Checkbox count | TBD | Exactly 3 flags |
| US5 | Template detection | TBD | Read-only indicator present |
| US5 | Save As safety | TBD | Original unchanged |

---

## Notes

- All scenarios testable manually without instrumentation
- Each story can be validated independently
- Integration test confirms no regressions
- Ready for user acceptance testing post-implementation
