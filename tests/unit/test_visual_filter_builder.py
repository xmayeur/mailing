"""Unit tests for visual_filter_builder module.

Tests FilterRow, FilterTable, DatabaseSchemaInfo, and FilterBuilder classes.
Uses pytest for test execution and assertions.
"""

import os

import pytest

from visual_filter_builder import (
    DatabaseSchemaInfo,
    FilterBuilder,
    FilterRow,
    FilterTable,
)

# Check if Qt can run (needs display server)
QT_AVAILABLE = bool(os.environ.get("DISPLAY") or os.environ.get("QT_QPA_PLATFORM"))


class TestFilterRow:
    """Tests for FilterRow dataclass."""

    def test_create_with_value(self) -> None:
        """Test creating row with value."""
        row = FilterRow("email", "is", "test@example.com")
        assert row.field_name == "email"
        assert row.operator == "is"
        assert row.value == "test@example.com"

    def test_create_without_value(self) -> None:
        """Test creating row without value."""
        row = FilterRow("email", "is not empty")
        assert row.field_name == "email"
        assert row.operator == "is not empty"
        assert row.value is None

    def test_empty_field_raises_error(self) -> None:
        """Test empty field name raises ValueError."""
        with pytest.raises(ValueError, match="field_name cannot be empty"):
            FilterRow("", "is", "value")

    def test_empty_operator_raises_error(self) -> None:
        """Test empty operator raises ValueError."""
        with pytest.raises(ValueError, match="operator cannot be empty"):
            FilterRow("email", "", "value")

    def test_whitespace_trimmed(self) -> None:
        """Test whitespace is trimmed from field and operator."""
        row = FilterRow("  email  ", "  is  ", "value")
        assert row.field_name == "email"
        assert row.operator == "is"


class TestFilterTable:
    """Tests for FilterTable class."""

    def test_create_empty(self) -> None:
        """Test creating empty table."""
        table = FilterTable()
        assert len(table.rows) == 0
        assert table.to_dict() == {}

    def test_add_row(self) -> None:
        """Test adding row."""
        table = FilterTable()
        idx = table.add_row("email", "is not empty")
        assert idx == 0
        assert len(table.rows) == 1
        assert table.rows[0].field_name == "email"

    def test_add_multiple_rows(self) -> None:
        """Test adding multiple rows."""
        table = FilterTable()
        idx1 = table.add_row("email", "is not empty")
        idx2 = table.add_row("status", "is", "active")
        assert idx1 == 0
        assert idx2 == 1
        assert len(table.rows) == 2

    def test_delete_row(self) -> None:
        """Test deleting row."""
        table = FilterTable()
        table.add_row("email", "is not empty")
        table.add_row("status", "is", "active")
        table.delete_row(0)
        assert len(table.rows) == 1
        assert table.rows[0].field_name == "status"

    def test_delete_out_of_range(self) -> None:
        """Test deleting out of range raises error."""
        table = FilterTable()
        with pytest.raises(IndexError):
            table.delete_row(0)

    def test_update_row_field(self) -> None:
        """Test updating row field."""
        table = FilterTable()
        table.add_row("email", "is", "value")
        table.update_row(0, field_name="status")
        assert table.rows[0].field_name == "status"
        assert table.rows[0].operator == "is"
        assert table.rows[0].value == "value"

    def test_update_row_operator(self) -> None:
        """Test updating row operator."""
        table = FilterTable()
        table.add_row("email", "is", "value")
        table.update_row(0, operator="contains")
        assert table.rows[0].field_name == "email"
        assert table.rows[0].operator == "contains"

    def test_update_row_value(self) -> None:
        """Test updating row value."""
        table = FilterTable()
        table.add_row("status", "is", "pending")
        table.update_row(0, value="active")
        assert table.rows[0].value == "active"

    def test_to_dict(self) -> None:
        """Test converting table to dict."""
        table = FilterTable()
        table.add_row("email", "is not empty")
        table.add_row("status", "is", "active")
        result = table.to_dict()
        assert result == {
            "email": "is not empty",
            "status": "is active",
        }

    def test_from_dict(self) -> None:
        """Test parsing dict into table."""
        input_dict = {
            "email": "is not empty",
            "status": "is active",
        }
        table = FilterTable.from_dict(input_dict)
        assert len(table.rows) == 2
        assert table.rows[0].field_name == "email"
        assert table.rows[0].operator == "is not empty"
        assert table.rows[1].field_name == "status"
        assert table.rows[1].operator == "is"
        assert table.rows[1].value == "active"

    def test_dict_roundtrip(self) -> None:
        """Test dict → table → dict roundtrip."""
        original = {
            "email": "is not empty",
            "status": "is active",
            "age": "greater than 18",
        }
        table = FilterTable.from_dict(original)
        result = table.to_dict()
        assert result == original


class TestDatabaseSchemaInfo:
    """Tests for DatabaseSchemaInfo class."""

    def test_create_with_fields(self) -> None:
        """Test creating schema with field names."""
        schema = DatabaseSchemaInfo(["email", "name", "status"])
        assert schema.field_names == ["email", "name", "status"]

    def test_default_all_fields_to_text(self) -> None:
        """Test default field type is text."""
        schema = DatabaseSchemaInfo(["email", "age"])
        assert schema.get_field_type("email") == "text"
        assert schema.get_field_type("age") == "text"

    def test_explicit_field_types(self) -> None:
        """Test setting explicit field types."""
        schema = DatabaseSchemaInfo(
            ["email", "age"],
            {"email": "text", "age": "numeric"},
        )
        assert schema.get_field_type("email") == "text"
        assert schema.get_field_type("age") == "numeric"

    def test_unknown_field_defaults_to_text(self) -> None:
        """Test unknown field defaults to text."""
        schema = DatabaseSchemaInfo(["email"])
        assert schema.get_field_type("unknown_field") == "text"

    def test_text_operators(self) -> None:
        """Test operators for text field."""
        schema = DatabaseSchemaInfo(["email"])
        ops = schema.get_operators_for_field("email")
        assert "Contains" in ops
        assert "Starts with" in ops
        assert "Is empty" in ops
        assert "Is not empty" in ops

    def test_numeric_operators(self) -> None:
        """Test operators for numeric field."""
        schema = DatabaseSchemaInfo(
            ["age"],
            {"age": "numeric"},
        )
        ops = schema.get_operators_for_field("age")
        assert "Greater than" in ops
        assert "Less than" in ops
        assert "Is empty" in ops
        assert "Contains" not in ops


# FilterBuilder tests require Qt display server, skipped in CI/headless environments
# Full functional tests can be added in Phase 3 when running in graphical context
