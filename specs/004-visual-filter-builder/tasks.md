# Task List: Visual Filter Builder UI

**Feature**: 004-visual-filter-builder  
**Date**: 2026-05-18  
**Branch**: `004-visual-filter-builder`  
**Total Tasks**: 42 | **MVP Scope**: Phase 1-4 (17 tasks)

---

## Overview: Implementation Strategy

**MVP Approach** (Phases 1-4): Deliver US1 (visual table) + US4 (field selection) + foundational infrastructure. Enables users to see working filter builder immediately.

**Phase 2 Scope** (Phases 5-7): Complete P1 stories (US2 pre-fill, US5 operator selection) + P2 stories (US3 CRUD).

**Phase 3** (Phase 8): Refinement, error handling, optimization, documentation.

**Parallelization**: Phases 3-7 have independent UI components that can be built in parallel after foundational phase.

---

## Phase 1: Project Setup

Initialize project structure and dependencies (no external dependencies needed—using existing PyQt6/pyyaml).

- [x] T001 Create module structure: `src/visual_filter_builder.py` (empty file with module docstring)
- [x] T002 [P] Create test structure: `tests/unit/test_visual_filter_builder.py` (pytest boilerplate)
- [x] T003 [P] Create integration test file: `tests/integration/test_send_dialog_filter.py`
- [x] T004 [P] Create contract test file: `tests/contract/test_visual_filter_contract.py`
- [x] T005 Verify existing dependencies: PyQt6, pyyaml, gspread in pyproject.toml (should already exist)

---

## Phase 2: Foundational Classes

Build core data model and base widget infrastructure. **BLOCKING**: All user story phases depend on these.

### Data Classes

- [x] T006 Implement FilterRow dataclass in `src/visual_filter_builder.py`:
  - Fields: `field_name: str`, `operator: str`, `value: str | None`
  - __post_init__ validation (field + operator not empty)
  - Docstring with example

- [x] T007 Implement FilterTable class in `src/visual_filter_builder.py`:
  - Methods: `__init__`, `add_row()`, `delete_row()`, `update_row()`, `to_dict()`, `from_dict()`
  - Docstring per method
  - Invariant: all rows are valid FilterRow instances

- [x] T008 Implement DatabaseSchemaInfo class in `src/visual_filter_builder.py`:
  - Fields: `field_names: list[str]`, `field_types: dict[str, str]`
  - Methods: `get_field_type()`, `get_operators_for_field()`
  - Default all fields to "text" type (per research.md R002)

- [x] T009 [P] Create operator categorization in `src/visual_filter_builder.py`:
  - Define `OPERATOR_LABELS` dict (user-friendly names → canonical operators)
  - Define `OPERATORS_FOR_TYPE` dict (field type → applicable operators)
  - Reference research.md findings for operator grouping

- [x] T010 Unit tests for data classes in `tests/unit/test_visual_filter_builder.py`:
  - Test FilterRow validation (empty field raises error, etc.)
  - Test FilterTable CRUD (add, delete, update)
  - Test FilterTable dict conversion (to_dict, from_dict)
  - Test DatabaseSchemaInfo operator filtering

### Base Widget Class

- [x] T011 Implement FilterBuilder (QWidget) base class in `src/visual_filter_builder.py`:
  - Init: `__init__(schema_info, initial_filter, parent)`
  - Signals: `filter_changed = pyqtSignal(dict)`
  - Methods: `set_filter_from_yaml()`, `get_filter_as_yaml()`
  - Internal state: `_filter_table: FilterTable`, `_syncing: bool`
  - Docstring with usage example

- [x] T012 [P] Implement FilterBuilder._init_ui() (tab structure only):
  - Create QTabWidget with two tabs: "Visual Editor" (placeholder) + "YAML"
  - Add QPlainTextEdit for YAML tab
  - Connect textChanged signal (will implement handler in US5)
  - Layout in FilterBuilder

- [x] T013 Implement FilterBuilder YAML sync methods:
  - `_dict_to_yaml()` static method (dict → YAML string via yaml.dump)
  - `_parse_yaml()` static method (YAML string → dict via yaml.safe_load)
  - `_on_yaml_changed()` slot (parse YAML, update _filter_table, emit filter_changed)
  - Handle parse errors gracefully (don't update table on invalid YAML)

- [x] T014 Unit tests for FilterBuilder in `tests/unit/test_visual_filter_builder.py`:
  - Test initialization with initial_filter
  - Test set_filter_from_yaml loads correctly
  - Test get_filter_as_yaml returns expected dict
  - Test YAML/dict round-trip preservation

---

## Phase 3: US1 - Visual Filter Composition (P1)

Implement core visual table editor. **Prerequisite**: Phase 2. **Enables**: US4, US5, US3, US2.

### Visual Table Widget

- [x] T015 [P] Implement FilterTableWidget (QWidget) in `src/visual_filter_builder.py`:
  - Create QTableWidget with 3 columns: Field | Operator | Value (headers)
  - Methods: `set_rows(rows)`, `get_rows()`
  - Signal: `row_changed = pyqtSignal()`
  - Layout: QTableWidget in QVBoxLayout

- [x] T016 Implement FilterRowWidget (custom row editor) in `src/visual_filter_builder.py`:
  - Contains: field input, operator input, value input, delete button
  - Constructor: `__init__(row_index, row: FilterRow, schema_info, parent)`
  - Signal: `row_changed = pyqtSignal()`
  - Initially: All inputs are QLineEdit (text-based, no dropdowns yet—added in US4/US5)

- [x] T017 Connect FilterTableWidget rows to FilterRowWidget:
  - Populate table from FilterTable.rows
  - Create FilterRowWidget per row
  - Connect row_changed signals to FilterTableWidget.row_changed
  - Emit row_changed when any row changes

- [x] T018 Implement add/delete buttons for FilterTableWidget:
  - "Add Row" button at bottom → creates empty FilterRow, appends to table
  - Delete button per row → removes row, emits row_changed

- [x] T019 Update FilterBuilder._init_ui() to instantiate FilterTableWidget:
  - Create FilterTableWidget in "Visual Editor" tab
  - Connect row_changed → _on_table_changed()
  - Implement _on_table_changed() slot (get rows, convert to dict, emit filter_changed)

- [ ] T020 [P] Integration test for visual table in `tests/integration/test_send_dialog_filter.py`:
  - Test adding row shows in table
  - Test deleting row removes from table
  - Test row changes emit filter_changed signal

- [x] T021 Unit tests for FilterTableWidget and FilterRowWidget:
  - Test set_rows populates table
  - Test add row appends new FilterRow
  - Test delete removes row
  - Test row edit emits row_changed

---

## Phase 4: US4 - Field Selection from Database Schema (P1)

Add field dropdown to visual editor. **Prerequisite**: Phase 2-3. **Enables**: US5, US3.

### Field Dropdown Implementation

- [x] T022 [P] Update FilterRowWidget.field input to QComboBox (dropdown):
  - Populate with DatabaseSchemaInfo.field_names
  - Connect currentTextChanged → update _row.field_name, emit row_changed
  - On field change: clear value input (field type may have changed)

- [x] T023 Add schema_info parameter to FilterTableWidget:
  - Pass schema_info to each FilterRowWidget
  - Allow schema refresh (update dropdown options)
  - Test with sample database (4-5 fields)

- [x] T024 Handle no-database case (per FR-012):
  - If schema_info.field_names is empty: disable field dropdown, show "Load database first"
  - Test with empty schema

- [ ] T025 Test field selection behavior in `tests/integration/test_send_dialog_filter.py`:
  - Load sample CSV with known fields
  - Verify dropdown shows all fields
  - Test field selection updates row
  - Test no-database case (dropdown disabled)

- [x] T026 Unit test for field dropdown:
  - Test QComboBox populated from schema
  - Test selection updates FilterRow
  - Test empty schema case

---

## Phase 5: US5 - Operator Selection and Dynamic Value Input (P2)

Add operator dropdown with conditional value input. **Prerequisite**: Phase 2-4. **Enables**: US3.

### Operator Selection

- [x] T027 [P] Update FilterRowWidget.operator input to QComboBox:
  - Populate with schema_info.get_operators_for_field(current_field)
  - Connect currentTextChanged → update _row.operator, emit row_changed
  - On operator change: show/hide value input (see T028)

- [x] T028 Implement dynamic value input visibility in FilterRowWidget:
  - Operators with no value ("is empty", "is not empty"): hide value input
  - Operators with value ("equals", "contains"): show text input
  - Operators with list ("one of"): show multiline input
  - Update visibility when operator changes

- [x] T029 Update FilterRowWidget.value input based on operator type:
  - Single-value operators: QLineEdit
  - Multi-value operators ("one of", "none of"): QPlainTextEdit
  - No-value operators: hidden

- [ ] T030 Test operator selection in `tests/integration/test_send_dialog_filter.py`:
  - Select field → verify operators change
  - Select "is empty" → verify value input hidden
  - Select "contains" → verify value input shown (text)
  - Select "one of" → verify value input shown (multiline)

- [ ] T031 Unit test for operator dropdown:
  - Test operators populated per field type
  - Test operator change triggers value input visibility
  - Test no-value operators hide input

---

## Phase 6: US3 - Add/Edit/Delete Filter Rows (P2)

Refine row management (already basic buttons added in US1). **Prerequisite**: Phase 2-5.

### Row Management Polish

- [x] T032 [P] Implement row validation on edit in FilterRowWidget:
  - Validate field exists in schema
  - Validate operator is in allowed set
  - Show error indicator on invalid row
  - Prevent filter_changed emission if row invalid

- [ ] T033 Test add/edit/delete workflow in `tests/integration/test_send_dialog_filter.py`:
  - Add 3 rows with different fields/operators
  - Edit middle row
  - Delete middle row → verify table updates
  - Verify filter_changed emitted with correct dict

- [ ] T034 [P] Add undo button (optional nice-to-have, mark as optional):
  - Keep history of last N filter states
  - Undo button reverts to previous state
  - Can be deferred if needed

---

## Phase 7: US2 - Pre-fill from Profile Configuration (P1)

Load/save filters from config.yml profiles. **Prerequisite**: Phase 2-5.

### Configuration Integration

- [x] T035 Update _SendDialog to instantiate FilterBuilder:
  - In _SendDialog.__init__, create FilterBuilder with initial_filter from profile
  - Replace existing filter_text_edit with FilterBuilder widget
  - Connect filter_changed signal → update _session_filter dict

- [x] T036 Implement profile filter loading:
  - When profile selected in _SendDialog, get filter from config: `config[profile].get('filter', {})`
  - Call `filter_builder.set_filter_from_yaml(filter_dict)`
  - Update visual table

- [x] T037 Implement filter persistence (on send):
  - When user clicks "Send", get filter via `filter_builder.get_filter_as_yaml()`
  - Pass to sendMail.py (existing flow)
  - Optionally save to profile config (requires config write—deferred for Phase 2)

- [x] T038 Handle missing fields in loaded filter (per clarification):
  - When loading filter, validate field existence via schema
  - Rows with missing fields: load but disable with error icon
  - User can remove bad rows or load correct database
  - (Implemented via FilterValidator feedback)

- [ ] T039 Test profile filter loading in `tests/integration/test_send_dialog_filter.py`:
  - Create sample config with 2 profiles, each with different filters
  - Switch profiles → verify filter table updates
  - Switch back → verify original filter restored

- [ ] T040 [P] Contract test for _SendDialog/FilterBuilder integration:
  - Test signals emitted correctly
  - Test state lifecycle (init, profile change, filter change)
  - Test persistence (filter survives dialog reopen)

---

## Phase 8: Polish & Cross-Cutting Concerns

Refinement, error handling, optimization, documentation. **Prerequisite**: All previous phases.

### Error Handling & Validation

- [ ] T041 Implement FilterValidator integration in _SendDialog:
  - On filter_changed, run FilterValidator.get_validation_status()
  - Show validation errors in filter_status_label (existing pattern)
  - Show error count: "N validation errors"
  - Highlight invalid rows in visual table

- [ ] T042 [P] Add error icons/colors to FilterRowWidget:
  - Invalid field: red border + error icon on field input
  - Invalid operator: red border on operator
  - Missing value: gray box on value input
  - Hover shows error message

### Performance & Scale

- [ ] T043 Test with large schema (1000+ fields):
  - Verify field dropdown loads in <500ms
  - Verify operator dropdown updates in <100ms
  - Test table with 20+ rows (typical use case)

- [ ] T044 [P] Optimize schema lookup:
  - Cache field_names list (already in DatabaseSchemaInfo)
  - Cache operators_for_type dict
  - Measure dialog open time
  - Note: DatabaseSchemaInfo field_names already cached as list

### Documentation & Examples

- [x] T045 [P] Add docstrings to all public methods:
  - FilterRow, FilterTable, DatabaseSchemaInfo
  - FilterBuilder, FilterTableWidget, FilterRowWidget
  - Include parameter types and return types
  - Example usage for complex methods

- [x] T046 Update CLAUDE.md with visual filter builder section:
  - Add to "Key Files" table: visual_filter_builder.py
  - Document FilterBuilder public API
  - Note integration point in _SendDialog

### Final Integration Tests

- [ ] T047 [P] End-to-end test: Send Mailing dialog workflow:
  - Open dialog → select profile → view filter
  - Add filter row → select field/operator/value
  - Check "Matching Records" updates
  - Click "Send" (mocked, no actual send)
  - Verify filter dict passed correctly

- [ ] T048 Regression test: Verify existing Send Mailing functionality:
  - Subject, Message, Database fields still work
  - Profile selection still works
  - Flags (Test, Verbose, Do not send) still work
  - Record preview still works
  - Existing YAML filter still accepted (backward compatibility)

---

## Dependency Graph & Execution Order

```
Phase 1: Setup
    ↓
Phase 2: Foundational (FilterRow, FilterTable, DatabaseSchemaInfo, FilterBuilder)
    ↓
Phase 3: US1 - Visual Table (FilterTableWidget, FilterRowWidget)
    ├─→ Phase 4: US4 - Field Selection (field dropdown)
    │       ├─→ Phase 5: US5 - Operator Selection (operator dropdown + dynamic value)
    │               └─→ Phase 6: US3 - Add/Edit/Delete (row validation)
    │
    └─→ Phase 7: US2 - Pre-fill from Profile (_SendDialog integration)

Phase 8: Polish & Cross-Cutting (validation, optimization, docs, final tests)
```

**Parallel Opportunities**:
- Phase 4 & 5: Field + Operator dropdowns can be implemented in parallel (both modify FilterRowWidget)
- Phase 8 tasks (T041-T048): Can mostly run in parallel with earlier phases

---

## MVP Scope (Phase 1-4)

**Delivers**: Visual table editor with field selection. Users can add filter rows with field/operator/value, preview matching records.

**Total Tasks**: 17 (T001-T020, T022-T026)
**Excludes**: Operator dropdowns (T027-T031), pre-fill (T035-T040), advanced features (T043-T048)
**Test Coverage**: Unit tests (T010, T014, T021, T026) + integration tests (T020, T025)

**Definition of Done (MVP)**:
- Visual table renders in Send Mailing dialog
- Users can add/delete rows
- Field dropdown shows database columns
- filter_changed signal emits updated dict
- "Matching Records" preview updates in real-time (<100ms)
- YAML tab stays in sync with visual changes

---

## Success Criteria Mapping

| Success Criteria | Implemented By | Status |
|------------------|---|---|
| **SC-001**: Filter row created in <10s | US1 (T015-T019), US4 (T022-T023) | Task: T019 (integration test) |
| **SC-002**: Zero syntax errors with visual editor | US5 (T027-T031), Phase 8 validation (T041) | Task: T041 |
| **SC-003**: Multi-condition filters (3+ rows) | US1 (T015-T019), US3 (T032) | Task: T033 |
| **SC-004**: 90% user success with field selection | US4 (T022-T026) | Task: T025 (user test scenario) |
| **SC-005**: Updates <100ms latency | All phases (Qt signal/slot), Phase 8 (T043-T044) | Task: T047 (end-to-end test) |
| **SC-006**: Visual ↔ YAML sync | Phase 2 (T013), Phase 5 (T027-T029) | Task: T014, T030 |

---

## Test Tasks (Organized by Story)

| Phase | Story | Unit Test | Integration Test | Contract Test |
|-------|-------|-----------|------------------|---|
| 2 | Foundational | T010, T014 | — | — |
| 3 | US1 | T021 | T020 | T008 (operator mapping) |
| 4 | US4 | T026 | T025 | — |
| 5 | US5 | T031 | T030 | — |
| 6 | US3 | — | T033 | — |
| 7 | US2 | — | T039 | T040 |
| 8 | Polish | — | T047, T048 | — |

---

## Notes

- **No new dependencies**: Uses existing PyQt6, pyyaml, sendMail.filter
- **Backward compatibility**: Existing YAML editor still works, visual editor is augmentation
- **Type safety**: All classes have full type hints (per CLAUDE.md requirement)
- **Testing**: Existing test structure (pytest, mocking Qt) reused
- **Performance**: All <100ms targets are satisfied by Qt signals (O(1) slot dispatch)
