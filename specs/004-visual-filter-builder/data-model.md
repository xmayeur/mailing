# Data Model: Visual Filter Builder

**Date**: 2026-05-18 | **Status**: Design | **Phase**: 1

## Entity Definitions

### FilterRow

Represents a single filter condition in the visual table.

```python
@dataclass
class FilterRow:
    """Single filter condition: field + operator + optional value."""
    
    field_name: str              # Column name from database schema
    operator: str                # Filter operator (e.g., "is", "contains", "greater than")
    value: str | None            # Optional filter value (empty string if operator is "is empty")
    
    def __post_init__(self) -> None:
        """Validate field and operator."""
        if not self.field_name:
            raise ValueError("field_name cannot be empty")
        if not self.operator:
            raise ValueError("operator cannot be empty")
```

**Validation Rules**:
- `field_name` must exist in database schema
- `operator` must be in `_FILTER_OPS` from sendMail.py
- `value` is required for most operators except "is empty", "is not empty"

**Conversion**:
- To YAML: `{field_name: "operator value"}` (e.g., `{"email": "is not empty"}`)
- From YAML: Parse "operator value" string, extract operator and value

---

### FilterTable

Collection of FilterRow objects with CRUD operations.

```python
class FilterTable:
    """Manages collection of filter rows."""
    
    def __init__(self, rows: list[FilterRow] | None = None) -> None:
        """Initialize with optional list of rows."""
        self.rows: list[FilterRow] = rows or []
    
    def add_row(self, field_name: str, operator: str, value: str | None = None) -> int:
        """Add new row. Returns row index."""
        row = FilterRow(field_name, operator, value)
        self.rows.append(row)
        return len(self.rows) - 1
    
    def delete_row(self, index: int) -> None:
        """Delete row at index."""
        if not (0 <= index < len(self.rows)):
            raise IndexError(f"Row index {index} out of range")
        self.rows.pop(index)
    
    def update_row(
        self, index: int, field_name: str | None = None, 
        operator: str | None = None, value: str | None = None
    ) -> None:
        """Update row at index (partial update allowed)."""
        if not (0 <= index < len(self.rows)):
            raise IndexError(f"Row index {index} out of range")
        row = self.rows[index]
        if field_name is not None:
            row.field_name = field_name
        if operator is not None:
            row.operator = operator
        if value is not None:
            row.value = value
    
    def to_dict(self) -> dict[str, str]:
        """Convert rows to filter dict for sendMail.filter()."""
        result = {}
        for row in self.rows:
            if row.value is None:
                result[row.field_name] = row.operator
            else:
                result[row.field_name] = f"{row.operator} {row.value}"
        return result
    
    @staticmethod
    def from_dict(filter_dict: dict[str, str]) -> "FilterTable":
        """Parse filter dict (from YAML) into FilterTable."""
        from sendMail import _parse_filter_expr  # noqa: F401
        
        table = FilterTable()
        for field_name, expr in filter_dict.items():
            operator, value = _parse_filter_expr(expr, field_name)
            table.add_row(field_name, operator, value)
        return table
```

**Invariants**:
- All rows are valid FilterRow instances
- No duplicate field names (later row overrides earlier if same field edited)
- Empty table is valid (no filters to apply)

---

### DatabaseSchemaInfo

Metadata about available database fields.

```python
class DatabaseSchemaInfo:
    """Information about database schema."""
    
    def __init__(self, field_names: list[str], field_types: dict[str, str] | None = None) -> None:
        """
        Initialize schema.
        
        Args:
            field_names: List of available column names
            field_types: Optional dict mapping field_name -> "text" | "numeric" | "date"
                        If not provided, all fields default to "text"
        """
        self.field_names = field_names
        self.field_types = field_types or {name: "text" for name in field_names}
    
    def get_field_type(self, field_name: str) -> str:
        """Get inferred type for field. Returns "text" if unknown."""
        return self.field_types.get(field_name, "text")
    
    def get_operators_for_field(self, field_name: str) -> list[str]:
        """Get applicable operators for field based on its type."""
        field_type = self.get_field_type(field_name)
        return self._operators_for_type(field_type)
    
    @staticmethod
    def _operators_for_type(field_type: str) -> list[str]:
        """Return list of operators applicable to field type."""
        from research import OPERATOR_LABELS  # Mapping from Phase 0 research
        
        if field_type == "numeric":
            return [
                "Is equal to", "Is not equal to",
                "Greater than", "Less than",
                "Greater or equal", "Less or equal",
                "Is empty", "Is not empty",
                "In list", "Not in list",
            ]
        else:  # "text" (default) or unknown
            return list(OPERATOR_LABELS.keys())
```

**Usage in UI**:
- When user selects field in dropdown, call `get_operators_for_field()` to populate operator dropdown
- Filters out irrelevant operators for that field type

---

### FilterBuilder (Qt Widget)

Main visual editor widget combining FilterTableWidget + YAML text editor.

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPlainTextEdit, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal
from typing import Any

class FilterBuilder(QWidget):
    """
    Visual filter editor with bidirectional sync between table and YAML.
    
    Signals:
        filter_changed: Emitted when filter changes. Emits dict[str, str].
    """
    
    filter_changed = pyqtSignal(dict)  # {field_name: "operator value"}
    
    def __init__(
        self, 
        schema_info: DatabaseSchemaInfo,
        initial_filter: dict[str, str] | None = None,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.schema_info = schema_info
        self._filter_table = FilterTable()
        self._syncing = False  # Prevent recursive signal emissions
        
        self._init_ui()
        if initial_filter:
            self.set_filter_from_yaml(initial_filter)
    
    def _init_ui(self) -> None:
        """Create UI: tabs with table editor and YAML editor."""
        layout = QVBoxLayout(self)
        
        # Tab widget for switching between visual and YAML
        tabs = QTabWidget(self)
        
        # Visual table editor
        self._table_widget = FilterTableWidget(self.schema_info, parent=self)
        self._table_widget.row_changed.connect(self._on_table_changed)
        tabs.addTab(self._table_widget, "Visual Editor")
        
        # YAML text editor
        self._yaml_edit = QPlainTextEdit(self)
        self._yaml_edit.setPlaceholderText("YAML filter (optional)\nExample: email: is not empty")
        self._yaml_edit.textChanged.connect(self._on_yaml_changed)
        tabs.addTab(self._yaml_edit, "YAML")
        
        layout.addWidget(tabs)
        self.setLayout(layout)
    
    def set_filter_from_yaml(self, filter_dict: dict[str, str]) -> None:
        """Load filter from YAML dict into visual table."""
        self._syncing = True
        try:
            self._filter_table = FilterTable.from_dict(filter_dict)
            self._table_widget.set_rows(self._filter_table.rows)
            yaml_text = self._dict_to_yaml(filter_dict)
            self._yaml_edit.setPlainText(yaml_text)
        finally:
            self._syncing = False
    
    def get_filter_as_yaml(self) -> dict[str, str]:
        """Get current filter as dict (for sendMail.filter)."""
        return self._filter_table.to_dict()
    
    def _on_table_changed(self) -> None:
        """Visual table changed. Sync to YAML."""
        if self._syncing:
            return
        self._syncing = True
        try:
            filter_dict = self._filter_table.to_dict()
            yaml_text = self._dict_to_yaml(filter_dict)
            self._yaml_edit.setPlainText(yaml_text)
            self.filter_changed.emit(filter_dict)
        finally:
            self._syncing = False
    
    def _on_yaml_changed(self) -> None:
        """YAML text changed. Parse and sync to visual table."""
        if self._syncing:
            return
        self._syncing = True
        try:
            yaml_text = self._yaml_edit.toPlainText()
            if yaml_text.strip():
                filter_dict = self._parse_yaml(yaml_text)
                self._filter_table = FilterTable.from_dict(filter_dict)
                self._table_widget.set_rows(self._filter_table.rows)
            else:
                self._filter_table = FilterTable()
                self._table_widget.set_rows([])
            self.filter_changed.emit(self._filter_table.to_dict())
        except Exception:
            # Invalid YAML—don't update table, wait for user to fix
            pass
        finally:
            self._syncing = False
    
    @staticmethod
    def _dict_to_yaml(filter_dict: dict[str, str]) -> str:
        """Convert filter dict to YAML string."""
        import yaml
        return yaml.dump(filter_dict, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def _parse_yaml(yaml_text: str) -> dict[str, str]:
        """Parse YAML string to filter dict."""
        import yaml
        result = yaml.safe_load(yaml_text)
        return result if isinstance(result, dict) else {}
```

**Public Methods**:
- `set_filter_from_yaml(filter_dict)` — Load filter from YAML
- `get_filter_as_yaml() -> dict[str, str]` — Get current filter for sendMail.filter()

**Signals**:
- `filter_changed(dict[str, str])` — Emitted when filter changes

---

## Component Relationships

```
_SendDialog (editor.py)
└── FilterBuilder (visual_filter_builder.py)
    ├── FilterTableWidget
    │   ├── FilterRowWidget (per row)
    │   └── DatabaseSchemaInfo (for field/operator dropdowns)
    └── QPlainTextEdit (YAML editor)
        └── FilterValidator (for validation feedback)
```

**Lifecycle**:
1. _SendDialog creates FilterBuilder with initial filter from profile config
2. User edits via visual table or YAML
3. FilterBuilder emits `filter_changed` signal
4. _SendDialog updates `_session_filter` dict
5. When user clicks "Send", filter is applied via sendMail.filter()

---

## State Management

**No external state storage** — FilterBuilder is stateless except for current rows. State lives in:
- _SendDialog._session_filter (dict[str, str])
- Config YAML (when profile is saved)

**Persistence**: Filter persists via existing config save mechanism (not changed by this feature).
