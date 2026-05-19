# Tasks: Send Dialog Improvements

**Input**: Design documents from `/specs/006-send-dialog-improvements/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks grouped by user story for independent implementation. All three stories (US1, US2, US3) are P1 priority and can be implemented in parallel.

**Tests**: No test tasks included (existing PyQt6 mocking patterns in tests/ sufficient for manual verification).

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story (US1, US2, US3)
- **File paths**: Exact locations in repository

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify project dependencies and environment

- [x] T001 Verify BeautifulSoup4 in requirements.txt (core dependency for HTML parsing)

---

## Phase 2: Foundational (Dialog Infrastructure)

**Purpose**: Prepare `_SendDialog` class for new features

**⚠️ CRITICAL**: Must complete before user story work begins

- [x] T002 Add instance variables to `_SendDialog.__init__()` in src/editor.py: `_test_sent: bool`, `attachments: list[str]`
- [x] T003 Create helper method `_extract_subject_from_html(html_path: str) -> str` in src/editor.py
- [x] T004 Connect test checkbox toggle signal to handler in `_SendDialog.__init__()` (src/editor.py)

**Checkpoint**: Dialog infrastructure ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Auto-populate Subject Line (Priority: P1) 🎯

**Goal**: Subject field auto-populates from HTML `<h1>` heading or filename, truncated to 50 characters

**Independent Test**: 
1. Open HTML file with `<h1>Title</h1>` in editor
2. Click Menu → Send
3. Verify Subject field shows "Title" (or truncated if >50 chars)
4. Test with HTML without `<h1>`: verify filename appears as subject

### Implementation for User Story 1

- [x] T005 [P] [US1] Implement `_extract_subject_from_html()` to parse HTML with BeautifulSoup, extract first `<h1>` text in src/editor.py
- [x] T006 [US1] Add `<h1>` text extraction with HTML tag stripping (BeautifulSoup.get_text()) in `_extract_subject_from_html()` (src/editor.py)
- [x] T007 [US1] Add filename fallback (Path.stem) if no `<h1>` found in `_extract_subject_from_html()` (src/editor.py)
- [x] T008 [US1] Add 50-character truncation logic in `_extract_subject_from_html()` (src/editor.py)
- [x] T009 [US1] Call `_extract_subject_from_html()` in `_SendDialog.__init__()` to populate subject_input field (src/editor.py)
- [x] T010 [US1] Test subject extraction with sample HTML files (manual: with/without `<h1>`, long titles, special chars)

**Checkpoint**: User Story 1 complete and independently testable

---

## Phase 4: User Story 2 - Attach Multiple Files (Priority: P1)

**Goal**: Add/remove file attachments in Send Mailing dialog, displayed in list widget positioned right of HTML input

**Independent Test**:
1. Open Send Mailing dialog
2. Click "Add File(s)" button
3. Select one or more files in picker
4. Verify files appear in list below HTML input
5. Click delete button next to a file
6. Verify file removed from list

### Implementation for User Story 2

- [x] T011 [P] [US2] Create attachment list widget UI in `_SendDialog.__init__()` (QListWidget or custom widget) in src/editor.py
- [x] T012 [US2] Add "Add File(s)" button with file picker (QFileDialog.getOpenFileNames()) in src/editor.py
- [x] T013 [US2] Implement file picker callback to add selected files to attachments list in src/editor.py
- [x] T014 [US2] Add delete button per list item and implement deletion handler in src/editor.py
- [x] T015 [US2] Implement clear attachments logic (reset to empty list) on dialog close/reopen in src/editor.py
- [x] T016 [US2] Integrate attachments list with `build_args()` method to pass files to sendMail CLI in src/editor.py
- [x] T017 [US2] Test attachment add/remove workflow with multiple files (manual: verify list updates, delete works, list clears on dialog reopen)

**Checkpoint**: User Story 2 complete and independently testable

---

## Phase 5: User Story 3 - Test Mode Enforcement (Priority: P1)

**Goal**: Test checkbox locked until test email sent, unlocks after success, resets on dialog reopen

**Independent Test**:
1. Open Send Mailing dialog
2. Verify Test checkbox is checked and cannot be unchecked
3. Send test email (test mode on)
4. Verify after successful test, Test checkbox becomes unlocked
5. Uncheck Test checkbox
6. Send to full list
7. Close and reopen dialog: verify Test checkbox is reset to checked (locked)

### Implementation for User Story 3

- [x] T018 [US3] Initialize `_test_sent = False` in `_SendDialog.__init__()` (src/editor.py)
- [x] T019 [US3] Set Test checkbox to checked by default in `_SendDialog.__init__()` (src/editor.py)
- [x] T020 [US3] Implement `_on_test_mode_toggled()` handler to block unchecking if `_test_sent == False` in src/editor.py
- [x] T021 [US3] Implement signal blocking logic: if user tries to uncheck and `_test_sent == False`, auto-recheck in src/editor.py
- [x] T022 [US3] Implement `_unlock_test_mode()` method to set `_test_sent = True` and enable test checkbox in src/editor.py
- [x] T023 [US3] Modify `_menu_send()` in EditorWindow to detect "OK_TEST" in sendMail result and call `dialog._unlock_test_mode()` in src/editor.py
- [x] T024 [US3] Test test mode state machine: verify locked → send test → unlocked → reset on reopen (manual)

**Checkpoint**: User Story 3 complete and independently testable

---

## Phase 6: Integration & Final Testing

**Purpose**: Verify all three stories work together

- [x] T025 [P] Integration test: Open dialog → populate subject → add attachments → verify test locked → send test → unlock → send bulk
- [x] T026 [P] Verify sendMail CLI receives all three features correctly in build_args() in src/editor.py
- [x] T027 Edge case testing: Multiple `<h1>` tags (use first), HTML formatting in `<h1>` (strip tags), long filenames, special characters, empty attachments list

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final refinement and validation

- [x] T028 Documentation: Update CLAUDE.md with new _SendDialog behavior and features
- [x] T029 Code review: Ensure all code follows project conventions (snake_case, type hints, no `type: ignore`)
- [x] T030 Run existing test suite to ensure no regressions: `pytest tests/ -v`
- [x] T031 Validate quickstart.md workflow matches implemented behavior
- [x] T032 Manual end-to-end test: newsletter creation → send with all three features

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase
  - Can proceed in parallel (different implementations, same file)
  - Or sequentially if preferred
- **Integration (Phase 6)**: Depends on all user stories
- **Polish (Phase 7)**: Depends on integration phase

### User Story Dependencies

- **User Story 1 (Subject)**: No dependencies on US2 or US3 - can be independent
- **User Story 2 (Attachments)**: No dependencies on US1 or US3 - can be independent
- **User Story 3 (Test Mode)**: No dependencies on US1 or US2 - can be independent

### Within Each User Story

- Helper methods before UI wiring
- UI controls before signal handlers
- Signal handlers before integration

### Parallel Opportunities

**Phase 1**: Single task, no parallelization needed

**Phase 2**: Tasks T002, T003, T004 can run in parallel (different methods/handlers)

**Phase 3 (US1)**:
- Tasks T005-T008: `_extract_subject_from_html()` implementation (sequential within method)
- Task T009: Wiring to dialog
- Task T010: Testing

**Phase 4 (US2)**:
- Tasks T011-T016: UI widget creation, file picker, delete handler (can parallelize widget creation + picker separately)
- Task T017: Testing

**Phase 5 (US3)**:
- Tasks T018-T024: State management, toggle handler, unlock logic (can parallelize signal handler setup + unlock method)

**Phase 6**: T025-T027 can parallelize (different test scenarios)

**Phase 7**: T028-T032 can parallelize (docs + code review + test suite, then end-to-end)

---

## Parallel Example: User Stories After Foundational

Once Phase 2 (Foundational) is complete:

```
Team A: Execute Phase 3 (US1)      [Independent]
Team B: Execute Phase 4 (US2)      [Independent]
Team C: Execute Phase 5 (US3)      [Independent]
Sync:   When all 3 done, Phase 6 Integration
```

All three can work simultaneously on src/editor.py without conflicts (different methods, different UI components).

---

## Implementation Strategy

### MVP First (All Three Stories - They're All P1)

1. Complete Phase 1: Setup (verify deps)
2. Complete Phase 2: Foundational (dialog infrastructure)
3. Execute Phases 3, 4, 5 in parallel or sequence (all are MVP)
4. Complete Phase 6: Integration test
5. Validate with quickstart.md workflow
6. Ready to merge

### Single Developer Approach

1. Phase 1: Setup (immediate)
2. Phase 2: Foundational (required before US work)
3. Phase 3: US1 (Subject) → T005-T010
4. Phase 4: US2 (Attachments) → T011-T017
5. Phase 5: US3 (Test Mode) → T018-T024
6. Phase 6: Integration → T025-T027
7. Phase 7: Polish → T028-T032

### Multi-Developer Approach

1. Team completes Phase 1 + 2 together
2. Once Foundational done:
   - Dev A: Execute Phase 3 (US1) + testing
   - Dev B: Execute Phase 4 (US2) + testing
   - Dev C: Execute Phase 5 (US3) + testing
3. Team syncs: Phase 6 integration
4. Team reviews: Phase 7 polish

---

## Notes

- All tasks in Phases 3, 4, 5 modify src/editor.py but are independent (different methods/features)
- No new files needed - all work within existing _SendDialog class
- Tests are manual (existing PyQt6 mock patterns sufficient) - no automated test tasks
- Each user story can be tested independently by opening the dialog and verifying behavior
- Commit after each Phase completion (Setup → Foundation → US1 → US2 → US3 → Integration → Polish)
- Avoid: merging stories in wrong priority order, mixing test mode with subject/attachment logic
- Each checkpoint validates story works independently before moving to next

---

## Task Count Summary

- **Total Tasks**: 32
- **Setup Phase**: 1 task
- **Foundational Phase**: 3 tasks
- **User Story 1 (Subject)**: 6 tasks
- **User Story 2 (Attachments)**: 7 tasks
- **User Story 3 (Test Mode)**: 7 tasks
- **Integration Phase**: 3 tasks
- **Polish Phase**: 5 tasks

**Parallel opportunities**: Phase 2 (3 tasks), Phase 3-5 (20 tasks across 3 stories), Phase 6 (3 tasks), Phase 7 (5 tasks)

**MVP scope**: All three user stories (Phase 1-5) = 26 tasks
