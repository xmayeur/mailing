# Qt Dialog Contract: Visual Filter Editor

**Date**: 2026-05-18 | **Status**: Design | **Module**: visual_filter_builder.py

## Overview

Contract document for Qt signal/slot integration between FilterBuilder widget and _SendDialog in editor.py.

---

## FilterBuilder Widget Interface

**Module**: `src/visual_filter_builder.py`

### Initialization

```python
def __init__(
    self, 
    schema_info: DatabaseSchemaInfo,
    initial_filter: dict[str, str] | None = None,
    parent: QWidget | None = None
) -> None:
    """
    Create filter builder widget.
    
    Args:
        schema_info: DatabaseSchemaInfo with field names and optional types
        initial_filter: Optional initial filter dict to load (e.g., from profile config)
        parent: Parent Qt widget
    """
```

**Responsibilities**:
- Create visual table editor (FilterTableWidget) and YAML text editor in tabs
- Maintain bidirectional sync between table and YAML
- Emit filter_changed signal on any edit
- Validate operator-field compatibility via schema_info

---

### Public Methods

#### set_filter_from_yaml(filter_dict: dict[str, str]) -> None

Load filter from YAML dict (from config or user paste).

**Preconditions**:
- filter_dict is valid (syntax validated by caller if needed)
- Fields in filter_dict should exist in schema_info (validation in FilterValidator, not here)

**Postconditions**:
- Visual table shows filter rows
- YAML editor shows formatted YAML
- No signals emitted during load (use _syncing flag)

**Error Handling**: Silently ignore invalid entries; only sync valid rows.

---

#### get_filter_as_yaml() -> dict[str, str]

Get current filter as dict for passing to sendMail.filter().

**Returns**: `{field_name: "operator value"}` dict

**Examples**:
```python
{"email": "is not empty", "status": "is active", "region": "contains USA"}
```

**Postconditions**:
- Returned dict is always valid (validated rows only)
- Empty dict if no rows

---

### Signals

#### filter_changed

**Signature**: `pyqtSignal(dict)` — emits dict[str, str]

**Emission**:
- Emitted when visual table row added/edited/deleted
- Emitted when YAML text changed and valid
- NOT emitted during initial load (in set_filter_from_yaml)

**Args**: Filter dict in format `{field_name: "operator value"}`

**Example Connection** (in _SendDialog):

```python
self.filter_builder = FilterBuilder(schema_info, initial_filter, parent=self)
self.filter_builder.filter_changed.connect(self._on_filter_changed)

def _on_filter_changed(self, filter_dict: dict[str, str]) -> None:
    """Update session filter and preview."""
    self._session_filter = filter_dict
    self.filter_and_display_records()  # Refresh preview
```

---

## _SendDialog Integration Points

**File**: `src/editor.py` — class `_SendDialog`

### Where to Insert FilterBuilder

Current layout:
```python
form = QFormLayout()
form.addRow("Database", database_row)
form.addRow("Filter (YAML)", filter_widget)  # Current: plain QPlainTextEdit
form.addRow("Password", password_input)
```

**New layout**:
```python
form = QFormLayout()
form.addRow("Database", database_row)

# Replace plain filter text editor with FilterBuilder
self.filter_builder = FilterBuilder(
    schema_info=self._get_schema(),
    initial_filter=self._session_filter or {},
    parent=self
)
form.addRow("Filter", self.filter_builder)
self.filter_builder.filter_changed.connect(self._on_filter_changed)

form.addRow("Password", password_input)
```

### Lifecycle Integration

**Profile Selection Change** (`_load_profile_defaults()`):
- Get filter from profile config: `config[profile_name].get("filter", {})`
- Call `self.filter_builder.set_filter_from_yaml(filter_dict)`

**Database Selection Change** (`_browse_database()`):
- Detect schema via `DatabaseSchemaProvider.detect_and_extract(database_path)`
- Create new `DatabaseSchemaInfo(fields)`
- Create/refresh `self.filter_builder` with new schema
- Preserve current filter dict if possible

**Send Button Click** (`accept()`):
- Get filter via `self.filter_builder.get_filter_as_yaml()`
- Pass to sendMail.py via command-line or programmatic call

---

## FilterTableWidget Interface

**Internal to visual_filter_builder.py** — used by FilterBuilder

### Initialization

```python
class FilterTableWidget(QWidget):
    """Visual table editor for filter rows."""
    
    row_changed = pyqtSignal()  # Emitted when any row changes
    
    def __init__(self, schema_info: DatabaseSchemaInfo, parent: QWidget | None = None) -> None:
        """Create table with field/operator/value columns."""
```

### Public Methods

#### set_rows(rows: list[FilterRow]) -> None

Populate table with rows.

```python
def set_rows(self, rows: list[FilterRow]) -> None:
    """Set table rows from FilterRow list."""
```

**Usage** (in FilterBuilder):
```python
self._table_widget.set_rows(self._filter_table.rows)
```

---

#### get_rows() -> list[FilterRow]

Get current rows as FilterRow list.

```python
def get_rows(self) -> list[FilterRow]:
    """Return current rows."""
```

---

### Signals

#### row_changed

**Signature**: `pyqtSignal()`

**Emission**: When user adds/edits/deletes row

**Usage** (in FilterBuilder):
```python
self._table_widget.row_changed.connect(self._on_table_changed)
```

---

## FilterRowWidget Interface

**Per-row editor** — used by FilterTableWidget

### Components

For each row: Field dropdown | Operator dropdown | Value input | Delete button

**Field Dropdown**:
- Options: All fields from schema_info.field_names
- On change: Emit row_changed; update operator dropdown

**Operator Dropdown**:
- Options: Operators from schema_info.get_operators_for_field(field_name)
- On change: Emit row_changed; show/hide value input

**Value Input**:
- Shown for operators that require value ("contains", "is equal to", etc.)
- Hidden for "is empty", "is not empty"
- Multiline for "one of", "none of" (comma-separated)
- On change: Emit row_changed

**Delete Button**:
- Removes row from table
- Emit row_changed

---

## Error Handling & Validation

### Validation Layers

1. **FilterBuilder**: Catch YAML parse errors, don't update table on invalid YAML
2. **FilterValidator**: Validate fields exist, operators are valid (called by _SendDialog)
3. **sendMail.filter()**: Apply filter at send time

### Error Feedback

**In _SendDialog** (existing pattern):
```python
self._filter_validator = FilterValidator()

def _on_filter_changed(self, filter_dict: dict[str, str]) -> None:
    """Validate and preview filter."""
    status = self._filter_validator.get_validation_status(
        self.filter_builder.get_filter_as_yaml(),
        self._get_schema()
    )
    if status["is_valid"]:
        self.filter_and_display_records()
    else:
        self.filter_status_label.setText(f"⚠ {status['syntax_errors']}")
```

---

## Thread Safety

**Not applicable**: All UI operations on Qt main thread. No background threads for filter operations.

---

## Performance Targets

| Operation | Target Latency | Status |
|-----------|----------------|--------|
| Row add/edit/delete | <10ms | Signal/slot only, no I/O |
| YAML refresh | <5ms | Simple dict→YAML conversion |
| Operator dropdown update | <50ms | Filter from full operator list |
| Schema load | <500ms | CSV header read or Google Sheets fetch |

---

## Backwards Compatibility

**No breaking changes**:
- FilterBuilder is new widget (not replacing, augmenting existing text editor)
- _SendDialog existing interface unchanged (only filtering internals change)
- YAML format unchanged (dict[str, str])
- Filter dict passed to sendMail.filter() unchanged

**Migration Path**:
- Old text-only editor can coexist with visual editor in tabs
- User can switch between visual and YAML editing
- Filter dict remains canonical representation

---

## Testing Strategy

**Unit Tests** (`test_visual_filter_builder.py`):
- FilterRow validation
- FilterTable CRUD operations
- FilterTable dict conversion (to/from)
- FilterBuilder sync (table ↔ YAML)

**Integration Tests** (`test_send_dialog_filter.py`):
- _SendDialog with FilterBuilder
- Profile change → filter reload
- Database change → schema update
- Filter preview with matcher

**Contract Tests** (`test_visual_filter_contract.py`):
- FilterBuilder signals emitted correctly
- _SendDialog slot connections work
- State lifecycle (init, change, reset)

---

## Future Extensions

1. **Field Type Detection** (Phase 2):
   - Extend DatabaseSchemaInfo with sample value inspection
   - Restrict operators by field type (numeric fields only show gt/lt)

2. **Filter Templates** (Phase 2):
   - Save/load common filters
   - Suggest operators based on field history

3. **Performance Tuning** (Phase 2):
   - Lazy-load large schema lists (1000+ fields)
   - Cache compiled operator lists
