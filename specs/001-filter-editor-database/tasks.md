# Tasks: Filter Editor with Database Preview in Send Newsletter Window

**Input**: Design documents from `/specs/001-filter-editor-database/`
**Prerequisites**: plan.md (complete), spec.md (complete)

**Organization**: Tasks grouped by user story to enable independent implementation of each story. Tests included where applicable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare foundation for filter editor feature

- [X] T001 Review existing SendNewsletterWindow class in src/editor.py to understand current structure and add-on points
- [X] T002 [P] Identify and review existing filter matching logic in src/sendMail.py (likely in email building functions)
- [X] T003 [P] Create filter validation helper module: src/filter_validator.py for YAML syntax and field validation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that MUST be complete before user story work begins

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement FilterValidator class in src/filter_validator.py with methods:
  - parse_yaml_filter(text) → dict | error
  - validate_field_names(filter_dict, database_schema) → list of missing fields
  - get_validation_status(text, schema) → {is_valid, syntax_errors, missing_fields}
- [X] T005 [P] Create DatabaseSchemaProvider class to extract field names from active database (CSV/Google Sheets headers)
- [X] T006 [P] Create FilterMatcher class to reuse/wrap existing filter matching logic from sendMail.py
- [X] T007 [P] Write unit tests for FilterValidator in tests/test_filter_validator.py
- [X] T008 [P] Write unit tests for DatabaseSchemaProvider in tests/test_schema_provider.py

**Checkpoint**: Foundation ready - user story implementation can now begin ✓

---

## Phase 3: User Story 1 - Load and Display Current Filter (Priority: P1) 🎯 MVP

**Goal**: Load filter from config.yml and display in editable text field when window opens

**Independent Test**: Launch editor, select profile, verify filter text field contains filter from config.yml for that profile

### Implementation for User Story 1

- [X] T009 [US1] Modify SendNewsletterWindow.__init__() in src/editor.py to add filter_text_edit widget (QPlainTextEdit)
- [X] T010 [US1] Add layout components: label "Filter (YAML)", text field, status indicator
- [X] T011 [US1] Implement load_current_filter(profile_name) method to read filter from config.yml
- [X] T012 [US1] Implement profile_changed() signal handler to update filter field when profile changes
- [X] T013 [US1] Add initial filter loading when SendNewsletterWindow initializes
- [X] T014 [P] [US1] Write unit tests for load_current_filter() in tests/test_editor.py
- [X] T015 [P] [US1] Write unit tests for profile switching behavior in tests/test_editor.py

**Checkpoint**: User Story 1 complete - filter displays and updates with profile selection ✓

---

## Phase 4: User Story 2 - Edit Filter and See Real-Time Validation (Priority: P1)

**Goal**: Validate filter syntax and field names in real-time as user edits

**Independent Test**: Edit filter text, observe validation messages without sending email

### Implementation for User Story 2

- [X] T016 [P] [US2] Add QPlainTextEdit.textChanged signal handler to trigger validation
- [X] T017 [US2] Implement validate_filter_on_change() with debouncing (200ms) to avoid excessive validation
- [X] T018 [US2] Call FilterValidator.get_validation_status() to check syntax and fields
- [X] T019 [US2] Update validation status indicator (green/red) based on validation result
- [X] T020 [US2] Display error messages in tooltip or status bar below filter field:
  - Syntax errors: "Line N: [error]"
  - Missing fields: "Fields not found: [field1, field2]"
- [X] T021 [US2] Add visual distinction: green border/icon for valid, red border/icon for invalid
- [X] T022 [P] [US2] Write unit tests for validation logic in tests/test_editor.py
- [X] T023 [P] [US2] Write integration tests for real-time validation feedback in tests/test_editor.py

**Checkpoint**: User Stories 1 & 2 complete - filter loads, user can edit, validation shows immediately ✓

---

## Phase 5: User Story 3 - Preview Filtered Database Records (Priority: P1)

**Goal**: Show scrollable list of filtered records and display count

**Independent Test**: Enter various filters, confirm record list updates and count matches expected result

### Implementation for User Story 3

- [X] T024 [US3] Add QTableWidget or QListWidget to SendNewsletterWindow for record preview below filter field
- [X] T025 [US3] Add "Matching Records" label with record count display (e.g., "5 records")
- [X] T026 [US3] Implement load_database_records() to load records from active profile's database source
- [X] T027 [US3] Implement filter_and_display_records() method:
  - Apply current filter using FilterMatcher
  - Display matching records in table/list
  - Update count display
- [X] T028 [US3] Connect validate_filter_on_change() to also trigger filter_and_display_records()
- [X] T029 [US3] Handle edge cases:
  - Empty database → "0 records"
  - Large datasets (1000+ records) → ensure scrollbar works, no lag
  - No filter/empty filter → display all records
- [X] T030 [P] [US3] Write unit tests for filter_and_display_records() in tests/test_editor.py
- [X] T031 [P] [US3] Write integration tests for record preview with various filters in tests/test_editor.py
- [X] T032 [P] [US3] Performance test: verify 1000+ record databases render without UI lag

**Checkpoint**: All P1 user stories complete - filter loads, validates, and shows record preview ✓

---

## Phase 6: User Story 4 - Apply Edited Filter for Session (Priority: P2)

**Goal**: Apply edited filter as session-active filter for email send operation

**Independent Test**: Apply filter, verify it is used for email send operation; close without applying, verify original filter remains active

### Implementation for User Story 4

- [ ] T033 [US4] Add "Apply Filter" button and "Cancel" button to SendNewsletterWindow
- [ ] T034 [US4] Implement apply_filter() slot to:
  - Validate filter one final time
  - Store edited filter as session-active filter (module-level or instance variable)
  - Signal SendNewsletterWindow that filter was updated
- [ ] T035 [US4] Implement cancel() slot to close dialog/reset filter to original (no side effects)
- [ ] T036 [US4] Modify email send operation in SendNewsletterWindow.send_email() to use session-active filter (if set) instead of config.yml filter
- [ ] T037 [US4] Pass session-active filter to sendMail.py email sending logic
- [ ] T038 [P] [US4] Write unit tests for apply_filter() behavior in tests/test_editor.py
- [ ] T039 [P] [US4] Write integration tests for session-active filter usage in email send in tests/test_editor.py

**Checkpoint**: All user stories complete - filter can be edited, previewed, and applied for session

---

## Phase 7: Edge Cases & Robustness

**Purpose**: Handle boundary conditions and error scenarios

- [ ] T040 [P] Handle database connection failures:
  - Show error in record preview area
  - Provide retry button
- [ ] T041 [P] Handle profile switching while filter editor is open:
  - Update filter field
  - Update record preview
  - Maintain any pending edits (ask user for confirmation if switching)
- [ ] T042 [P] Handle databases with zero records:
  - Display "0 records" count
  - Show empty list
- [ ] T043 [P] Handle Unicode/special characters in filter values:
  - Ensure no corruption or encoding errors
- [ ] T044 [P] Handle malformed YAML with missing colons/quotes:
  - Identify exact line number in error message

**Checkpoint**: Edge cases handled, system resilient to errors

---

## Phase 8: Polish & Testing

**Purpose**: Comprehensive testing and final QA

- [ ] T045 [P] Full manual QA:
  - Test all user stories end-to-end
  - Verify all edge cases
  - Check UI layout and responsiveness
- [ ] T046 [P] Performance testing:
  - Validation feedback latency (<200ms)
  - Record list rendering (<300ms)
  - Large database handling (1000+ records)
- [ ] T047 [P] Test with various databases:
  - CSV files (different encodings, large files)
  - Google Sheets (various data types)
- [ ] T048 [P] Test with various filter definitions:
  - Complex nested YAML (if supported)
  - Multiple conditions
  - Edge case field names (underscores, numbers, etc.)
- [ ] T049 Final code review and documentation

**Checkpoint**: Feature ready for merge - all tests passing, all edge cases handled, QA approved

---

## Dependency Map

```
Foundation Phase (T001-T008)
├─ User Story 1 (T009-T015)
│  └─ User Story 2 (T016-T023)
│     └─ User Story 3 (T024-T032)
│        └─ User Story 4 (T033-T039)
├─ Edge Cases (T040-T044) [parallel with US4]
└─ Polish (T045-T049) [after US4 complete]
```

**Critical Path**: T001-T008 → T009-T015 → T016-T023 → T024-T032 → T033-T039 → T045-T049

**Parallelizable**: Within each phase, [P] marked tasks can run in parallel.
