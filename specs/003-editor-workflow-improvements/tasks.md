# Task Breakdown: Editor Workflow Improvements

**Feature**: `003-editor-workflow-improvements`  
**Generated**: 2026-05-18  
**Total Tasks**: 24  
**Estimated Duration**: 21.5 hours (2-3 days)

---

## Implementation Strategy

This feature improves editor usability across 5 independent user stories (P1, P1, P2, P2, P3). Stories are designed to be independently implementable and testable, allowing parallel development.

**Suggested MVP Scope**: Complete User Story 1 (P1 - Persistent Document Folder) for immediate value. Add Story 2 (responsive filtering) in same sprint. Stories 3-5 are secondary improvements.

**Parallel Opportunities**:
- US1 (config persistence) and US2 (debounce fix) can be developed in parallel (different components)
- US3 (rename dialog) and US4 (remove checkbox) can be developed in parallel (both dialog changes)
- US5 (template safety) can start once core editor logic is stable

---

## Phase 1: Setup & Configuration Schema

**Objective**: Extend editor config to support path persistence

### Configuration Changes
- [x] T001 Update `config.yml` to add `default_documents_path` key documentation and example
- [x] T002 Extend `_ConfigDialog` class in `src/editor.py` with new configuration field for `default_documents_path` (bug fixed: use directory picker)
- [x] T003 Add validation in `_ConfigDialog._get_spinbox_default_value()` and `_load_yaml_block()` to handle path strings
- [x] T004 Update `_ConfigDialog._default_profile_data()` to include `"default_documents_path": ""` in defaults

**Acceptance Criteria**:
- Config file loads/saves with new key without errors
- Settings dialog displays editable field for default documents path
- Non-existent paths are logged as warnings but don't block save
- OS-appropriate defaults documented (Windows: Documents, macOS/Linux: home)

---

## Phase 2: User Story 1 - Persistent Document Folder (P1)

**Goal**: Newsletter creators can use a remembered document folder without navigating repeatedly

**Independent Test**: Save file to custom folder → close editor → reopen → verify Save As opens in same folder

### Implementation Tasks
- [x] T005 [US1] Load `default_documents_path` from config in `EditorWindow.__init__()` at line ~1891
- [x] T006 [US1] Implement OS-specific path defaults (Windows: `%USERPROFILE%\Documents`, macOS/Linux: `~`) in `EditorWindow._get_default_documents_path()`
- [x] T007 [US1] Add path validation in `EditorWindow._validate_documents_path()` to check existence and handle missing paths
- [x] T008 [US1] Update `EditorWindow._save_as()` to use remembered path as initial directory in `QFileDialog.getSaveFileName()`
- [x] T009 [US1] Update `EditorWindow._save()` to persist save directory to config after successful save
- [x] T010 [US1] Update `EditorWindow.open_file()` to persist file directory to config after successful open

### Testing Tasks (Optional)
- [x] T011 [US1] Test: Save file to `/tmp/test-folder`, close editor, reopen, verify Save As defaults to `/tmp/test-folder`
- [x] T012 [US1] Test: Delete remembered folder, restart editor, verify fallback to OS default without crash
- [x] T013 [US1] Test: Network path scenario (if available), verify handling of disconnected drives

**Acceptance Criteria**:
- Editor starts with correct default folder
- Save As dialog opens in remembered folder on subsequent launches
- Invalid/missing paths don't crash editor; fall back to OS default
- Path updates occur after every successful save/open
- Config writes are atomic (no corruption on error)

---

## Phase 3: User Story 2 - Responsive Filter Editing (P1)

**Goal**: Filter field typing is responsive without lag or validation interruption

**Independent Test**: Type rapidly in filter field at normal typing speed → all characters appear immediately → validation feedback appears after pausing

### Implementation Tasks
- [x] T014 [P] [US2] Locate debounce timer in `_SendDialog._on_filter_text_changed()` at line ~675
- [x] T015 [P] [US2] Analyze current debounce timeout value (expected 200ms) in `_validation_timer.start()`
- [x] T016 [US2] Reduce debounce timeout from 200ms to 50ms in `_SendDialog._on_filter_text_changed()` at line 675
- [x] T017 [US2] Implement debounce separation: delay validation display without blocking character input in `_SendDialog._run_filter_validation()`
- [x] T018 [US2] Update `_SendDialog._update_validation_ui()` to show feedback non-intrusively after user pauses typing
- [x] T019 [P] [US2] Test rapid typing: compose filter "email: is not empty" at normal speed, measure perceived latency
- [x] T020 [US2] Verify no characters are dropped or delayed during rapid input to filter field

**Testing Tasks (Optional)**
- [x] T021 [US2] Benchmark: Filter field typing latency before/after (target <50ms perceived delay)
- [x] T022 [US2] Test: Type filter expression with 5+ conditions rapidly, verify responsiveness maintained

**Acceptance Criteria**:
- User can type without perceiving lag or stuttering
- Validation feedback appears <100ms after typing stops
- No characters are dropped or delayed during rapid typing
- Typing flow is uninterrupted by validation checks

---

## Phase 4: User Story 3 - Send Mailing Window Clarity (P2)

**Goal**: Dialog title clearly indicates bulk mailing operations

**Independent Test**: Open Send Mailing dialog → verify window title reads "Send Mailing" (not "Send Newsletter")

### Implementation Tasks
- [x] T023 [P] [US3] Update `_SendDialog.__init__()` at line 372: change `setWindowTitle("Send Newsletter")` to `setWindowTitle("Send Mailing")`
- [x] T024 [P] [US3] Search codebase for any references to "Send Newsletter" dialog title and update or remove them
- [x] T025 [P] [US3] Update CLAUDE.md or user documentation that references old dialog name

**Acceptance Criteria**:
- Dialog window title displays "Send Mailing" when opened
- No internal code or documentation references old "Send Newsletter" title remain
- No regressions in dialog functionality

---

## Phase 5: User Story 4 - Simplified Send Mailing Dialog (P2)

**Goal**: UI is cleaner with only essential checkboxes (Test, Verbose, Do not send)

**Independent Test**: Open Send Mailing dialog → verify Flags section shows exactly 3 checkboxes (no "Selected" checkbox)

### Implementation Tasks
- [x] T026 [P] [US4] Locate `self.selected_check` initialization in `_SendDialog.__init__()` around line ~488-490
- [x] T027 [P] [US4] Remove `self.selected_check = QCheckBox(...)` widget initialization in Flags section
- [x] T028 [P] [US4] Remove `selected_check` from `flag_layout.addWidget()` in `_SendDialog.__init__()` around line ~490
- [x] T029 [P] [US4] Remove `self.selected_check.setChecked()` call from `_SendDialog._load_profile_defaults()` around line ~632
- [x] T030 [P] [US4] Update `_SendDialog.build_args()` to handle absence of selected field: either omit `namespace.selected` or default to `False`
- [x] T031 [P] [US4] Search for any code that reads `namespace.selected` and ensure it handles None/False gracefully

**Testing Tasks (Optional)**
- [x] T032 [US4] Test: Open Send Mailing dialog, count Flags section checkboxes (should be 3: Test, Verbose, Do not send)
- [x] T033 [US4] Test: Verify dialog layout has no visual gaps or misalignment after checkbox removal

**Acceptance Criteria**:
- "Selected only" checkbox does not appear in Flags section
- Flags section displays exactly 3 checkboxes
- Dialog layout is clean with no visual gaps
- No errors when building args without selected field

---

## Phase 6: User Story 5 - Template Safety Enforcement (P3)

**Goal**: Template files open in read-only mode, forcing Save As for safety

**Independent Test**: Open `template.html` → verify read-only indicator → try Ctrl+S → verify Save As opens instead

### Implementation Tasks
- [x] T034 [US5] Create `EditorWindow._is_template` boolean flag initialization in `EditorWindow.__init__()` at line ~1896
- [x] T035 [US5] Implement template detection in `EditorWindow.open_file()` at line ~1984: check if filename contains ".template" or matches "template.*"
- [x] T036 [US5] Set `self._is_template = True` when template file is detected in `EditorWindow.open_file()`
- [x] T037 [US5] Update `EditorWindow._update_title()` to append "[Read-Only Template]" to title when template is open
- [x] T038 [US5] Disable Save action in `EditorWindow._build_menus()` when `self._is_template` is True (line ~2333-2335)
- [x] T039 [US5] Keep Save As action enabled for templates; verify `_save_as()` creates new file without modifying template
- [x] T040 [US5] Apply read-only CSS styling to editor when template is open (pass flag to `_inject_initial_content()`)

### Testing Tasks (Optional)
- [x] T041 [US5] Test: Open `template.html`, verify title shows "[Read-Only Template]"
- [x] T042 [US5] Test: Try Ctrl+S on template, verify Save As dialog opens instead of direct save
- [x] T043 [US5] Test: Edit template, use Save As, verify original template is unchanged and new file is created

**Acceptance Criteria**:
- Template files open with read-only visual indicator in title bar
- Save (Ctrl+S, File → Save) is disabled for templates
- Save As remains enabled and allows creating copy
- User can make edits in memory and save as new file without modifying template
- Original template is never overwritten

---

## Phase 7: Integration & End-to-End Testing

**Objective**: All features work together without side effects or regressions

### Functional Integration Tests
- [x] T044 [P] Execute User Story 1 acceptance tests: folder persistence across sessions
- [x] T045 [P] Execute User Story 2 acceptance tests: filter field responsiveness
- [x] T046 [P] Execute User Story 3 acceptance tests: window title clarity
- [x] T047 [P] Execute User Story 4 acceptance tests: simplified checkbox layout
- [x] T048 [P] Execute User Story 5 acceptance tests: template read-only enforcement

### Edge Case & Regression Testing
- [x] T049 Corrupted config file: verify editor loads with fallback defaults
- [x] T050 Missing config file: verify editor initializes config with defaults
- [x] T051 Very long or special-character paths: verify handling without crash
- [x] T052 Network drive paths: verify graceful fallback if network unavailable
- [x] T053 Template file deleted after open: verify editor handles missing file gracefully
- [x] T054 Profile switching while template open: verify template state is preserved
- [x] T055 Filter validation with complex YAML: verify debounce doesn't affect complex filters

### Regression Testing
- [x] T056 Save/open non-template files: verify normal behavior unaffected
- [x] T057 Edit regular (non-template) files: verify Save works normally
- [x] T058 Config dialog: verify all existing settings still editable
- [x] T059 Send Mailing send operation: verify all fields correctly passed to sendMail
- [x] T060 Database preview in Send Mailing: verify filters work with visual improvements
- [x] T061 Profile management: verify create/duplicate/delete profiles still work

### Test Coverage & Documentation
- [x] T062 Document template naming convention: files with ".template" or "template.*" open read-only
- [x] T063 Document config key: `default_documents_path` location and OS-specific defaults
- [x] T064 Update CLAUDE.md with new config options and editor behavior
- [x] T065 Update user guide with path persistence and template safety features

**Acceptance Criteria**:
- All user story acceptance tests pass
- No regressions in existing functionality
- Edge cases handled gracefully
- Documentation is current and accurate
- Feature is ready for release

---

## Dependencies & Execution Order

### Critical Path (Sequential)
1. **Phase 1** (Setup): Configuration schema changes (T001-T004) must complete first
2. **Phase 2** (US1): Path persistence depends on config schema from Phase 1
3. **Phases 3-6** (US2-US5): Can proceed in parallel once Phase 1 is complete

### Parallel Opportunities
- **Parallel A**: US2 (Filter debounce) development while US1 (Path persistence) in progress
- **Parallel B**: US3 (Rename dialog) + US4 (Remove checkbox) can be done simultaneously
- **Parallel C**: US5 (Template safety) can start once core editor changes are stable
- **Parallel D**: All testing can happen in parallel across user stories

### Dependency Graph
```
Phase 1 (Setup)
  ├─→ Phase 2 (US1: Path Persistence)
  ├─→ Phase 3 (US2: Filter Responsiveness) [parallel with US1]
  ├─→ Phase 4 (US3: Window Clarity) [parallel with US2]
  ├─→ Phase 5 (US4: Simplified Dialog) [parallel with US3]
  └─→ Phase 6 (US5: Template Safety) [parallel with US4]
       └─→ Phase 7 (Integration & Testing)
```

---

## Task Statistics

| Phase | Story | P# | Tasks | Hours | Dependencies |
|-------|-------|----|----|-------|-----|
| 1 | Setup | - | 4 | 3-4 | None |
| 2 | US1 | P1 | 6 | 5-7 | Phase 1 |
| 3 | US2 | P1 | 7 | 3-4 | Phase 1 |
| 4 | US3 | P2 | 3 | 1-1.5 | Phase 1 |
| 5 | US4 | P2 | 6 | 1.5-2 | Phase 1 |
| 6 | US5 | P3 | 7 | 4-5 | Phase 1 |
| 7 | Integration | - | 22 | 4-5 | Phases 2-6 |
| **Total** | **5 Stories** | **P1/P2/P3** | **24** | **21.5-28** | **Sequential/Parallel** |

---

## Success Criteria Summary

### User Story 1 (Persistent Document Folder)
- ✅ Editor remembers last save location
- ✅ Save As opens in remembered folder on next session
- ✅ Invalid paths fall back to OS default without errors
- ✅ Folder updates after every save/open

### User Story 2 (Responsive Filter Editing)
- ✅ Filter field typing has <50ms perceived latency
- ✅ Validation feedback appears after typing pauses
- ✅ No characters dropped or delayed
- ✅ Typing flow uninterrupted

### User Story 3 (Send Mailing Window Clarity)
- ✅ Dialog title displays "Send Mailing"
- ✅ No references to old "Send Newsletter" title remain

### User Story 4 (Simplified Dialog)
- ✅ "Selected only" checkbox removed from Flags
- ✅ Flags shows exactly 3 checkboxes
- ✅ Dialog layout is clean

### User Story 5 (Template Safety)
- ✅ Templates open read-only with visual indicator
- ✅ Save is disabled, Save As is enabled
- ✅ Original template never modified
- ✅ User can edit and save as new file

---

## Checklist Format Explanation

Each task follows the strict format:
```
- [ ] [TaskID] [Parallelizable?] [StoryLabel?] Description with exact file path
```

**Examples from this breakdown**:
- `- [x] T001 Update config.yml to add...` (Setup phase)
- `- [x] T005 [US1] Load default_documents_path...` (Story-specific)
- `- [ ] T014 [P] [US2] Locate debounce timer...` (Parallelizable & story-specific)
- `- [ ] T044 [P] Execute User Story 1 acceptance tests` (Parallelizable test)

---

## Notes

- **Test tasks are optional**: Only include if your team follows TDD or user explicitly requests them. This breakdown includes optional test tasks marked in Phase 7.
- **Parallel execution**: Tasks marked `[P]` can be developed simultaneously by different team members.
- **Story independence**: Each user story can be completed and tested independently; stories don't block each other.
- **MVP approach**: Start with US1 (P1) for immediate value, add US2 in same sprint, defer US3-US5 to follow-up release if time-constrained.

