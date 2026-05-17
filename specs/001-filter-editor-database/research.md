# Research: Filter Application Bug Fix

**Feature**: Filter Editor with Database Preview (001-filter-editor-database)  
**Date**: 2026-05-17  
**Bug**: After filter validation, "Apply Filter" button returns no records

## Problem Statement

When user:
1. Edits filter in text field (passes validation)
2. Clicks "Apply Filter" button
3. Expects: Record list updates to show only filtered records
4. Actual: Record list doesn't update; appears empty or stale

## Root Cause

Method `_SendDialog._apply_filter()` (src/editor.py:760):
- ✓ Validates filter syntax against schema
- ✓ Parses YAML and stores in `self._session_filter`
- ✓ Updates status label with success message
- ✗ **MISSING**: Does NOT call method to update record preview list

Without updating the preview, user cannot verify filter result before sending.

## Solution

After successfully applying filter (line 791 in editor.py), call `self.filter_and_display_records()` to:
- Re-filter loaded records using new session filter
- Update record table display with filtered rows
- Update record count

## Implementation Details

**File**: src/editor.py  
**Method**: `_SendDialog._apply_filter()` (line 760)  
**Change**: Add `self.filter_and_display_records()` call after line 791

**Why this works**:
- `filter_and_display_records()` already handles filtering logic
- Uses `FilterMatcher.filter_rows()` to apply YAML filter to database rows
- Updates table via `_update_record_display()`
- Consistent with validation flow (validation is debounced via `_update_validation_ui()` which also calls `filter_and_display_records()`)

## Test Coverage Gap

Current test `test_apply_filter_valid()` only verifies `self._session_filter` is stored, not that records display is updated.

Need new test: `test_apply_filter_updates_display()` that:
1. Load database with multiple records
2. Apply filter
3. Assert record count/list matches filtered result

## Validation

- Passes existing 22 filter editor tests
- New test covers record display update
- Integration: session filter passed to sendMail.py (already validated in prior work)
