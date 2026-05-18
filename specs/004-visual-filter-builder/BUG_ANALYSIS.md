# Deep-Dive Bug Analysis: Visual Filter Builder (004-visual-filter-builder)

**Date**: 2026-05-18  
**Branch**: 004-visual-filter-builder  
**Status**: Analysis of 4 critical bugs blocking functionality

---

## Bug #1: Multiple Duplicate Rows in Filter Widget

**Severity**: CRITICAL  
**Symptoms**: When loading filter from profile, multiple rows appear for same field/value pair. Expected exactly one row per key/value.

### Root Cause Analysis

Located in `src/visual_filter_builder.py:756-762` - `FilterTableWidget._clear_rows()`:

```python
def _clear_rows(self) -> None:
    """Remove all row widgets from display."""
    while self._row_widgets:
        widget = self._row_widgets.pop()
        widget.deleteLater()  # <-- ASYNC! Not immediate
```

**Problem**: `deleteLater()` is **asynchronous** in PyQt6. The widget is scheduled for deletion on the next event loop cycle, but is **not removed from the layout immediately**.

**Scenario causing duplication**:

1. Profile A has filter `{"email": "is not empty", "status": "active"}` (2 rows)
2. User switches to Profile B, which triggers `_load_profile_defaults()`
3. Line 672: `refresh_schema()` is called → `row_changed.emit()` 
4. Line 689: `load_current_filter()` is called → `set_filter_from_yaml()` → `set_rows()` → `_clear_rows()`
5. `_clear_rows()` pops widgets and calls `deleteLater()` on them
6. `_row_widgets` list is now empty
7. BUT the widgets are still in `self._container_layout` and still visible!
8. New rows are added via `_add_row_widget(i, row)` which inserts into the layout
9. Result: Old widgets + new widgets both visible → duplicates!

The duplicate appears because:
- Line 754: `self._container_layout.insertWidget(row_idx, widget)` doesn't remove old widgets
- The layout now has both old (scheduled for deletion) and new widgets
- User sees 4 rows when expecting 2

### Fix

Replace `widget.deleteLater()` with immediate removal:

```python
def _clear_rows(self) -> None:
    """Remove all row widgets from display."""
    if not PYQT_AVAILABLE:
        return
    while self._row_widgets:
        widget = self._row_widgets.pop()
        widget.setParent(None)  # Remove from layout immediately
        widget.deleteLater()     # Schedule memory cleanup
```

`setParent(None)` immediately removes the widget from its layout, before scheduling async cleanup.

---

## Bug #2: Database Schema Not Loading / Retry Does Not Work

**Severity**: CRITICAL  
**Symptoms**: When loading a CSV/Excel database, field dropdown remains empty even after profile selection with valid database file.

### Root Cause Analysis

Located in `src/editor.py:785-825` - `_get_database_schema()`:

```python
def _get_database_schema(self) -> list[str]:
    cache = self._get_schema_cache()
    profile_name = self._current_profile or "default"
    db_path = self.database_input.text().strip()
    
    # ... Google Sheets branch ...
    
    if not db_path:
        return []  # <-- Silent failure if no path
    
    def _load_csv_schema() -> list[str]:
        try:
            from schema_provider import DatabaseSchemaProvider
            return DatabaseSchemaProvider.detect_and_extract(db_path)
        except Exception as e:
            log.debug("Could not extract database schema: %s", e)
            return []  # <-- Silent failure
    
    return cache.get(f"{profile_name}_csv_{db_path}", _load_csv_schema)
```

**Problems**:

1. **Cache key includes db_path**: If user changes database file path, the cache key changes, so old path is cached separately. This is correct behavior, but means errors aren't retried until path changes.

2. **Caching of empty results**: If schema extraction fails (e.g., file not found, permission denied), it returns `[]`. This empty result is **cached**. If user later fixes the problem (e.g., moves the file to correct location), the cache still returns `[]`.

3. **Silent error handling**: Exceptions are caught and logged at DEBUG level. User gets no feedback. The "Load database first" message in dropdowns comes from empty schema, but user doesn't know WHY it's empty.

4. **Profile path not synced with database_input**: When `_load_profile_defaults()` sets `database_input.setText()` (line 660), there's a `QApplication.processEvents()` call (line 663), but the schema is loaded BEFORE the database file is actually read from disk. Race condition possibility if file I/O is slow.

5. **schema_provider.py detect_and_extract() doesn't handle all cases**:
   - Checks `path.exists()` for CSV but `_get_database_schema()` doesn't validate path exists first
   - For Excel (.xlsx/.xls), relies on `openpyxl` which may not be installed
   - For Google Sheets, relies on gsheet_service which may not be passed

### Fix

1. **Clear cache on database change** (short-term):
   - Add method to clear cache entry when database_input changes
   - Or always retry if schema is empty

2. **Add retry mechanism** (medium-term):
   - Store schema extraction failures separately from success
   - Retry failed extractions on retry button click

3. **Add user feedback** (short-term):
   - Log schema errors at WARNING level
   - Show error message in UI if database file not found

---

## Bug #3: Dropdown Lists Don't Populate / Show as Disabled

**Severity**: CRITICAL  
**Symptoms**: Field dropdown shows empty or disabled. Operator dropdown won't change. User can't select fields even with database loaded.

### Root Cause Analysis

Located in `src/visual_filter_builder.py:932-955` - `FilterRowWidget._populate_field_combo()` and `_populate_operator_combo()`:

```python
def _populate_field_combo(self) -> None:
    """Populate field combo with schema fields or disable if no database."""
    self._field_combo.clear()
    if self.schema_info.field_names:
        self._field_combo.addItems(self.schema_info.field_names)
        self._field_combo.setEnabled(True)
    else:
        self._field_combo.addItem("")  # Empty placeholder
        self._field_combo.setEnabled(False)  # <-- Disabled!

def _populate_operator_combo(self) -> None:
    field = self._field_combo.currentText()
    if field and field != "Load database first":
        operators = self.schema_info.get_operators_for_field(field)
        self._operator_combo.addItems(operators)
    self._operator_combo.setEnabled(bool(self.schema_info.field_names))
```

**Problems**:

1. **Dropdown disabled when no database**: If schema is empty (Bug #2), field combo is **disabled**, preventing user from even trying to fix it. Disabled UI element doesn't respond to clicks or signals.

2. **Operator combo depends on field being selected**: But field combo is disabled, so user can't select anything. Catch-22.

3. **No refresh signal after schema loads**: When `refresh_schema()` is called (line 725), it calls `refresh_schema()` on each row widget (line 734-735), which re-populates combos. But this happens AFTER `set_rows()` has already been called with empty fields.

4. **Order of operations issue in _load_profile_defaults()**:
   - Line 668-672: Schema is extracted and set
   - Line 672: `refresh_schema()` is called on existing row widgets
   - Line 689: `load_current_filter()` is called, which calls `set_filter_from_yaml()` → `set_rows()`
   - `set_rows()` creates NEW row widgets with old schema_info!
   - The schema has already been updated, so new widgets should get new schema, but the order is confusing

### Fix

1. **Enable dropdowns even when schema is empty** (short-term):
   ```python
   def _populate_field_combo(self) -> None:
       self._field_combo.clear()
       if self.schema_info.field_names:
           self._field_combo.addItems(self.schema_info.field_names)
       else:
           self._field_combo.addItem("")
       self._field_combo.setEnabled(True)  # Always enabled
   ```

2. **Ensure schema is fresh when setting rows**:
   - Call `refresh_schema()` AFTER `set_rows()` in `_load_profile_defaults()`
   - Or pass updated schema_info to `set_rows()`

3. **Add visual feedback when database missing**:
   - Use placeholder text "No database loaded" instead of just disabling

---

## Bug #4: Switching to YAML Editor Doesn't Sync Changes

**Severity**: HIGH  
**Symptoms**: User edits YAML tab, but visual table doesn't update. Or user switches tabs and changes are lost.

### Root Cause Analysis

Located in `src/visual_filter_builder.py:600-618` - `FilterBuilder._on_yaml_changed()`:

```python
def _on_yaml_changed(self) -> None:
    """Handle YAML text change—parse and update filter table."""
    if self._syncing or not PYQT_AVAILABLE:
        return
    
    self._syncing = True
    try:
        yaml_text = self._yaml_edit.toPlainText()
        if yaml_text.strip():
            filter_dict = self._parse_yaml(yaml_text)
            self._filter_table = FilterTable.from_dict(filter_dict)
        else:
            self._filter_table = FilterTable()
        self._table_widget.set_rows(self._filter_table.rows)  # <-- Calls set_rows again!
        self.filter_changed.emit(self._filter_table.to_dict())
    except Exception as e:
        log.debug("YAML parse error: %s", e)
    finally:
        self._syncing = False
```

**Problems**:

1. **set_rows() causes duplicate rows** (relates to Bug #1):
   - When user types in YAML tab, `textChanged` signal fires
   - `_on_yaml_changed()` calls `set_rows()` which calls `_clear_rows()`
   - Due to Bug #1 (async deletion), old rows aren't removed
   - New rows are added, resulting in duplicates

2. **Parsing failure silently fails**:
   - `_parse_yaml()` catches all exceptions and returns empty dict
   - If YAML is malformed, user gets no feedback
   - Table disappears or becomes empty

3. **Signal loops**:
   - User edits YAML → `_on_yaml_changed()` fires
   - `_on_yaml_changed()` calls `set_rows()`
   - `set_rows()` might trigger `row_changed` signal
   - `row_changed` calls `_on_table_changed()`
   - `_on_table_changed()` updates YAML text
   - YAML text change triggers `_on_yaml_changed()` again!
   - The `_syncing` flag prevents infinite loops, but it's fragile

4. **YAML validation not implemented**:
   - No feedback to user when YAML is invalid
   - No "invalid YAML" error message in UI

### Fix

1. **Fix Bug #1 first** - Once duplicate row issue is fixed, YAML sync will work better

2. **Add YAML validation feedback**:
   ```python
   def _on_yaml_changed(self) -> None:
       if self._syncing:
           return
       
       self._syncing = True
       try:
           yaml_text = self._yaml_edit.toPlainText()
           if yaml_text.strip():
               filter_dict = self._parse_yaml(yaml_text)
               if not filter_dict and yaml_text.strip():
                   # YAML didn't parse - show error
                   return
               self._filter_table = FilterTable.from_dict(filter_dict)
           else:
               self._filter_table = FilterTable()
           self._table_widget.set_rows(self._filter_table.rows)
           self.filter_changed.emit(self._filter_table.to_dict())
       finally:
           self._syncing = False
   ```

3. **Improve error handling**:
   - Catch YAML parse errors specifically
   - Log at WARNING level for user visibility
   - Show error message as tooltip or status

---

## Summary of Root Causes

| Bug | Root Cause | Impact |
|-----|-----------|--------|
| B1: Duplicate Rows | `deleteLater()` async, widgets not removed before new ones added | Unreadable UI with 2N rows instead of N |
| B2: Schema Not Loading | Caching failures, no feedback, path sync race condition | Field dropdown stays empty even with valid database |
| B3: Dropdowns Disabled | Combo disabled when schema empty, prevents user fix | User blocked from even trying to use filter |
| B4: YAML Sync Broken | Depends on B1 (set_rows), no validation feedback | User changes lost when switching tabs |

**Causal Chain**: B1 → B4 (YAML sync uses set_rows) and B2 → B3 (empty schema disables dropdowns)

---

## Implementation Order

1. **Fix B1 first** (widget lifecycle): Changes `deleteLater()` to `setParent(None)` - fixes duplicate rows
2. **Fix B2** (schema loading): Add cache clearing on database change - fixes empty dropdowns
3. **Fix B3** (dropdown enable): Enable combos even when schema empty, add placeholder text - improves UX
4. **Fix B4** (YAML sync): With B1 fixed, YAML sync will work; add validation feedback

---

## Testing Strategy

1. **B1**: Load profile → switch profiles → verify exactly N rows appear (no duplicates)
2. **B2**: Load CSV with 5 fields → verify schema extracts → change database file → verify new schema loads
3. **B3**: No database loaded → field dropdown enabled and clickable → shows empty message
4. **B4**: Edit YAML → verify table updates in <100ms → switch back to visual → verify changes persist

---

## Files to Modify

- `src/visual_filter_builder.py` - Line 756-762 (B1), 932-955 (B3), 600-618 (B4)
- `src/editor.py` - Line 785-825 (B2), 668-689 (order of operations)
- `src/schema_provider.py` - No changes needed (extract_and_detect works correctly)
