# Implementation Plan: Fix Dynamic Filter Operations Support

**Branch**: `001-filter-editor-database` | **Date**: 2026-05-17 | **Spec**: [spec.md](spec.md)
**Input**: Bug fix: dynamic filter operations "starts with", "is", "contains" do not work in editor

## Summary

Filter editor supports only subset of available operations. Operations like "contains", "starts with", "ends with", "matches" are defined but missing from _FILTER_OPS recognition list. Users cannot use these operations in the filter editor despite being valid in CLI. Fix adds missing operations to parser, enables string-matching operations in validation/preview.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: PyQt6, gspread, google-api-python-client  
**Storage**: YAML config (config.yml), CSV databases, Google Sheets  
**Testing**: pytest, integration tests with filter_validator.py / filter_matcher.py  
**Target Platform**: macOS, Linux (PyQt6 desktop app)  
**Project Type**: Desktop application with email campaign management  
**Performance Goals**: <300ms for filter matching on 1000 records  
**Constraints**: Maintain backward compatibility with existing filter syntax  
**Scale/Scope**: Single-user application, ~2000 LOC for filter/editor components

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Scope**: Bug fix within existing filter system, no architectural changes
- **Backward Compatibility**: Must not break existing filters using supported operations
- **Testing**: Requires integration test coverage for each new operation
- **Code Quality**: Follow existing patterns in sendMail.py filter functions

## Project Structure

### Documentation (this feature)

```text
specs/001-filter-editor-database/
├── plan.md              # This file
├── research.md          # Phase 0 output (after /speckit.plan)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (if applicable)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code

```text
src/
├── sendMail.py          # Filter implementation (_FILTER_OPS, _parse_filter_expr, _eval_string)
├── filter_validator.py  # Syntax validation for editor
├── filter_matcher.py    # Filter matching for record preview
└── editor.py            # UI for filter editing

tests/
├── unit/test_filter.py               # Unit tests for filter operations
└── integration/test_editor_filter.py # Integration tests with UI
```

## Implementation Phases

### Phase 0: Research (Current)

**Unknowns to Clarify**:
1. Which string operations should be added? (contains, starts with, ends with, matches, does not match, does not contain)
2. Should regex matching be supported for "matches" operation?
3. Should all string operations be case-sensitive or configurable?

**Investigation Tasks**:
- [ ] Verify all _OP_* constants and which are missing from _FILTER_OPS
- [ ] Check CLI usage patterns for string operations (config.yml examples)
- [ ] Review test coverage gaps for string operations

**Output**: research.md with decisions on scope, regex support, case sensitivity

### Phase 1: Design & Implementation

**Technical Design**:
- Add missing string operations to _FILTER_OPS list: ["contains", "starts with", "ends with", "matches", "does not match", "does not contain"]
- Expand _eval_string() function to handle new operations
- Update _parse_filter_expr() to recognize new operations (should work automatically once in _FILTER_OPS)
- Update filter_validator.py to recognize new operations as valid
- Add integration tests for each new operation

**Data Model**: No schema changes. Filter format remains `{field: "operator value"}`.

**Contracts**: Filter UI accepts standard operations list from sendMail._FILTER_OPS.

**Artifacts**:
- [ ] data-model.md: Clarify filter operation semantics
- [ ] quickstart.md: Examples of using each new operation
- [ ] Updated sendMail.py: _FILTER_OPS, _eval_string()
- [ ] Updated tests: unit + integration for each operation

### Phase 2: Testing & Validation

**Test Coverage**:
- Unit tests for _eval_string() with each new operation
- Integration tests in editor for filter preview with new operations
- Edge cases: empty strings, null values, case sensitivity, special characters

**Success Criteria**:
- All new operations parse correctly
- filter_validator recognizes them as valid
- filter_matcher applies them correctly
- Editor preview shows correct filtered records
- No regression in existing operations

## Next Steps

1. Run `/speckit.plan` to generate research.md
2. Research missing operations and usage patterns
3. Run `/speckit.tasks` to generate implementation tasks
4. Implement _FILTER_OPS changes
5. Add/update tests
6. Verify editor filter preview works with new operations

## Related Files

- sendMail.py: Line 1029 (_FILTER_OPS), 1053 (_parse_filter_expr), 1106 (_eval_string)
- filter_validator.py: Line 46 (validate_field_names - may need update)
- filter_matcher.py: Uses sendMail.filter() - should work automatically
- editor.py: Line 666 (_get_database_schema) - caching already integrated
- tests/unit/test_filter.py: Existing filter operation tests
- tests/integration/test_editor_filter.py: Editor UI integration tests
