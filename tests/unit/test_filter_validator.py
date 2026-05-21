"""Tests for filter validation with edge case handling (T044)."""

import pytest

from src.filter_validator import FilterValidator


@pytest.fixture
def validator():
    return FilterValidator()


class TestMalformedYAMLErrorReporting:
    """T044: Malformed YAML should report errors with line information."""

    def test_valid_yaml_returns_dict(self, validator: FilterValidator) -> None:
        """Valid YAML parses successfully."""
        result = validator.parse_yaml_filter("email: test@example.com\nname: John")
        assert result is not None
        assert isinstance(result, dict)

    def test_invalid_yaml_returns_none(self, validator: FilterValidator) -> None:
        """Invalid YAML returns None."""
        result = validator.parse_yaml_filter("email: test\nname: [unclosed list")
        assert result is None

    def test_malformed_yaml_validation_reports_error(
        self, validator: FilterValidator
    ) -> None:
        """Validation status reports syntax errors for malformed YAML."""
        # Missing colon after key
        status = validator.get_validation_status(
            "email test@example.com",  # Missing colon
            ["email", "name"],
        )
        assert not status["is_valid"]
        assert len(status["syntax_errors"]) > 0
        assert (
            "YAML" in status["syntax_errors"][0]
            or "syntax" in status["syntax_errors"][0].lower()
        )

    def test_valid_yaml_shows_no_syntax_error(self, validator: FilterValidator) -> None:
        """Valid YAML shows no syntax errors."""
        status = validator.get_validation_status(
            "email: test@example.com", ["email", "name"]
        )
        # May have missing field errors but not syntax errors
        assert len(status["syntax_errors"]) == 0


class TestUnicodeHandling:
    """T043: Unicode characters should be handled properly."""

    def test_unicode_in_filter_values(self, validator: FilterValidator) -> None:
        """Unicode characters in filter values should work."""
        filter_text = "name: José\nemail: josé@example.com"
        result = validator.parse_yaml_filter(filter_text)
        assert result is not None
        assert result.get("name") == "José"

    def test_special_characters_in_field_names(
        self, validator: FilterValidator
    ) -> None:
        """Field names with special characters should be handled."""
        filter_text = "name_with_underscore: value\nemail-with-dash: test@example.com"
        status = validator.get_validation_status(
            filter_text,
            ["name_with_underscore", "email-with-dash"],
        )
        assert status["is_valid"]


class TestEmptyAndZeroRecords:
    """T042: Empty filters and zero records should display clearly."""

    def test_empty_filter_is_valid(self, validator: FilterValidator) -> None:
        """Empty filter should be valid (apply no filtering)."""
        status = validator.get_validation_status("", ["email", "name"])
        assert status["is_valid"]
        assert len(status["syntax_errors"]) == 0
        assert len(status["missing_fields"]) == 0

    def test_whitespace_only_filter_is_valid(self, validator: FilterValidator) -> None:
        """Whitespace-only filter should be valid."""
        status = validator.get_validation_status("   \n  \t  ", ["email"])
        assert status["is_valid"]
