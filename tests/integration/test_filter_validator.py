"""Tests for filter_validator module."""

import pytest

from src.filter_validator import FilterValidator


class TestFilterValidator:
    """Tests for FilterValidator class."""

    @pytest.fixture
    def validator(self) -> FilterValidator:
        """Fixture: FilterValidator instance."""
        return FilterValidator()

    def test_parse_yaml_filter_valid(self, validator: FilterValidator) -> None:
        """Test parsing valid YAML filter."""
        text = "age: gt 18\nstatus: is active"
        result = validator.parse_yaml_filter(text)
        assert result == {"age": "gt 18", "status": "is active"}

    def test_parse_yaml_filter_empty(self, validator: FilterValidator) -> None:
        """Test parsing empty filter returns empty dict."""
        assert validator.parse_yaml_filter("") == {}
        assert validator.parse_yaml_filter("   ") == {}

    def test_parse_yaml_filter_invalid_syntax(self, validator: FilterValidator) -> None:
        """Test parsing invalid YAML returns None."""
        invalid_yaml = "{ invalid yaml: [unclosed"
        result = validator.parse_yaml_filter(invalid_yaml)
        assert result is None

    def test_parse_yaml_filter_not_dict(self, validator: FilterValidator) -> None:
        """Test parsing non-dict YAML returns None."""
        result = validator.parse_yaml_filter("- item1\n- item2")  # list, not dict
        assert result is None

    def test_validate_field_names_all_valid(self, validator: FilterValidator) -> None:
        """Test validation when all fields exist in schema."""
        filter_dict = {"age": "gt 18", "name": "is John"}
        schema = ["age", "name", "email"]
        missing = validator.validate_field_names(filter_dict, schema)
        assert missing == []

    def test_validate_field_names_missing(self, validator: FilterValidator) -> None:
        """Test validation detects missing fields."""
        filter_dict = {"age": "gt 18", "salary": "gt 50000"}
        schema = ["age", "name"]
        missing = validator.validate_field_names(filter_dict, schema)
        assert set(missing) == {"salary"}

    def test_validate_field_names_empty_filter(self, validator: FilterValidator) -> None:
        """Test validation with empty filter returns no missing."""
        missing = validator.validate_field_names({}, ["age", "name"])
        assert missing == []

    def test_get_validation_status_valid_filter(
        self, validator: FilterValidator
    ) -> None:
        """Test validation status for valid filter."""
        status = validator.get_validation_status("age: gt 18", ["age", "name"])
        assert status["is_valid"] is True
        assert status["syntax_errors"] == []
        assert status["missing_fields"] == []

    def test_get_validation_status_invalid_syntax(
        self, validator: FilterValidator
    ) -> None:
        """Test validation status for invalid YAML syntax."""
        status = validator.get_validation_status("{ bad yaml:", ["age"])
        assert status["is_valid"] is False
        assert len(status["syntax_errors"]) > 0
        assert "Invalid YAML syntax" in status["syntax_errors"][0]

    def test_get_validation_status_missing_fields(
        self, validator: FilterValidator
    ) -> None:
        """Test validation status for missing fields."""
        status = validator.get_validation_status(
            "age: gt 18\nsalary: gt 50000", ["age", "name"]
        )
        assert status["is_valid"] is False
        assert status["missing_fields"] == ["salary"]

    def test_get_validation_status_empty_filter(
        self, validator: FilterValidator
    ) -> None:
        """Test validation status for empty filter."""
        status = validator.get_validation_status("", ["age"])
        assert status["is_valid"] is True
        assert status["syntax_errors"] == []
        assert status["missing_fields"] == []
