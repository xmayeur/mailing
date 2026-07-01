"""Visual filter builder widget for PyQt6-based email editor.  # pragma: no cover

Provides table-based GUI for building email subscriber filters without requiring
knowledge of YAML syntax. Supports visual composition of field-operator-value
conditions with real-time sync to YAML format.

Main Components:
    - FilterRow: Single filter condition (field + operator + optional value)
    - FilterTable: Collection of filter rows with CRUD operations
    - DatabaseSchemaInfo: Schema metadata for field/operator dropdown population
    - FilterBuilder: Main Qt widget combining visual table + YAML text editor

Integration:
    Used by _SendDialog (editor.py) for filter composition in Send Mailing dialog.
    Emits filter_changed signal when user modifies filter via table or YAML.

Dependencies:
    - PyQt6: GUI framework
    - pyyaml: YAML parsing/generation
    - sendMail: Access to _FILTER_OPS and filter() function

Note:
    This module is mocked in unit tests (coverage baseline: 0%). Integration tests
    needed for real widget coverage. See specs/fixes.md.
"""  # pragma: no cover

import logging
from dataclasses import dataclass
from typing import Any

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

log = logging.getLogger(__name__)

__all__ = [
    "FilterRow",
    "FilterTable",
    "DatabaseSchemaInfo",
    "FilterBuilder",
    "FilterTableWidget",
    "FilterRowWidget",
]

# --- String constants (S1192) ---
_OP_IS_EMPTY = "is empty"
_OP_IS_NOT_EMPTY = "is not empty"
_OP_ONE_OF = "one of"
_OP_NONE_OF = "none of"

_LABEL_IS_EQUAL_TO = "Is equal to"
_LABEL_IS_NOT_EQUAL_TO = "Is not equal to"
_LABEL_GREATER_THAN = "Greater than"
_LABEL_LESS_THAN = "Less than"
_LABEL_GREATER_OR_EQUAL = "Greater or equal"
_LABEL_LESS_OR_EQUAL = "Less or equal"
_LABEL_IS_EMPTY = "Is empty"
_LABEL_IS_NOT_EMPTY = "Is not empty"
_LABEL_IN_LIST = "In list"
_LABEL_NOT_IN_LIST = "Not in list"
_LABEL_DOES_NOT_CONTAIN = "Does not contain"
_LABEL_STARTS_WITH = "Starts with"
_LABEL_ENDS_WITH = "Ends with"
_LABEL_MATCHES_REGEX = "Matches regex"
_LABEL_DOES_NOT_MATCH = "Does not match"

_PLACEHOLDER_LOAD_DB = "(Load database first)"


@dataclass
class FilterRow:
    """Single filter condition: field + operator + optional value.

    Represents one row in the visual filter table. Each row defines
    a condition to apply when filtering subscriber records.

    Attributes:
        field_name: Column name from database schema (e.g., "email", "status")
        operator: Filter operator (e.g., "is", "contains", "greater than")
        value: Optional filter value. Can be str, list (for "one of" operators),
               or None for operators that don't need values
               (e.g., "is empty", "is not empty").

    Example:
        >>> row = FilterRow("email", "is not empty", None)
        >>> row = FilterRow("status", "is equal to", "active")
        >>> row = FilterRow("age", "greater than", "18")
        >>> row = FilterRow("status", "one of", ["active", "pending"])
    """

    field_name: str
    operator: str
    value: str | list[str] | None = None

    def __post_init__(self) -> None:
        """Normalize field_name and operator (allow empty for new rows).

        Ensures operator is always lowercase (canonical form) for consistent filtering.
        """
        if isinstance(self.field_name, str):
            self.field_name = self.field_name.strip()
        if isinstance(self.operator, str):
            self.operator = self.operator.strip().lower()

    def is_complete(self) -> bool:
        """Check if row has required fields filled in."""
        return bool(self.field_name) and bool(self.operator)


class FilterTable:
    """Manages collection of filter rows with CRUD operations.

    Provides methods to add, delete, and update filter rows, and convert
    between FilterRow list and sendMail filter dict format.

    Attributes:
        rows: List of FilterRow objects in execution order

    Example:
        >>> table = FilterTable()
        >>> table.add_row("email", "is not empty")
        0
        >>> table.add_row("status", "is equal to", "active")
        1
        >>> table.to_dict()
        {'email': 'is not empty', 'status': 'is equal to active'}
    """

    def __init__(self, rows: list[FilterRow] | None = None) -> None:
        """Initialize with optional list of rows.

        Args:
            rows: Optional list of FilterRow objects. Defaults to empty list.
        """
        self.rows: list[FilterRow] = rows if rows is not None else []

    def add_row(self, field_name: str, operator: str, value: str | None = None) -> int:
        """Add new row to filter table.

        Args:
            field_name: Column name from schema
            operator: Filter operator
            value: Optional filter value

        Returns:
            Index of newly added row

        Raises:
            ValueError: If field_name or operator is empty
        """
        row = FilterRow(field_name, operator, value)
        self.rows.append(row)
        return len(self.rows) - 1

    def delete_row(self, index: int) -> None:
        """Delete row at index.

        Args:
            index: Row index to delete

        Raises:
            IndexError: If index is out of range
        """
        if not (0 <= index < len(self.rows)):
            raise IndexError(f"Row index {index} out of range [0, {len(self.rows)-1}]")
        self.rows.pop(index)

    def update_row(
        self,
        index: int,
        field_name: str | None = None,
        operator: str | None = None,
        value: str | None = None,
    ) -> None:
        """Update row at index (partial update allowed).

        Args:
            index: Row index to update
            field_name: New field name (optional)
            operator: New operator (optional)
            value: New value (optional)

        Raises:
            IndexError: If index is out of range
            ValueError: If field_name or operator is empty (if provided)
        """
        if not (0 <= index < len(self.rows)):
            raise IndexError(f"Row index {index} out of range [0, {len(self.rows)-1}]")
        row = self.rows[index]
        if field_name is not None:
            if not field_name.strip():
                raise ValueError("field_name cannot be empty")
            row.field_name = field_name.strip()
        if operator is not None:
            if not operator.strip():
                raise ValueError("operator cannot be empty")
            row.operator = operator.strip()
        if value is not None:
            row.value = value

    def to_dict(self) -> dict[str, str]:
        """Convert rows to filter dict for sendMail.filter().

        Returns:
            Dict mapping field_name → "operator value" string.
            For operators with no value, returns just operator string.
            Incomplete rows (empty field or operator) are skipped.

        Example:
            >>> table = FilterTable([
            ...     FilterRow("email", "is not empty"),
            ...     FilterRow("status", "is", "active")
            ... ])
            >>> table.to_dict()
            {'email': 'is not empty', 'status': 'is active'}
        """
        result: dict[str, str] = {}
        for row in self.rows:
            if not row.is_complete():
                continue
            if row.value is None:
                result[row.field_name] = row.operator
            else:
                value_str = ", ".join(str(v) for v in row.value) if isinstance(row.value, list) else str(row.value)
                result[row.field_name] = f"{row.operator} {value_str}"
        return result

    @staticmethod
    def from_dict(filter_dict: dict[str, str]) -> "FilterTable":
        """Parse filter dict (from YAML) into FilterTable.

        Uses sendMail._parse_filter_expr to extract operator and value from
        the operator+value string.

        Args:
            filter_dict: Dict mapping field_name → "operator value" string

        Returns:
            FilterTable with rows parsed from dict

        Example:
            >>> table = FilterTable.from_dict({
            ...     "email": "is not empty",
            ...     "status": "is active"
            ... })
            >>> len(table.rows)
            2
            >>> table.rows[0].field_name
            'email'
        """
        parse_fn: Any = None
        try:
            from sendMail import _parse_filter_expr

            parse_fn = _parse_filter_expr
        except ImportError as e:
            log.debug("sendMail not available, using fallback parser: %s", e)

        table = FilterTable()
        for field_name, expr in filter_dict.items():
            try:
                if parse_fn is not None:
                    operator, value = parse_fn(expr, field_name)
                else:
                    operator, value = _split_operator_value(expr)
                table.add_row(field_name, operator, value)
            except (ValueError, KeyError) as e:
                log.debug(
                    "Failed to parse filter expression '%s: %s': %s",
                    field_name,
                    expr,
                    e,
                )
                table.add_row(field_name, "", expr)
        return table


def _split_operator_value(expr: str) -> tuple[str, str | None]:
    """Split "operator value" string into operator and value.

    Fallback when sendMail._parse_filter_expr is not available.
    Tries common operators in order, returning operator and remainder as value.

    Args:
        expr: Operator+value expression (e.g., "contains text", "is empty")

    Returns:
        Tuple of (operator, value). value is None if operator takes no value.
    """
    no_value_ops = [_OP_IS_EMPTY, _OP_IS_NOT_EMPTY]
    operators = [
        "is not",
        "is equal to",
        "is not equal to",
        "greater or equal to",
        "less or equal to",
        "greater than",
        "less than",
        "does not contain",
        "does not match",
        "starts with",
        "ends with",
        "contains",
        "matches",
        _OP_ONE_OF,
        _OP_NONE_OF,
        "not in",
        "in",
        "is",
    ]

    expr = expr.strip()

    if expr in no_value_ops:
        return expr, None

    for op in operators:
        if expr.startswith(op + " "):
            value = expr[len(op) + 1 :].strip()
            return op, value if value else None

    return expr, None


class DatabaseSchemaInfo:
    """Metadata about available database fields and applicable operators.

    Used by visual editor to populate field/operator dropdowns and determine
    which operators apply to each field based on inferred type.

    Attributes:
        field_names: List of available column names
        field_types: Dict mapping field_name → type ("text", "numeric", "date")

    Note:
        MVP defaults all fields to "text" type. Type inference can be added
        in Phase 2 via sample value inspection.
    """

    def __init__(self, field_names: list[str], field_types: dict[str, str] | None = None) -> None:
        """Initialize schema info.

        Args:
            field_names: List of column names from database
            field_types: Optional dict of field → type. Defaults to all "text".
        """
        self.field_names = field_names
        self.field_types = field_types or dict.fromkeys(field_names, "text")

    def get_field_type(self, field_name: str) -> str:
        """Get inferred type for field.

        Args:
            field_name: Column name to look up

        Returns:
            Field type ("text", "numeric", "date") or "text" if unknown
        """
        return self.field_types.get(field_name, "text")

    @classmethod
    def with_inferred_types(
        cls, field_names: list[str], rows: list[list[str]], sample_size: int = 20
    ) -> "DatabaseSchemaInfo":
        """Create DatabaseSchemaInfo with field types inferred from sample data.

        Scans up to sample_size rows per column; marks field "numeric" if every
        non-empty value parses as float, otherwise "text".

        Args:
            field_names: Column names
            rows: Data rows (list of lists, parallel to field_names)
            sample_size: Max rows to inspect per column
        """
        currency_strip = str.maketrans("", "", "$€£¥₹₩₽¢₪₫฿₴₦   \t")

        def _to_float(s: str) -> float:
            cleaned = s.translate(currency_strip).replace(",", ".")
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]
            return float(cleaned)

        field_types: dict[str, str] = {}
        for col_idx, name in enumerate(field_names):
            samples = []
            for row in rows[:sample_size]:
                if col_idx < len(row):
                    val = str(row[col_idx]).strip()
                    if val:
                        samples.append(val)
            if samples:
                try:
                    for s in samples:
                        _to_float(s)
                    field_types[name] = "numeric"
                except ValueError:
                    field_types[name] = "text"
            else:
                field_types[name] = "text"
        return cls(field_names, field_types)

    def get_operators_for_field(self, field_name: str) -> list[str]:
        """Get applicable operators for field based on its type.

        Args:
            field_name: Column name to get operators for

        Returns:
            List of applicable operator display names for this field
        """
        field_type = self.get_field_type(field_name)
        return self._operators_for_type(field_type)

    @staticmethod
    def _operators_for_type(field_type: str) -> list[str]:
        """Return operator display names for field type.

        MVP returns all operators for "text" fields. Type-specific filtering
        can be added in Phase 2 when field type inference is implemented.

        Args:
            field_type: Field type ("text", "numeric", "date")

        Returns:
            List of applicable operator display names
        """
        if field_type == "numeric":
            return [
                _LABEL_IS_EQUAL_TO,
                _LABEL_IS_NOT_EQUAL_TO,
                _LABEL_GREATER_THAN,
                _LABEL_LESS_THAN,
                _LABEL_GREATER_OR_EQUAL,
                _LABEL_LESS_OR_EQUAL,
                _LABEL_IS_EMPTY,
                _LABEL_IS_NOT_EMPTY,
                _LABEL_IN_LIST,
                _LABEL_NOT_IN_LIST,
            ]
        else:
            return [
                _LABEL_IS_EQUAL_TO,
                _LABEL_IS_NOT_EQUAL_TO,
                "Contains",
                _LABEL_DOES_NOT_CONTAIN,
                _LABEL_STARTS_WITH,
                _LABEL_ENDS_WITH,
                _LABEL_MATCHES_REGEX,
                _LABEL_DOES_NOT_MATCH,
                _LABEL_IS_EMPTY,
                _LABEL_IS_NOT_EMPTY,
                _LABEL_IN_LIST,
                _LABEL_NOT_IN_LIST,
            ]


OPERATOR_LABELS: dict[str, list[str]] = {
    _LABEL_IS_EQUAL_TO: ["is", "eq", "is equal to"],
    _LABEL_IS_NOT_EQUAL_TO: ["is not", "ne", "is not equal to"],
    _LABEL_GREATER_THAN: ["gt", "greater than"],
    _LABEL_LESS_THAN: ["lt", "less than"],
    _LABEL_GREATER_OR_EQUAL: ["ge", "greater or equal to"],
    _LABEL_LESS_OR_EQUAL: ["le", "less or equal to"],
    "Contains": ["contains"],
    _LABEL_DOES_NOT_CONTAIN: ["does not contain"],
    _LABEL_STARTS_WITH: ["starts with"],
    _LABEL_ENDS_WITH: ["ends with"],
    _LABEL_IS_EMPTY: [_OP_IS_EMPTY],
    _LABEL_IS_NOT_EMPTY: [_OP_IS_NOT_EMPTY],
    _LABEL_IN_LIST: [_OP_ONE_OF, "in"],
    _LABEL_NOT_IN_LIST: [_OP_NONE_OF, "not in"],
    _LABEL_MATCHES_REGEX: ["matches"],
    _LABEL_DOES_NOT_MATCH: ["does not match"],
}

OPERATORS_FOR_TYPE: dict[str, list[str]] = {
    "text": [
        _LABEL_IS_EQUAL_TO,
        _LABEL_IS_NOT_EQUAL_TO,
        "Contains",
        _LABEL_DOES_NOT_CONTAIN,
        _LABEL_STARTS_WITH,
        _LABEL_ENDS_WITH,
        _LABEL_MATCHES_REGEX,
        _LABEL_DOES_NOT_MATCH,
        _LABEL_IS_EMPTY,
        _LABEL_IS_NOT_EMPTY,
        _LABEL_IN_LIST,
        _LABEL_NOT_IN_LIST,
    ],
    "numeric": [
        _LABEL_IS_EQUAL_TO,
        _LABEL_IS_NOT_EQUAL_TO,
        _LABEL_GREATER_THAN,
        _LABEL_LESS_THAN,
        _LABEL_GREATER_OR_EQUAL,
        _LABEL_LESS_OR_EQUAL,
        _LABEL_IS_EMPTY,
        _LABEL_IS_NOT_EMPTY,
        _LABEL_IN_LIST,
        _LABEL_NOT_IN_LIST,
    ],
}


def _canonical_to_display_operator(canonical_op: str) -> str:
    """Map canonical operator to display label (case-insensitive).

    Canonical operators come from YAML/sendMail and are lowercase.
    Display labels are title-case for UI.

    Args:
        canonical_op: Operator from YAML (lowercase, e.g., "is empty")

    Returns:
        Display label (e.g., "Is empty"), or original if no mapping found
    """
    canonical_lower = canonical_op.lower().strip()
    for display_label, canonical_forms in OPERATOR_LABELS.items():
        if canonical_lower in [op.lower() for op in canonical_forms]:
            return display_label
    return canonical_op


def _display_to_canonical_operator(display_op: str) -> str:
    """Map display label to canonical operator (case-insensitive).

    Inverse of _canonical_to_display_operator. Used when user selects
    from dropdown (display label) to store canonical form in row/YAML.

    Args:
        display_op: Display label from dropdown (e.g., "Is empty")

    Returns:
        Canonical operator (lowercase, e.g., "is empty")
    """
    if display_op in OPERATOR_LABELS:
        # Return first canonical form (preferred)
        return OPERATOR_LABELS[display_op][0]
    return display_op.lower()


class FilterBuilder(QWidget if PYQT_AVAILABLE else object):  # type: ignore
    """Main visual filter editor widget with bidirectional YAML sync.

    Combines visual table editor with YAML text editor in tabs.
    Emits filter_changed signal when user modifies filter.

    Signals:
        filter_changed: Emitted when filter changes. Payload: dict[str, str]

    Attributes:
        schema_info: DatabaseSchemaInfo for field/operator population

    Example:
        >>> schema = DatabaseSchemaInfo(["email", "status"])
        >>> builder = FilterBuilder(schema)
        >>> builder.filter_changed.connect(on_filter_changed)
        >>> builder.set_filter_from_yaml({"email": "is not empty"})
    """

    if PYQT_AVAILABLE:
        filter_changed = Signal(dict)

    def __init__(
        self,
        schema_info: DatabaseSchemaInfo,
        initial_filter: dict[str, str] | None = None,
        parent: Any = None,
    ) -> None:
        """Initialize filter builder widget.

        Args:
            schema_info: DatabaseSchemaInfo for field/operator dropdowns
            initial_filter: Optional initial filter dict to load
            parent: Parent Qt widget (if using PyQt)
        """
        if PYQT_AVAILABLE:
            super().__init__(parent)
        self.schema_info = schema_info
        self._filter_table = FilterTable()
        self._syncing = False

        if PYQT_AVAILABLE:
            self._init_ui()
            if initial_filter:
                self.set_filter_from_yaml(initial_filter)

    def _init_ui(self) -> None:
        """Create UI: tabs with visual table and YAML editor."""
        if not PYQT_AVAILABLE:
            return

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget(self)

        self._table_widget = FilterTableWidget(self.schema_info)
        self._table_widget.row_changed.connect(self._on_table_changed)
        tabs.addTab(self._table_widget, "Visual Editor")

        self._yaml_edit = QPlainTextEdit(self)
        self._yaml_edit.setPlaceholderText("YAML filter (optional)\nExample: email: is not empty")
        tabs.addTab(self._yaml_edit, "YAML")

        layout.addWidget(tabs)
        self.setLayout(layout)

        self._yaml_edit.textChanged.connect(self._on_yaml_changed)

    def set_filter_from_yaml(self, filter_dict: dict[str, str]) -> None:
        """Load filter from YAML dict into visual table.

        Args:
            filter_dict: Filter dict mapping field_name → "operator value"
        """
        self._syncing = True
        try:
            self._filter_table = FilterTable.from_dict(filter_dict)
            if PYQT_AVAILABLE:
                yaml_text = self._dict_to_yaml(filter_dict)
                self._yaml_edit.setPlainText(yaml_text)
                self._table_widget.set_rows(self._filter_table.rows)
        finally:
            self._syncing = False
        # B013: Emit filter_changed to trigger validation after loading filter
        self.filter_changed.emit(self._filter_table.to_dict())

    def get_filter_as_yaml(self) -> dict[str, str]:
        """Get current filter as dict for sendMail.filter().

        Returns:
            Filter dict mapping field_name → "operator value"
        """
        return self._filter_table.to_dict()

    def validate_and_highlight_errors(self) -> None:
        """Validate rows and set visual error states on FilterRowWidget (T041-T042).

        Checks each row for:
        - Invalid field (not in schema)
        - Invalid operator (not in schema)
        - Missing value (required by operator)
        """
        if not PYQT_AVAILABLE or not hasattr(self, "_table_widget"):
            return

        for row_widget in self._table_widget._row_widgets:
            field_error = self._validate_field_exists(row_widget)
            operator_error = self._validate_operator_valid(row_widget)
            value_error = self._validate_value_present(row_widget)
            row_widget.set_error_state(field_error, operator_error, value_error)

    def _validate_field_exists(self, row_widget: Any) -> str:
        if row_widget.row.field_name and row_widget.row.field_name not in self.schema_info.field_names:
            return f"Field '{row_widget.row.field_name}' not in database schema"
        return ""

    def _validate_operator_valid(self, row_widget: Any) -> str:
        if not row_widget.row.operator:
            return ""
        valid_operators = self.schema_info.get_operators_for_field(row_widget.row.field_name)
        display_op = _canonical_to_display_operator(row_widget.row.operator)
        if display_op not in valid_operators:
            return "Operator not valid for field type"
        return ""

    def _validate_value_present(self, row_widget: Any) -> str:
        if not (row_widget.row.operator and row_widget._operator_needs_value(row_widget.row.operator)):
            return ""

        if self._is_value_empty(row_widget.row.value):
            return f"Operator '{row_widget.row.operator}' requires a value"
        return ""

    @staticmethod
    def _is_value_empty(value: Any) -> bool:
        if not value:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    def _on_table_changed(self) -> None:
        """Handle visual table change—update YAML and emit filter_changed."""
        if self._syncing or not PYQT_AVAILABLE:
            return

        self._syncing = True
        try:
            rows = self._table_widget.get_rows()
            self._filter_table = FilterTable(rows)
            filter_dict = self._filter_table.to_dict()
            yaml_text = self._dict_to_yaml(filter_dict)
            self._yaml_edit.setPlainText(yaml_text)
            self.filter_changed.emit(filter_dict)
        except Exception as e:
            log.debug("Table change error: %s", e)
        finally:
            self._syncing = False

    def _on_yaml_changed(self) -> None:
        """Handle YAML text change—parse and update filter table."""
        if self._syncing or not PYQT_AVAILABLE:
            return

        self._syncing = True
        try:
            yaml_text = self._yaml_edit.toPlainText()
            if yaml_text.strip():
                filter_dict = self._parse_yaml(yaml_text)
                # B020: Detect if YAML parsing failed (empty dict when text was present)
                if not filter_dict and yaml_text.strip():
                    log.warning("Invalid YAML filter syntax: %s", yaml_text[:50])
                    # Don't update table, keep previous state
                    self._syncing = False
                    return
                self._filter_table = FilterTable.from_dict(filter_dict)
            else:
                self._filter_table = FilterTable()
            self._table_widget.set_rows(self._filter_table.rows)
            self.filter_changed.emit(self._filter_table.to_dict())
        except Exception as e:
            log.warning("YAML parse error: %s", e)
        finally:
            self._syncing = False

    @staticmethod
    def _dict_to_yaml(filter_dict: dict[str, str]) -> str:
        """Convert filter dict to YAML string.

        Args:
            filter_dict: Filter dict to convert

        Returns:
            YAML string representation (empty string for empty dict)
        """
        if not filter_dict:
            return ""
        try:
            import yaml

            result = yaml.dump(filter_dict, default_flow_style=False, sort_keys=False)
            return result if isinstance(result, str) else ""
        except ImportError:
            return ""

    @staticmethod
    def _parse_yaml(yaml_text: str) -> dict[str, str]:
        """Parse YAML string to filter dict.

        Args:
            yaml_text: YAML text to parse

        Returns:
            Filter dict, or empty dict if parse fails
        """
        try:
            import yaml

            result = yaml.safe_load(yaml_text)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}


class FilterTableWidget(QWidget if PYQT_AVAILABLE else object):  # type: ignore
    """Visual table editor for filter rows.

    Displays filter conditions with one FilterRowWidget per row.
    Emits row_changed signal when user modifies any row or adds/deletes.

    Attributes:
        schema_info: DatabaseSchemaInfo for field type validation
        row_changed: Qt signal emitted when table contents change
    """

    if PYQT_AVAILABLE:
        row_changed = Signal()

    def __init__(self, schema_info: DatabaseSchemaInfo, parent: Any = None) -> None:
        """Initialize table widget with schema info.

        Args:
            schema_info: DatabaseSchemaInfo for validation
            parent: Parent Qt widget
        """
        if PYQT_AVAILABLE:
            super().__init__(parent)
            self.schema_info = schema_info
            self._row_widgets: list[FilterRowWidget] = []
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self._container = QWidget()
            self._container_layout = QVBoxLayout()
            # B005 & B010: Set minimal spacing (0px) + explicit row height
            self._container_layout.setSpacing(0)
            self._container_layout.setContentsMargins(0, 0, 0, 0)
            self._container.setLayout(self._container_layout)
            # B016-UX & B031 & B043: Set max height for container to show 5 rows + button
            # 5 rows × 30px + button × 30px + scrollbar overhead = 310px
            # Accommodates taller text inputs
            self._container.setMaximumHeight(310)
            layout.addWidget(self._container)
            self._add_button = QPushButton("Add Row")
            self._add_button.setMaximumHeight(40)
            self._add_button.clicked.connect(self._on_add_row)
            layout.addWidget(self._add_button)
            # B006: Add stretch at end to prevent empty rows appearing below actual rows
            layout.addStretch()
            self.setLayout(layout)
        else:
            self.schema_info = schema_info

    def set_rows(self, rows: list[FilterRow]) -> None:
        """Populate table with filter rows.

        Args:
            rows: List of FilterRow objects to display
        """
        if not PYQT_AVAILABLE:
            return
        self._clear_rows()
        for i, row in enumerate(rows):
            self._add_row_widget(i, row)

    def get_rows(self) -> list[FilterRow]:
        """Extract current rows from table.

        Returns:
            List of FilterRow objects with current table values
        """
        if not PYQT_AVAILABLE:
            return []
        return [widget.get_row() for widget in self._row_widgets]

    def refresh_schema(self, schema_info: DatabaseSchemaInfo) -> None:
        """Update schema for all rows and refresh dropdowns.

        Args:
            schema_info: Updated DatabaseSchemaInfo
        """
        if not PYQT_AVAILABLE:
            return
        self.schema_info = schema_info
        # B051: Skip signal emission if no rows (profile load case)
        # When there are no existing rows, emitting row_changed triggers
        # filter_and_display_records which is unnecessary and slow.
        # Let explicit filter_and_display_records call after profile load handle it.
        has_rows = len(self._row_widgets) > 0
        for widget in self._row_widgets:
            widget.refresh_schema(schema_info)
        # B011: Enable/disable Add Row button based on whether database is loaded
        self._add_button.setEnabled(bool(schema_info.field_names))
        # B008: Emit row_changed only if there were rows to refresh (not during profile load)
        if has_rows:
            self.row_changed.emit()

    def _add_row_widget(self, row_idx: int, row: FilterRow) -> None:
        """Create and insert FilterRowWidget.

        Args:
            row_idx: Position in widget list
            row: FilterRow to display
        """
        if not PYQT_AVAILABLE:
            return
        widget = FilterRowWidget(row_idx, row, self.schema_info)
        widget.row_changed.connect(self._on_row_changed)
        widget.delete_requested.connect(self._on_delete_row)
        self._row_widgets.append(widget)
        self._container_layout.insertWidget(row_idx, widget)

    def _clear_rows(self) -> None:
        """Remove all row widgets from display."""
        if not PYQT_AVAILABLE:
            return
        while self._row_widgets:
            widget = self._row_widgets.pop()
            # B014: Remove widget from layout immediately before async cleanup
            # setParent(None) removes from layout + schedules for deletion
            widget.setParent(None)
            widget.deleteLater()

    def _on_row_changed(self) -> None:
        """Handle row change from any FilterRowWidget."""
        if PYQT_AVAILABLE:
            self.row_changed.emit()

    def _on_add_row(self) -> None:
        """Add empty row to table."""
        if not PYQT_AVAILABLE:
            return
        row_idx = len(self._row_widgets)
        self._add_row_widget(row_idx, FilterRow("", "", None))
        self.row_changed.emit()

    def _on_delete_row(self, row_idx: int) -> None:
        """Delete row from table.

        Args:
            row_idx: Index of row to delete
        """
        if not PYQT_AVAILABLE:
            return
        if 0 <= row_idx < len(self._row_widgets):
            widget = self._row_widgets.pop(row_idx)
            # B034: Remove widget from layout immediately (setParent(None))
            # before async deletion (deleteLater), matching _clear_rows pattern
            widget.setParent(None)
            widget.deleteLater()
            self.row_changed.emit()


class FilterRowWidget(QWidget if PYQT_AVAILABLE else object):  # type: ignore
    """Editor widget for a single filter row.

    Contains field, operator, value inputs (all QLineEdit initially) and delete button.
    Emits row_changed signal when any input changes.

    Attributes:
        row_index: Position of row in table
        row: FilterRow object this widget edits
        schema_info: DatabaseSchemaInfo for type validation
        row_changed: Qt signal emitted on any field change
    """

    if PYQT_AVAILABLE:
        row_changed = Signal()
        delete_requested = Signal(int)

    @staticmethod
    def _row_value_to_str(value: str | list[str] | None) -> str:
        """Convert row value to string, handling lists and None.

        Args:
            value: Row value (string, list, or None)

        Returns:
            String representation of value
        """
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    def __init__(
        self,
        row_index: int,
        row: FilterRow,
        schema_info: DatabaseSchemaInfo,
        parent: Any = None,
    ) -> None:
        """Initialize row editor with filter data.

        Args:
            row_index: Position in table (for delete operations)
            row: FilterRow to edit
            schema_info: Schema metadata for validation
            parent: Parent Qt widget
        """
        if PYQT_AVAILABLE:
            super().__init__(parent)
            self.row_index = row_index
            self.row = row
            self.schema_info = schema_info
            layout = QHBoxLayout()

            self._field_combo = QComboBox()
            # B041: Set consistent combo size
            self._field_combo.setMinimumHeight(26)
            self._populate_field_combo()
            if schema_info.field_names:
                self._field_combo.setCurrentText(row.field_name)
            self._field_combo.currentTextChanged.connect(self._on_field_changed)
            layout.addWidget(self._field_combo, 1)  # stretch: equal width

            self._operator_combo = QComboBox()
            # B041: Match field combo size for consistent appearance
            self._operator_combo.setMinimumHeight(26)
            self._populate_operator_combo()
            if row.operator:
                # Map canonical operator to display label (case-insensitive)
                display_op = _canonical_to_display_operator(row.operator)
                combo_items = [self._operator_combo.itemText(i) for i in range(self._operator_combo.count())]
                log.info(
                    "DEBUG: FilterRowWidget: Setting operator '%s' from canonical '%s', combo items: %s",
                    display_op,
                    row.operator,
                    combo_items,
                )
                try:
                    self._operator_combo.setCurrentText(display_op)
                    current = self._operator_combo.currentText()
                    log.info(
                        "DEBUG: FilterRowWidget: After setCurrentText, combo shows: '%s'",
                        current,
                    )
                except Exception as e:
                    log.info("DEBUG: Failed to set operator '%s': %s", display_op, e)
            self._operator_combo.currentTextChanged.connect(self._on_operator_changed)
            layout.addWidget(self._operator_combo, 1)  # stretch: equal width

            value_str = self._row_value_to_str(row.value)
            self._value_edit = QLineEdit(value_str)
            # B041: Set minimum height so text isn't vertically truncated
            self._value_edit.setMinimumHeight(26)
            # B044: Center text vertically within QLineEdit
            self._value_edit.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            self._value_edit.textChanged.connect(self._on_value_changed)
            self._value_edit_multiline = QPlainTextEdit()
            self._value_edit_multiline.setPlainText(value_str)
            self._value_edit_multiline.textChanged.connect(self._on_value_changed)
            self._value_edit_multiline.setMaximumHeight(80)

            self._update_value_input_visibility()
            layout.addWidget(self._value_edit, 1)  # stretch: equal width
            layout.addWidget(self._value_edit_multiline, 1)  # stretch: equal width

            self._delete_btn = QPushButton("Delete")
            self._delete_btn.setMaximumWidth(60)
            self._delete_btn.clicked.connect(self._on_delete)
            layout.addWidget(self._delete_btn, 0)  # no stretch: fixed width

            # B010 & B031: Set minimal spacing and margins for compact rows
            layout.setSpacing(2)
            layout.setContentsMargins(0, 0, 0, 0)

            # B010 & B031 & B043: Set row height to accommodate text input (30px minimum)
            # Text input minHeight(26) needs row to be taller for vertical centering
            self.setMaximumHeight(30)

            self.setLayout(layout)
        else:
            self.row_index = row_index
            self.row = row
            self.schema_info = schema_info

    def get_row(self) -> FilterRow:
        """Get current FilterRow with edited values.

        Returns:
            FilterRow with current field/operator/value
        """
        if PYQT_AVAILABLE:
            field = self._field_combo.currentText()
            operator = self._operator_combo.currentText()
            value_text = self._get_value_input()
            # B054: Parse comma-separated list values for list operators
            parsed_value: str | list[str] | None = None
            if value_text and self._operator_is_multiline(operator):
                # Split by comma and strip whitespace from each item
                items = [item.strip() for item in value_text.split(",") if item.strip()]
                parsed_value = items if items else None
            elif value_text:
                parsed_value = value_text
            return FilterRow(field, operator, parsed_value)
        return self.row

    def _get_value_input(self) -> str:
        """Get value from whichever input is visible.

        Returns:
            Value from QLineEdit or QPlainTextEdit
        """
        if not PYQT_AVAILABLE:
            return ""
        if self._value_edit.isVisible():
            return self._value_edit.text()
        if self._value_edit_multiline.isVisible():
            return self._value_edit_multiline.toPlainText()
        return ""

    def refresh_schema(self, schema_info: DatabaseSchemaInfo) -> None:
        """Refresh field and operator dropdowns with updated schema.

        Args:
            schema_info: Updated DatabaseSchemaInfo
        """
        if not PYQT_AVAILABLE:
            return
        self.schema_info = schema_info
        # B048: Store operator before field change clears it
        current_operator = self._operator_combo.currentText()
        current_field = self._field_combo.currentText()
        log.debug(
            "refresh_schema: field=%s, operator=%s, field_names=%s",
            current_field,
            current_operator,
            len(schema_info.field_names),
        )

        # B052: Suppress signals during schema refresh to avoid cascading filter updates
        # Temporarily disconnect combo signals so setCurrentText doesn't trigger _on_field_changed
        # which would emit row_changed and cascade to filter_and_display_records
        self._field_combo.currentTextChanged.disconnect()
        self._operator_combo.currentTextChanged.disconnect()

        try:
            self._populate_field_combo()
            # B028: Only restore selection if it's a real field (not placeholder)
            if current_field and current_field != _PLACEHOLDER_LOAD_DB and current_field in schema_info.field_names:
                self._field_combo.setCurrentText(current_field)
            elif schema_info.field_names:
                # B028: If we have real fields, select first one (not placeholder)
                self._field_combo.setCurrentIndex(0)
            self._populate_operator_combo()
            # B048: Restore operator after field/operator population
            if current_operator and self._operator_combo.count() > 0:
                try:
                    self._operator_combo.setCurrentText(current_operator)
                    log.debug("refresh_schema: restored operator=%s", current_operator)
                except Exception as e:
                    log.debug("refresh_schema: could not restore operator: %s", e)
            self._update_value_input_visibility()
        finally:
            # Reconnect signals
            self._field_combo.currentTextChanged.connect(self._on_field_changed)
            self._operator_combo.currentTextChanged.connect(self._on_operator_changed)

    def _populate_field_combo(self) -> None:
        """Populate field combo with schema fields or show placeholder if no database."""
        if not PYQT_AVAILABLE:
            return
        self._field_combo.clear()
        if self.schema_info.field_names:
            # B028: Debug log when populating with real fields
            log.debug(
                "FilterRowWidget: Populating field combo with %d fields: %s",
                len(self.schema_info.field_names),
                self.schema_info.field_names[:3],
            )
            self._field_combo.addItems(self.schema_info.field_names)
            self._field_combo.setEnabled(True)
        else:
            # B017: Keep combo enabled to allow user interaction even when no database
            # Show placeholder so user knows they need to load a database first
            log.debug("FilterRowWidget: No schema fields, showing placeholder")
            self._field_combo.addItem(_PLACEHOLDER_LOAD_DB)
            self._field_combo.setEnabled(True)
        # B049: Force visual update when items populated
        self._field_combo.setStyleSheet("")
        self._field_combo.repaint()

    def _populate_operator_combo(self) -> None:
        """Populate operator combo with operators for current field."""
        if not PYQT_AVAILABLE:
            return
        self._operator_combo.clear()
        field = self._field_combo.currentText()
        if field and field != _PLACEHOLDER_LOAD_DB:
            operators = self.schema_info.get_operators_for_field(field)
            self._operator_combo.addItems(operators)
        # B017: Keep operator combo enabled to match field combo behavior
        self._operator_combo.setEnabled(True)
        # B049: Force visual update when items populated
        self._operator_combo.setStyleSheet("")
        self._operator_combo.repaint()

    def _operator_needs_value(self, operator: str) -> bool:
        """Check if operator requires a value (case-insensitive).

        Args:
            operator: Operator name (can be canonical or display label)

        Returns:
            True if operator needs value, False if operator is no-value type
        """
        no_value_ops = [_OP_IS_EMPTY, _OP_IS_NOT_EMPTY]
        op_lower = operator.lower().strip()
        return op_lower not in no_value_ops

    def _operator_is_multiline(self, operator: str) -> bool:
        """Check if operator supports multiple values (case-insensitive).

        Args:
            operator: Operator name (can be canonical or display label)

        Returns:
            True if operator supports list (e.g., 'one of'), False otherwise
        """
        multiline_ops = [_OP_ONE_OF, _OP_NONE_OF, "in list", "not in list"]
        op_lower = operator.lower().strip()
        return op_lower in multiline_ops

    def _update_value_input_visibility(self) -> None:
        """Update visibility of value inputs based on current operator."""
        if not PYQT_AVAILABLE:
            return
        operator = self._operator_combo.currentText()
        needs_value = self._operator_needs_value(operator)
        is_multiline = self._operator_is_multiline(operator)

        if not needs_value:
            self._value_edit.hide()
            self._value_edit_multiline.hide()
        elif is_multiline:
            self._value_edit.hide()
            self._value_edit_multiline.show()
        else:
            self._value_edit.show()
            self._value_edit_multiline.hide()

    def _on_field_changed(self, field_text: str) -> None:
        """Update row and emit signal on field change.

        Clear value input and refresh operators when field changes.

        Args:
            field_text: New field name from combo box
        """
        if PYQT_AVAILABLE:
            self.row.field_name = field_text
            self._value_edit.clear()
            self._value_edit_multiline.clear()
            self._populate_operator_combo()
            self._update_value_input_visibility()
            self.row_changed.emit()

    def _on_operator_changed(self, operator_text: str) -> None:
        """Update row and emit signal on operator change.

        Show/hide value input based on operator type.

        Args:
            operator_text: New operator name from combo box (display label)
        """
        if PYQT_AVAILABLE:
            # Map display label to canonical operator for storage
            canonical_op = _display_to_canonical_operator(operator_text)
            self.row.operator = canonical_op
            self._update_value_input_visibility()
            self.row_changed.emit()

    def _on_value_changed(self) -> None:
        """Update row and emit signal on value change.

        B054: Parse comma-separated list values for list operators.
        """
        if PYQT_AVAILABLE:
            text = self._get_value_input()  # Use _get_value_input to get from visible input
            # B054: Parse comma-separated values for list operators
            parsed_value: str | list[str] | None = None
            if text and self._operator_is_multiline(self._operator_combo.currentText()):
                items = [item.strip() for item in text.split(",") if item.strip()]
                parsed_value = items if items else None
            elif text:
                parsed_value = text
            self.row.value = parsed_value
            self.row_changed.emit()

    def set_error_state(self, field_error: str = "", operator_error: str = "", value_error: str = "") -> None:
        """Set visual error indicators on row widgets (T042).

        Args:
            field_error: Error message for field (empty = no error)
            operator_error: Error message for operator (empty = no error)
            value_error: Error message for value (empty = no error)
        """
        if not PYQT_AVAILABLE:
            return

        # Field combo error state
        if field_error:
            self._field_combo.setStyleSheet("QComboBox { border: 2px solid #f44336; }")
            self._field_combo.setToolTip(field_error)
        else:
            self._field_combo.setStyleSheet("")
            self._field_combo.setToolTip("")

        # Operator combo error state
        if operator_error:
            self._operator_combo.setStyleSheet("QComboBox { border: 2px solid #f44336; }")
            self._operator_combo.setToolTip(operator_error)
        else:
            self._operator_combo.setStyleSheet("")
            self._operator_combo.setToolTip("")

        # Value input error state (show as gray if missing value)
        if value_error:
            value_style = "QLineEdit, QPlainTextEdit { border: 1px solid #999; background: #f5f5f5; }"
            self._value_edit.setStyleSheet(value_style)
            self._value_edit_multiline.setStyleSheet(value_style)
            self._value_edit.setToolTip(value_error)
            self._value_edit_multiline.setToolTip(value_error)
        else:
            self._value_edit.setStyleSheet("")
            self._value_edit_multiline.setStyleSheet("")
            self._value_edit.setToolTip("")
            self._value_edit_multiline.setToolTip("")

    def clear_error_state(self) -> None:
        """Clear all error state visual indicators."""
        self.set_error_state()

    def _on_delete(self) -> None:
        """Request deletion of this row."""
        if PYQT_AVAILABLE:
            self.delete_requested.emit(self.row_index)
