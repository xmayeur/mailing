# Implementation Plan: Visual Filter Builder UI

**Feature**: `004-visual-filter-builder`  
**Created**: 2026-05-18  
**Status**: Ready for Implementation

---

## Overview

This plan breaks down the visual filter builder into implementable phases, introducing a table-based UI for composing filters without YAML syntax knowledge, with full sync between visual and text-based editors.

### Success Metrics

- Users compose 3-row filters in <10 seconds using only dropdowns
- Zero filter syntax errors when using visual editor
- 90% of non-technical users can select correct fields
- Visual editor ↔ YAML editor sync latency <100ms

---

## Phase 1: Foundation & Data Structure (Priority: P1)

### 1.1 Define Filter Row Model

**Objective**: Create internal data structure to represent a single filter condition

**Tasks**:
- [ ] Create `FilterRow` dataclass or named tuple with fields: `field`, `operator`, `value` (optional)
- [ ] Create `FilterConfig` container class to manage list of `FilterRow` objects
- [ ] Implement conversion methods: `FilterConfig.to_yaml()` → dict for YAML output, `FilterConfig.from_yaml()` → parse YAML dict
- [ ] Add validation method: `FilterRow.is_valid()` checks field/operator/value constraints

**Acceptance**:
- Can create FilterRow objects in code
- Can convert list of rows to/from YAML dict format
- Validation catches missing required values
- Round-trip conversion (YAML → rows → YAML) preserves data

**Estimate**: 3-4 hours

---

### 1.2 Define Filter Operators & Field Types

**Objective**: Map supported operators to field types and determine required inputs

**Tasks**:
- [ ] Create `FilterOperator` enum with: `EMPTY`, `NOT_EMPTY`, `EQUALS`, `CONTAINS`, `GREATER_THAN`, `LESS_THAN`, `ONE_OF`
- [ ] Create `FieldType` enum: `TEXT`, `NUMBER`, `DATE`, `CATEGORY`
- [ ] Build operator-type matrix: map which operators apply to which field types
  - TEXT: EMPTY, NOT_EMPTY, EQUALS, CONTAINS, ONE_OF
  - NUMBER: EMPTY, NOT_EMPTY, EQUALS, GREATER_THAN, LESS_THAN
  - DATE: EMPTY, NOT_EMPTY, EQUALS, GREATER_THAN, LESS_THAN
  - CATEGORY: EMPTY, NOT_EMPTY, EQUALS, ONE_OF
- [ ] Define input requirements per operator:
  - EMPTY/NOT_EMPTY: no value required
  - EQUALS/CONTAINS/GREATER_THAN/LESS_THAN: single text/numeric value required
  - ONE_OF: comma-separated values required

**Acceptance**:
- Operator enum matches filter syntax supported by sendMail
- Operator-type matrix is complete and accurate
- Input requirements are clearly defined

**Estimate**: 2-3 hours

---

## Phase 2: UI Component Design (Priority: P1)

### 2.1 Create Filter Table Widget

**Objective**: Build reusable PyQt6 table widget for filter editing

**Tasks**:
- [ ] Create `FilterTableWidget` class extending `QTableWidget`
- [ ] Define columns: Field (col 0), Operator (col 1), Value (col 2), Delete (col 3)
- [ ] Implement `add_row()` method: appends empty row with dropdown widgets
- [ ] Implement `delete_row(row_index)` method: removes row from table
- [ ] Implement `set_data(filter_config)` method: populates table from FilterConfig
- [ ] Implement `get_data()` method: returns FilterConfig from current table state
- [ ] Style table for clarity: alternating row colors, clear headers, compact spacing

**Acceptance**:
- Table displays 4 columns as designed
- Add/delete row buttons work without errors
- Table can be populated from FilterConfig and exported back
- Layout is readable and compact

**Estimate**: 4-5 hours

---

### 2.2 Create Field Dropdown Cell

**Objective**: Populate field dropdown with database schema columns

**Tasks**:
- [ ] Create `FieldDropdownDelegate` class (PyQt6 item delegate)
- [ ] On row edit, fetch database schema (via existing `_SendDialog._get_database_schema()`)
- [ ] Populate dropdown with field names in sorted order
- [ ] Add placeholder text if no database loaded: "[Load Database]"
- [ ] Emit signal when field is selected (to trigger operator list update)
- [ ] Handle schema changes: refresh field list if database is reloaded

**Acceptance**:
- Dropdown shows all database column names
- Dropdown is disabled/grayed if no database loaded
- Field selection triggers operator refresh
- Schema updates are reflected in next opened dialog

**Estimate**: 3-4 hours

---

### 2.3 Create Operator Dropdown Cell

**Objective**: Show only valid operators for selected field type

**Tasks**:
- [ ] Create `OperatorDropdownDelegate` class
- [ ] On field selection, infer field type from schema (text by default unless marked numeric)
- [ ] Filter operator list based on field type (use operator-type matrix from Phase 1.2)
- [ ] Populate dropdown with matching operators
- [ ] Emit signal when operator is selected (to trigger value field show/hide)

**Acceptance**:
- Dropdown shows only operators valid for the selected field
- Operator list updates when field changes
- Text fields show EQUALS, CONTAINS, etc.; number fields show GREATER_THAN, etc.

**Estimate**: 3-4 hours

---

### 2.4 Create Dynamic Value Input Cell

**Objective**: Show/hide value input based on selected operator

**Tasks**:
- [ ] Create `ValueInputDelegate` class
- [ ] For operators requiring no value (EMPTY, NOT_EMPTY): hide input field
- [ ] For single-value operators (EQUALS, CONTAINS, GREATER_THAN, LESS_THAN): show text/numeric input
- [ ] For multi-value operators (ONE_OF): show comma-separated text input
- [ ] Validate input on edit: numeric operators validate numeric input
- [ ] Show error state if validation fails (red border, error message)

**Acceptance**:
- Value input only appears when needed
- Input type matches operator (text vs numeric)
- Validation provides user feedback
- Error states are clear

**Estimate**: 3-4 hours

---

## Phase 3: Integration with Send Mailing Dialog (Priority: P1)

### 3.1 Replace Text-Based Filter Editor

**Objective**: Replace `_SendDialog.filter_text_edit` (QPlainTextEdit) with visual table

**Tasks**:
- [ ] In `_SendDialog.__init__()`, replace `self.filter_text_edit` with `self.filter_table`
- [ ] Add "Add Row" button above table for new filter rows
- [ ] Keep "Apply Filter" and "Reset Filter" buttons (they now operate on table, not text)
- [ ] Maintain layout: form → filter section → table with buttons → record preview
- [ ] Test layout resizing and scrolling for multi-row filters

**Acceptance**:
- Visual table replaces text area in Send Mailing dialog
- Add/delete controls are accessible and functional
- Dialog layout remains clean with no visual regressions

**Estimate**: 2-3 hours

---

### 3.2 Sync Visual Editor ↔ YAML Text (Bidirectional)

**Objective**: Keep visual table and YAML representation in sync

**Tasks**:
- [ ] Add `_filter_visual_to_yaml()` method: convert table to YAML text
- [ ] Add `_filter_yaml_to_visual()` method: parse YAML text to table rows
- [ ] On table edit (cell changed), update underlying YAML text in background
- [ ] On profile load, populate table from profile's YAML filter (via `load_current_filter()`)
- [ ] On "Apply Filter" click, convert table to `_session_filter` dict (existing flow)
- [ ] Add user option to toggle between visual and text editors (advanced users may prefer YAML)

**Acceptance**:
- Editing table updates YAML representation immediately
- Loading profile fills table with existing filter
- Apply/Reset buttons work with visual editor
- Visual and text representations stay in sync

**Estimate**: 4-5 hours

---

### 3.3 Pre-fill from Profile Configuration

**Objective**: Auto-populate filter table when profile is selected

**Tasks**:
- [ ] In `_SendDialog._load_profile_defaults()`, after loading profile config, call `_populate_filter_table(profile_cfg)`
- [ ] Parse profile's `filter` or `filter_test` YAML into FilterConfig
- [ ] Populate table with FilterRow objects from parsed config
- [ ] Handle empty filters: clear table if profile has no filter
- [ ] Handle invalid/corrupted filters: show warning, leave table empty

**Acceptance**:
- Switching profiles updates filter table
- Previous profile's filter is replaced with new profile's
- Empty filters show as empty table
- Corrupted filters don't crash dialog, show warning

**Estimate**: 2-3 hours

---

## Phase 4: Database Schema Integration (Priority: P1)

### 4.1 Schema Detection & Field Type Inference

**Objective**: Improve field type detection from database

**Tasks**:
- [ ] Enhance `schema_provider.DatabaseSchemaProvider` to return field type hints (text/number/date)
- [ ] For CSV: infer type by scanning first 10 non-empty values in column
- [ ] For Google Sheets: use existing schema detection, assume text by default
- [ ] Cache schema per database file to avoid repeated scans
- [ ] Handle mixed-type columns: default to TEXT, allow user override

**Acceptance**:
- Schema returns field names AND types
- Numeric columns are identified correctly
- Type inference is reasonably accurate
- Schema caching avoids performance issues

**Estimate**: 3-4 hours

---

### 4.2 Handle Missing/Changed Databases

**Objective**: Gracefully handle schema changes and database unavailability

**Tasks**:
- [ ] If database is unloaded, disable field dropdown
- [ ] If database is reloaded (new file), refresh field dropdown
- [ ] If filter references a field no longer in schema, show warning in table
- [ ] Allow user to manually edit field name (advanced option) if database is unavailable
- [ ] Preserve filter state when database is unloaded, restore when reloaded

**Acceptance**:
- No crashes if database becomes unavailable
- Field dropdown re-populates on database change
- Invalid field references are highlighted
- User can still edit filters without database (manual entry)

**Estimate**: 2-3 hours

---

## Phase 5: Record Preview Integration (Priority: P2)

### 5.1 Update Record Filtering

**Objective**: Ensure record preview uses visual filter correctly

**Tasks**:
- [ ] Verify `filter_and_display_records()` works with new FilterConfig format
- [ ] On filter table change, call `filter_and_display_records()` to update preview
- [ ] Test filtering with multi-row filters (AND logic)
- [ ] Performance: ensure filtering doesn't block UI with large datasets

**Acceptance**:
- Record preview updates when filter table changes
- Multi-row filters correctly filter records (AND logic)
- Large datasets don't freeze UI during filtering

**Estimate**: 2-3 hours

---

## Phase 6: Testing & Validation (Priority: P1)

### 6.1 Functional Testing

**Objective**: Validate all user scenarios work correctly

**Tasks**:
- [ ] Test adding/editing/deleting filter rows
- [ ] Test field and operator dropdowns populate correctly
- [ ] Test value input shows/hides based on operator
- [ ] Test sync between visual and YAML text (both directions)
- [ ] Test profile pre-fill with various filters
- [ ] Test record preview updates on filter change
- [ ] Test edge cases: empty filters, missing databases, invalid operators

**Acceptance**:
- All user stories pass acceptance scenarios
- Dropdown data is accurate
- Sync is bidirectional and lossless
- Edge cases handled gracefully

**Estimate**: 4-5 hours

---

### 6.2 Integration Testing

**Objective**: Ensure visual filter builder works with existing Send Mailing features

**Tasks**:
- [ ] Test with profile switching
- [ ] Test with database switching
- [ ] Test with Send Mailing send operation (filters applied correctly)
- [ ] Test with test mode and verbose logging
- [ ] Ensure no regressions in existing filter features

**Estimate**: 3-4 hours

---

## Implementation Order

**Week 1**:
1. Phase 1: Data structures (FilterRow, operators, types)
2. Phase 2: UI components (table, dropdowns, inputs)
3. Phase 4.1: Schema type inference

**Week 2**:
4. Phase 3: Integration with Send Mailing dialog
5. Phase 4.2: Handle schema changes
6. Phase 5: Record preview sync

**Week 3**:
7. Phase 6: Testing & validation

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Sync loss between visual/YAML | High | Round-trip testing, unit tests for conversion |
| Performance with large filter sets | Medium | Limit visual rows, paginate if needed |
| Field type inference inaccuracy | Medium | Allow user override, default to TEXT conservatively |
| Database unavailability breaks UI | Medium | Disable fields gracefully, allow manual entry |
| Breaking change to existing YAML filters | High | Preserve backward compatibility, test old configs |

---

## Testing Checklist

- [ ] Add/delete/edit filter rows work
- [ ] Field dropdown shows database columns
- [ ] Operator dropdown filters by field type
- [ ] Value input shows/hides correctly
- [ ] Visual-to-YAML conversion is accurate
- [ ] YAML-to-visual parsing is accurate
- [ ] Profile pre-fill works with all filter types
- [ ] Record preview updates on filter change
- [ ] Database schema changes update dropdowns
- [ ] All scenarios from spec pass acceptance tests
- [ ] No regressions in existing features

---

## Deliverables

1. `FilterRow` and `FilterConfig` data classes
2. `FilterOperator` and `FieldType` enums with type matrix
3. `FilterTableWidget` PyQt6 widget with delegates
4. `FieldDropdownDelegate`, `OperatorDropdownDelegate`, `ValueInputDelegate` classes
5. Integration with `_SendDialog` (replace text editor with table)
6. Bidirectional sync between visual table and YAML text
7. Enhanced schema detection with field type inference
8. Graceful handling of database changes
9. Integration with record preview filtering
10. Comprehensive test coverage
11. Updated documentation and user guide

---

## Performance Considerations

- Schema caching: avoid repeated database scans
- Lazy dropdown population: load operators/values only when visible
- Debounced filtering: update record preview after user pauses editing (0.5s)
- Table rendering: limit visible rows to ~20 with scrolling for large filters

---

## Backward Compatibility

- Existing YAML filters must load correctly into visual editor
- Visual editor must generate YAML output compatible with sendMail filter parsing
- Text editor remains available as fallback for advanced users
- No changes to config file format or filter semantics

