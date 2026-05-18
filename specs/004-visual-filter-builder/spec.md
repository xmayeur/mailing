# Feature Specification: Visual Filter Builder UI

**Feature Branch**: `004-visual-filter-builder`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User-friendly visual filter editing interface for Send Mailing dialog

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visual Filter Composition (Priority: P1)

Campaign managers compose filters by editing raw YAML text, which requires knowledge of filter syntax and field names. A visual table-based editor allows non-technical users to build filters by selecting fields and operators from dropdowns, eliminating syntax errors and reducing cognitive load.

**Why this priority**: Core feature for the Send Mailing dialog. Directly improves usability for the majority of filter-composing workflows.

**Independent Test**: Can be tested by opening Send Mailing dialog and verifying a table appears where users can visually add and edit filter rows with field/operator/value dropdowns.

**Acceptance Scenarios**:

1. **Given** Send Mailing dialog is open, **When** user looks at the filter section, **Then** a structured table with rows appears instead of a plain text area
2. **Given** user has no filter configured, **When** they open the Send Mailing dialog, **Then** the filter table is empty and ready for new rows
3. **Given** a user creates a filter row by selecting field "email" and operator "is not empty", **When** they apply it, **Then** the corresponding YAML filter is generated correctly

---

### User Story 2 - Pre-fill from Profile Configuration (Priority: P1)

When a user switches profiles or reopens the Send Mailing dialog, their previously configured filter should automatically appear in the visual editor. This eliminates re-entering filters and ensures consistency across sessions.

**Why this priority**: Essential for workflow continuity. Users expect their configuration to persist when they select a profile.

**Independent Test**: Can be tested by configuring a filter in one profile, switching profiles, then switching back and verifying the filter is restored in the visual editor.

**Acceptance Scenarios**:

1. **Given** profile "newsletter" has a filter with fields "status: active" and "region: USA", **When** user selects this profile, **Then** the filter table shows two rows with these field-value pairs
2. **Given** user switches from profile A to profile B (which has a different filter), **When** the dialog updates, **Then** the filter table refreshes to show profile B's filter
3. **Given** a profile has no filter configured, **When** user selects it, **Then** the filter table is empty

---

### User Story 3 - Add/Edit/Delete Filter Rows (Priority: P2)

Users should be able to add new filter conditions, modify existing ones, and remove unwanted filters without re-entering everything. Each row represents one filter condition (field + operator + optional value).

**Why this priority**: Core filter management workflow. Enables flexible filter composition and modification.

**Independent Test**: Can be tested by adding a row, editing its values, and deleting it, verifying the table updates correctly.

**Acceptance Scenarios**:

1. **Given** the filter table is open, **When** user clicks "Add Row" button, **Then** a new empty row appears with field, operator, and optional value inputs
2. **Given** a filter row exists with "email: is not empty", **When** user changes the field dropdown to "status", **Then** the row updates and the operator list refreshes to match the new field
3. **Given** a row exists in the filter table, **When** user clicks a delete button on that row, **Then** the row is removed and the filter is updated
4. **Given** user edits a value in a filter row, **When** they finish editing, **Then** the change is reflected in the visual editor immediately

---

### User Story 4 - Field Selection from Database Schema (Priority: P1)

Users should select filter fields from a dropdown populated with valid database column names from the loaded subscriber database. This ensures only valid fields are used and users discover available fields without memorization.

**Why this priority**: Enables visual filter building without requiring knowledge of the exact field names in the database.

**Independent Test**: Can be tested by loading a database and verifying the field dropdown displays all column names from that database.

**Acceptance Scenarios**:

1. **Given** a CSV database with columns ["email", "name", "country", "subscription_level"] is loaded, **When** user opens the field dropdown, **Then** all four column names appear as selectable options
2. **Given** no database is loaded, **When** user opens the field dropdown, **Then** it shows a disabled state or empty list with a message to load a database
3. **Given** user selects a field from the dropdown, **When** they confirm the selection, **Then** that field name populates in the row's field input

---

### User Story 5 - Operator Selection and Dynamic Value Input (Priority: P2)

Different filter operators (e.g., "is not empty", "equals", "contains", "greater than") require different value inputs. The interface should show appropriate input controls based on the selected operator, simplifying the user's task.

**Why this priority**: Improves usability by showing only relevant input fields. Reduces confusion about what values are needed for each operator.

**Independent Test**: Can be tested by selecting different operators and verifying the correct input fields appear (e.g., text field for "contains", dropdown for "one of").

**Acceptance Scenarios**:

1. **Given** user selects operator "is empty" for a field, **When** they view the row, **Then** no value input field appears (operator requires no value)
2. **Given** user selects operator "equals", **When** they view the row, **Then** a text input field appears for entering the comparison value
3. **Given** user selects operator "greater than", **When** they view the row, **Then** a numeric input field appears
4. **Given** user selects operator "one of", **When** they view the row, **Then** an input field for comma-separated values appears

---

### Edge Cases

- **Database schema changes after dialog open**: Schema is re-loaded when user selects a different database file. Existing filter rows are validated against new schema.
- **Operators on wrong field type**: Research.md categorizes operators by type (universal, text-only, numeric-only). MVP defaults all fields to "text" type, allowing all operators. Field type inference can be added in Phase 2.
- **Filter references non-existent field**: Rows with missing fields are loaded but disabled/grayed-out with error icon. User can interactively remove them or reload correct database. FilterValidator provides feedback.
- **Empty vs null values**: Represented as `value: str | None` in FilterRow (see data-model.md). Empty string ("") differs from None (no value). Operators like "is empty" don't require value input.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a table-based filter editor in the Send Mailing dialog with rows for each filter condition
- **FR-002**: Each filter row MUST contain: a field selector dropdown, an operator selector dropdown, and a conditional value input
- **FR-003**: System MUST populate the field dropdown with database column names from the currently loaded subscriber database
- **FR-004**: System MUST populate the operator dropdown with valid filter operators applicable to the selected field
- **FR-005**: System MUST show/hide the value input field based on the selected operator (e.g., hide for "is empty", show for "equals")
- **FR-006**: System MUST allow users to add new filter rows via an "Add Row" button
- **FR-007**: System MUST allow users to delete filter rows via a delete button or similar control per row
- **FR-008**: System MUST allow users to edit existing filter row values (field, operator, value) inline
- **FR-009**: System MUST pre-fill the filter table with the current filter configuration from the selected profile's YAML configuration
- **FR-010**: System MUST generate valid YAML filter output from the visual editor that matches the original YAML format
- **FR-011**: System MUST update the underlying filter representation in real-time as users modify the table
- **FR-012**: System MUST handle the case where no database is loaded by disabling or graying out the filter editor
- **FR-013**: System MUST preserve filter state when user switches profiles and returns to a previously selected profile

### Key Entities

- **Filter Row**: A single condition in the filter table with field name, operator, and optional value
- **Database Schema**: List of column names extracted from the loaded subscriber database (CSV, Google Sheets, etc.)
- **Filter Operator**: A predefined set of comparison operators (is empty, is not empty, equals, contains, greater than, less than, one of, etc.)
- **Filter Configuration**: YAML representation of filters stored in the profile config, now also editable via the visual UI

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a complete filter condition in under 10 seconds using only mouse/dropdown selections (no typing field names)
- **SC-002**: Filter errors due to syntax or invalid field names are reduced to zero when using the visual editor
- **SC-003**: Users successfully build multi-condition filters (3+ rows) without consulting documentation
- **SC-004**: 90% of users without database schema knowledge can select correct fields from the field dropdown
- **SC-005**: Filter table updates reflect changes immediately (latency <100ms when modifying a row)
- **SC-006**: Visual editor and YAML text editor (legacy) remain in sync — changes in one are reflected in the other

## Clarifications

### Session 2026-05-18

- Q: How should the system handle filter rows that reference fields no longer present in the loaded database? → A: Load all rows but disable/gray-out rows with missing fields, showing error icon. User can interactively remove bad rows or reload database.

## Assumptions

- Database schema is already loaded and available via existing schema detection mechanism
- Filter operators are a fixed, predefined set (not user-configurable)
- YAML filter format remains unchanged (field: value pairs)
- Field types (text, number, etc.) can be inferred or are not strictly enforced in this MVP (validation handled by sendMail at send time)
- Users have access to the database schema when composing filters
- Multi-value operators (e.g., "one of") accept comma-separated values as plain text input
- The visual editor augments but does not replace the existing YAML text editor — both remain available for user choice
- Operator list varies by field type (text fields offer "contains", numeric fields offer "greater than", etc.)

