# Feature Specification: Filter Editor with Database Preview in Send Newsletter Window

**Feature Branch**: `001-filter-editor-database`  
**Created**: 2026-05-17  
**Status**: Draft  
**Input**: User description: "Extend Send Newsletter window with editable filter and filtered database record preview"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Load and Display Current Filter (Priority: P1)

User opens Send Newsletter window and sees the active filter loaded from config.yml based on the selected profile. The filter is displayed in an editable text field in YAML format.

**Why this priority**: Core feature—without loading the current filter, user cannot understand or modify what will be applied.

**Independent Test**: Can be tested by launching editor, selecting profile, and verifying filter text field contains filter from config.yml.

**Acceptance Scenarios**:

1. **Given** Send Newsletter window is open with a profile selected, **When** window loads, **Then** filter field displays the YAML filter from config.yml for that profile
2. **Given** profile is switched, **When** new profile selected, **Then** filter field updates to show new profile's filter
3. **Given** no filter defined in config.yml, **When** window loads, **Then** filter field shows empty or default state

---

### User Story 2 - Edit Filter and See Real-Time Validation (Priority: P1)

User edits the filter in the text field and receives immediate validation feedback. Valid YAML syntax and field existence are checked.

**Why this priority**: Core feature—users need to know if their filter is valid before applying it.

**Independent Test**: Can be tested by editing filter text and verifying validation messages appear without sending email.

**Acceptance Scenarios**:

1. **Given** filter text field with valid YAML, **When** user edits text, **Then** validation passes and visual indicator shows valid state
2. **Given** filter text field with invalid YAML, **When** user enters invalid syntax, **Then** error message displays syntax issue
3. **Given** filter references non-existent field, **When** field validation runs, **Then** error indicates which field does not exist in database schema
4. **Given** valid filter, **When** user clears text, **Then** validation allows empty filter (applies no filtering)

---

### User Story 3 - Preview Filtered Database Records (Priority: P1)

User sees a scrollable list of database records that match the current filter (or all records if no filter). Record count is displayed prominently.

**Why this priority**: Core feature—users need to verify filter result before sending.

**Independent Test**: Can be tested by entering various filters and confirming record list updates accordingly.

**Acceptance Scenarios**:

1. **Given** valid filter, **When** filter is applied, **Then** scrollable list shows matching records and displays total count
2. **Given** no filter or empty filter, **When** list renders, **Then** all database records are shown
3. **Given** filter matches zero records, **When** applied, **Then** list is empty and count shows "0 records"
4. **Given** large result set, **When** list renders, **Then** scrollbar enables and performance is acceptable

---

### User Story 4 - Apply Edited Filter for Session (Priority: P2)

User clicks "Apply" or confirms filter, making the edited filter the active one for the current email send session. The main window reflects this change.

**Why this priority**: Enables session-level filter override without modifying config.yml.

**Independent Test**: Can be tested by applying filter and verifying it is used for email send operation.

**Acceptance Scenarios**:

1. **Given** edited filter in dialog, **When** user clicks "Apply Filter", **Then** edited filter becomes session active filter
2. **Given** session-active filter, **When** filter is applied, **Then** record count and list update immediately
3. **Given** window closed without applying, **When** dialog closes, **Then** original filter remains active (no side effects)

### Edge Cases

- What happens when database has zero records? → Show empty list with "0 records" count
- How does system handle very large databases (10k+ records)? → Use QTableWidget scrollbar for navigation; optimize filter matching to <300ms for 1000 records (pagination not required for v1)
- What if filter references field names that exist in config but not in active database? → Validation error with field name(s) that cannot be found
- What happens when user switches profiles while filter editor is open? → Filter field updates; list updates to match new profile's database
- How does system handle malformed YAML with missing values? → Syntax error message identifies line number
- What if database connection fails while loading records? → Show error state in list area with retry option
- What happens with Unicode/special characters in filter values? → System should handle without corruption
- What if user closes dialog during validation/loading? → Operation should be cancellable with no side effects

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST load and display the active filter from config.yml in YAML text format when Send Newsletter window opens
- **FR-002**: System MUST parse edited filter text and validate YAML syntax in real-time as user types
- **FR-003**: System MUST validate filter field names against the active database schema and report missing/invalid fields
- **FR-004**: System MUST load database records from the active profile's database source (CSV or Google Sheets) 
- **FR-005**: System MUST filter loaded records using the current filter definition and display matching records in scrollable list
- **FR-006**: System MUST display the total count of filtered records prominently
- **FR-007**: Users MUST be able to apply/confirm edited filter, making it the session-active filter for email send operation
- **FR-008**: System MUST revert to original filter if user closes dialog without applying changes
- **FR-009**: System MUST support filter syntax identical to config.yml filter definitions (YAML key-value matching)
- **FR-010**: System MUST handle empty/null filters (show all records)
- **FR-011**: System MUST provide visual distinction between valid and invalid filter states
- **FR-012**: System MUST disable "Apply Filter" button when any validation error exists (syntax errors or missing fields)

### Key Entities

- **Filter**: YAML-formatted definition with field-value pairs used to match database records. Key attributes: field names, match values, syntax validity, session-active flag
- **Database Record**: Single row/entry from active database (CSV or Google Sheets). Attributes: field names (columns) and values. Matches filter if all filter key-value pairs exist and match in record
- **Profile**: Email profile from config.yml. Key attributes: name, associated database source, default filter definition, SMTP/Gmail settings
- **Validation Result**: Feedback from filter validation. Attributes: is_valid, syntax_errors (list), missing_fields (list), field_availability (per-field status)

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Filter editor loads in <500ms after window opens
- **SC-002**: Validation feedback appears within 200ms of user stopping typing (debounced) — performance goal, not hard requirement; acceptable if slightly higher under load
- **SC-003**: Record list updates and renders within 300ms of valid filter application
- **SC-004**: All user stories can be independently tested and pass acceptance scenarios
- **SC-005**: System correctly identifies 100% of syntax errors and invalid field references
- **SC-006**: Database record preview handles databases with 1000+ records without UI lag

## Assumptions

- **User Assumption**: Users are familiar with YAML syntax and filtering concepts used in sendMail config.yml
- **Scope**: Feature applies only to Send Newsletter window; main sendMail.py CLI unaffected
- **Filter Syntax**: Filter syntax remains identical to existing config.yml filter definitions (no new filter language)
- **Database Loading**: Database records load lazily on profile selection/change (not on window open to avoid UI blocking)
- **Field Names**: Database field names (column headers) are consistent between config.yml filter references and actual database
- **Session Scope**: Edited filter applies only to current session; config.yml is not modified
- **Filter Matching**: Reuse/wrap existing filter matching logic from sendMail.py (identify and wrap target function in Phase 1 review)
- **UI Framework**: Uses existing PyQt6 framework and editor window infrastructure

## Clarifications

### Session 2026-05-17

- Q1: Large database handling (10k+ records) → A: Simple scrolling sufficient (QTableWidget scrollbar), optimize filter matching to <300ms for 1000 records. Pagination not required for v1.
- Q2: Database loading trigger → A: Load on profile change only (lazy loading, responsive UI). Records not fetched until profile selected.
- Q3: Validation error handling → A: Disable "Apply Filter" button when any validation error exists (syntax or missing fields). Safest approach, prevents broken filters.
- Q4: Filter matching logic source → A: Wrap existing sendMail.py filtering function (minimal duplication, reuse proven logic). Identify target function in Phase 1 review.
- Q5: Validation feedback latency → A: Performance goal, not hard requirement. Target <200ms but acceptable if slightly higher under load (practical flexibility).
