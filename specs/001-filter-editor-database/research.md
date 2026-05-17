# Research: String Filter Operations Support

**Feature**: Filter Editor with Database Preview (001-filter-editor-database)  
**Date**: 2026-05-17  
**Bug**: Dynamic filter operations "starts with", "is", "contains" do not work in editor

## Problem Statement

User attempts to use string operations in editor filter:
- "contains value"
- "starts with prefix"
- "ends with suffix"
- "matches regex"

**Expected**: Filter syntax accepted and records filtered correctly  
**Actual**: Operations not recognized; validation fails or filter doesn't apply

## Root Cause Analysis

### Finding 1: Missing from _FILTER_OPS Parser List

**File**: src/sendMail.py (line 1029-1050)

Defined operations (via constants):
- ✓ "is", "is not", "is equal to", "is not equal to"
- ✓ "in", "not in", "one of", "none of"
- ✓ "gt", "lt", "ge", "le" (numeric)
- ✓ "is empty", "is not empty"
- ❌ **"contains"** – defined (_OP_CONTAINS) but NOT in _FILTER_OPS
- ❌ **"does not contain"** – defined (_OP_DOES_NOT_CONTAIN) but NOT in _FILTER_OPS
- ❌ **"starts with"** – defined (_OP_STARTS_WITH) but NOT in _FILTER_OPS
- ❌ **"ends with"** – defined (_OP_ENDS_WITH) but NOT in _FILTER_OPS
- ❌ **"matches"** – defined (_OP_MATCHES) but NOT in _FILTER_OPS
- ❌ **"does not match"** – defined (_OP_DOES_NOT_MATCH) but NOT in _FILTER_OPS

**Result**: _parse_filter_expr() fails to recognize these operators, raises ValueError.

### Finding 2: Implementations Exist in _eval_string()

**File**: src/sendMail.py (line 1106-1120)

Implemented checks:
- ✓ "in", "one of", "not in", "none of"
- ✓ "is", "is equal to", "is not", "is not equal to"
- ✓ "is empty", "is not empty"
- ❌ "contains", "does not contain", "starts with", "ends with", "matches", "does not match" **not implemented**

**Gap**: Even if added to _FILTER_OPS, _eval_string() won't handle them.

### Finding 3: Editor Validation Uses Filter Parser

**File**: src/filter_validator.py (line 66)

Calls _parse_filter_expr() via filter() function. **If parser fails, validation fails.**

## Solution

### Step 1: Add Missing Operations to _FILTER_OPS

```python
_FILTER_OPS = [
    # ... existing ...
    "contains",
    "does not contain",
    "starts with",
    "ends with",
    "matches",
    "does not match",
]
```

### Step 2: Implement String Operations in _eval_string()

```python
def _eval_string(field_value: str, test_value: Any, op: str) -> bool:
    # ... existing cases ...
    if op in ("contains",):
        return bool(test_value in field_value)
    if op in ("does not contain",):
        return bool(test_value not in field_value)
    if op in ("starts with", _OP_STARTS_WITH):
        return bool(field_value.startswith(test_value))
    if op in ("ends with", _OP_ENDS_WITH):
        return bool(field_value.endswith(test_value))
    if op in ("matches", _OP_MATCHES):
        try:
            return bool(re.search(test_value, field_value))
        except re.error:
            log.warning(f"Invalid regex pattern: {test_value}")
            return False
    if op in ("does not match", _OP_DOES_NOT_MATCH):
        try:
            return not bool(re.search(test_value, field_value))
        except re.error:
            return False
    return True
```

### Step 3: Import `re` Module

Add `import re` to sendMail.py if not already present.

## Impact Analysis

**Breaking Changes**: None
- Operations currently unused (not in _FILTER_OPS)
- No existing filters depend on them
- Purely additive

**Performance**: 
- String operations: O(n) where n=field length
- Regex: O(n*m) worst case, acceptable for filter matching

**Testing**: Need unit + integration tests for 6 operations

## Case Sensitivity

All string operations will be **case-sensitive** to match existing behavior of "is" operation.

Users needing case-insensitive: Use "matches" with regex flag `(?i)` (e.g., `matches (?i)pattern`)

## Test Plan

**Unit tests** (test_filter.py):
- test_filter_contains
- test_filter_does_not_contain
- test_filter_starts_with
- test_filter_ends_with
- test_filter_matches
- test_filter_does_not_match
- test_filter_matches_invalid_regex (error handling)

**Integration tests** (test_editor_filter.py):
- test_filter_preview_contains
- test_filter_validation_starts_with
- test_filter_preview_matches_regex

## Validation Checklist

- [ ] _FILTER_OPS includes all 6 string operations
- [ ] _eval_string() implements all 6 operations
- [ ] re module imported and error handling in place
- [ ] Unit tests pass for each operation
- [ ] Integration tests pass (editor preview works)
- [ ] No regression in existing operations
- [ ] Documentation updated (sendMail.filter() docstring)
