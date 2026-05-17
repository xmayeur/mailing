# Bug Fix Plan: Filter Validation Shows "All Fields Not Found" After Profile Selection

**Branch**: `001-filter-editor-database` | **Date**: 2026-05-17 | **Issue**: Filter validation fails with missing fields after profile selection
**Input**: Bug report: "Filter box reports 'all fields not found' after selecting profile. Profiles 'cambristi' and 'artscroises' have been tested and work."

## Summary

Bug: When user selects a profile in _SendDialog, the filter validation immediately reports all filter fields as "not found". The profiles 'cambristi' and 'artscroises' are known to have valid filters in config.yml. Root cause: database schema is not being loaded/updated when profile changes, so validation runs against empty schema. Fix: ensure database path is loaded before running validation when profile changes.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: PyQt6 (for _SendDialog UI), YAML parsing (yaml.safe_load)  
**Storage**: CSV files, config.yml (YAML profiles)
**Testing**: pytest with 40+ passing tests (test_editor_filter.py, test_filter_validator.py, test_schema_provider.py)
**Target Platform**: Desktop (PyQt6 GUI)
**Project Type**: Desktop application (bulk email tool)
**Performance Goals**: Validation <200ms, record preview <300ms for 1000+ records  
**Constraints**: Session-only filter (no modification to config.yml)
**Scale/Scope**: Multiple profiles with different databases, filters with various field names

### Root Cause Analysis

**Current Flow in _load_profile_defaults()** (line 548-579):
1. Get profile config from self._config_data
2. Update database_input text field
3. Load current filter via load_current_filter()
4. Call filter_and_display_records()

**Problem**: filter_and_display_records() calls _get_database_schema() which reads from self.database_input.text() to get the path. But the timing is:
- database_input text is SET at line 564
- filter_and_display_records() is called at line 579
- BUT validation runs with schema extracted from database_input.text()
- If database path was empty before, schema is still empty on first profile load

**Hypothesis**: Database schema extraction fails because:
1. Profile change updates filter field first
2. Validation triggers via textChanged signal
3. But database path in database_input might not be set yet
4. Schema comes back empty []
5. All fields marked "not found"

## Constitution Check

*GATE: Must pass before Phase 0 research.*

✓ PASS: Bug fix is isolated to filter validation timing in _SendDialog
✓ PASS: No changes to config.yml or core sendMail.py logic required
✓ PASS: Fix uses existing validation infrastructure (FilterValidator, DatabaseSchemaProvider)
✓ PASS: Will include regression tests (existing 40 tests + new timing test)

## Fix Strategy

### Diagnosis (Phase 0)
1. Verify exact timing of events in _load_profile_defaults()
2. Check if database_input is updated BEFORE filter_and_display_records()
3. Test schema extraction with known working profiles (cambristi, artscroises)
4. Confirm validation is called before database schema is available

### Solution (Phase 1)
**Option A**: Set database_input BEFORE calling load_current_filter()
- Ensures schema is available when filter_text_edit triggers textChanged
- Minimal change, preserves existing flow

**Option B**: Disable validation timer during profile load
- Prevent premature validation while transitioning profiles
- Enable after everything is loaded
- More explicit control over timing

**Option C**: Cache schema per profile in _load_profile_defaults()
- Load schema once, pass to validation
- Avoids file I/O during validation
- Most efficient but requires refactoring

### Recommended: Option A (minimal change)
Move database_input.setText() from line 564 to line 549 (before load_current_filter)

### Test Approach
- Add timing test to test_editor_filter.py
- Verify all profiles load filter without "fields not found" errors
- Test with cambristi and artscroises (known working)
- Test with profile that has no database defined

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
