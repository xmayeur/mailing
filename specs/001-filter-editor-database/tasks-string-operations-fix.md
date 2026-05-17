# Tasks: Fix Dynamic Filter String Operations Support

**Bug**: Filter operations "contains", "starts with", "ends with", "matches" defined but not recognized by parser  
**Root Cause**: 6 string operations missing from _FILTER_OPS list in sendMail.py  
**Impact**: Editor cannot use these operations; validation fails

**Input**: research.md (complete), plan.md (complete)

---

## Phase 1: Core Implementation

**Goal**: Add missing operations to parser and implement evaluation logic

- [ ] T001 [P] Review sendMail.py filter implementation:
  - Verify _FILTER_OPS list (line 1029)
  - Review _eval_string() function (line 1106)
  - Check import statements for regex support

- [ ] T002 Add missing operations to _FILTER_OPS:
  - Add 6 string operations: "contains", "does not contain", "starts with", "ends with", "matches", "does not match"
  - Ensure order matches evaluation logic
  - File: src/sendMail.py (line 1029)

- [ ] T003 Implement string operations in _eval_string():
  - "contains": substring check `test_value in field_value`
  - "does not contain": `test_value not in field_value`
  - "starts with": `field_value.startswith(test_value)`
  - "ends with": `field_value.endswith(test_value)`
  - "matches": regex `re.search(test_value, field_value)` with error handling
  - "does not match": `not re.search(...)`
  - File: src/sendMail.py (line 1106)

- [ ] T004 [P] Import re module if not already imported:
  - Add `import re` at top of sendMail.py
  - Verify no circular import issues

- [ ] T005 Add error handling for invalid regex patterns:
  - Catch `re.error` in "matches" and "does not match" operations
  - Log warning and return False (safe default - exclude row)
  - Prevents crashes from invalid patterns

- [ ] T006 Update sendMail.filter() docstring:
  - List all supported operations including new string operations
  - Update "Supported operations:" line to include "contains", "starts with", "ends with", "matches"
  - File: src/sendMail.py (line 1137)

**Checkpoint**: Parser recognizes and evaluates all 6 string operations

---

## Phase 2: Unit Tests

**Goal**: Test each operation with valid/invalid inputs

- [ ] T007 Write unit tests for "contains":
  - test_filter_contains_matching
  - test_filter_contains_non_matching
  - test_filter_contains_empty_test_value
  - File: tests/unit/test_filter.py

- [ ] T008 Write unit tests for "does not contain":
  - test_filter_does_not_contain_matching
  - test_filter_does_not_contain_non_matching
  - File: tests/unit/test_filter.py

- [ ] T009 Write unit tests for "starts with":
  - test_filter_starts_with_matching
  - test_filter_starts_with_non_matching
  - test_filter_starts_with_empty_value
  - File: tests/unit/test_filter.py

- [ ] T010 Write unit tests for "ends with":
  - test_filter_ends_with_matching
  - test_filter_ends_with_non_matching
  - File: tests/unit/test_filter.py

- [ ] T011 Write unit tests for "matches" (regex):
  - test_filter_matches_valid_regex
  - test_filter_matches_multiple_matches
  - test_filter_matches_invalid_regex (error handling)
  - test_filter_matches_case_sensitive
  - File: tests/unit/test_filter.py

- [ ] T012 Write unit tests for "does not match":
  - test_filter_does_not_match_valid_regex
  - test_filter_does_not_match_invalid_regex
  - File: tests/unit/test_filter.py

- [ ] T013 [P] Write unit tests for case sensitivity:
  - test_filter_string_ops_case_sensitive (all string ops)
  - Verify "contains" vs "CONTAINS" behave differently
  - File: tests/unit/test_filter.py

**Checkpoint**: All 6 operations have unit test coverage (matching, non-matching, edge cases)

---

## Phase 3: Integration Tests

**Goal**: Verify editor recognizes and applies operations

- [ ] T014 [P] Add integration tests for filter validation:
  - test_filter_validation_contains_valid
  - test_filter_validation_starts_with_valid
  - test_filter_validation_matches_valid
  - File: tests/integration/test_editor_filter.py

- [ ] T015 [P] Add integration tests for filter preview:
  - test_filter_preview_contains
  - test_filter_preview_starts_with
  - test_filter_preview_ends_with
  - test_filter_preview_matches_regex
  - test_filter_preview_does_not_match
  - File: tests/integration/test_editor_filter.py

- [ ] T016 Test invalid regex error handling:
  - test_filter_preview_matches_invalid_regex_graceful
  - Verify filter fails gracefully, doesn't crash
  - File: tests/integration/test_editor_filter.py

**Checkpoint**: Editor correctly validates and applies all new operations

---

## Phase 4: Validation & Testing

**Goal**: Ensure no regressions, all tests pass

- [ ] T017 [P] Run unit tests:
  - `pytest tests/unit/test_filter.py -v`
  - Verify all 25+ new test cases pass
  - Check code coverage for _eval_string()

- [ ] T018 [P] Run integration tests:
  - `pytest tests/integration/test_editor_filter.py -v`
  - Verify filter editor recognizes all operations
  - Verify record preview updates correctly

- [ ] T019 [P] Run full test suite:
  - `pytest tests/ -v --cov=.`
  - Verify no regression in existing operations
  - Check all 40+ existing filter tests still pass

- [ ] T020 Manual testing:
  - Launch editor
  - Test each operation with sample CSV database:
    - "email contains @gmail"
    - "name starts with A"
    - "status ends with active"
    - "message matches urgent|critical"
  - Verify record preview filters correctly
  - Verify validation shows correct field count

- [ ] T021 [P] Performance testing:
  - Regex operations on 1000+ records
  - Verify <300ms filter matching time
  - Check no UI lag or freezing

**Checkpoint**: All tests pass, no regressions, operations work end-to-end

---

## Phase 5: Documentation & Polish

**Goal**: Update docs, verify completeness

- [ ] T022 Update CLAUDE.md project documentation:
  - Add note about supported filter operations
  - Link to sendMail.py filter function
  - Example usage of new operations

- [ ] T023 [P] Add code comments:
  - Document each new operation in _eval_string()
  - Explain regex error handling strategy
  - Note case-sensitivity behavior

- [ ] T024 Create usage examples in docs/:
  - Example filters using each new operation
  - Regex pattern examples
  - Edge cases and error scenarios

**Checkpoint**: Implementation complete, documented, tested

---

## Execution Order

**Sequential (must complete before next phase)**:
1. Phase 1: Core Implementation (T001-T006)
2. Phase 2: Unit Tests (T007-T013)
3. Phase 3: Integration Tests (T014-T016)
4. Phase 4: Validation (T017-T021)
5. Phase 5: Documentation (T022-T024)

**Parallelizable within phases**:
- Phase 1: T001 (research) + T004 (import) can run in parallel
- Phase 2: T007-T013 can run in parallel (different operations)
- Phase 3: T014-T015 can run in parallel (different test files)
- Phase 4: T017-T021 can run in parallel
- Phase 5: T023-T024 can run in parallel

---

## Success Criteria

✓ All 6 string operations work in editor filter  
✓ Validation correctly recognizes them as valid  
✓ Record preview filters correctly  
✓ No regression in existing operations  
✓ All unit tests pass (25+ new cases)  
✓ All integration tests pass  
✓ Full test suite passes  
✓ Regex error handling prevents crashes  
✓ Documentation updated  

**Definition of Done**: All tests pass, operations work end-to-end in editor, no regressions
