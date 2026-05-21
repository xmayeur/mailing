"""Tests for filter persistence to profile config."""
import pytest
from src.filter_persistence import FilterPersistence


class TestFilterPersistence:
    """Test saving/restoring filters to profile configuration."""

    def test_save_filter_to_profile(self):
        """Save active filter criteria to profile config."""
        config = {"name": "test_profile"}
        persistence = FilterPersistence(config)

        criteria = {"status": "active", "domain": "example.com"}
        persistence.save_filter(criteria)

        assert config["filters"]["criteria"] == criteria
        assert config["filters"]["active"] is True

    def test_load_filter_from_profile(self):
        """Load saved filters from profile on initialization."""
        config = {
            "name": "test_profile",
            "filters": {"criteria": {"status": "active"}, "active": True}
        }
        persistence = FilterPersistence(config)

        result = persistence.load_filters()
        assert result["criteria"]["status"] == "active"

    def test_filter_not_configured_returns_none(self):
        """Load filters returns None if not saved."""
        config = {"name": "test_profile"}
        persistence = FilterPersistence(config)

        result = persistence.load_filters()
        assert result is None

    def test_invalid_filter_criteria_rejected(self):
        """Invalid (empty) filter criteria rejected on save."""
        config = {"name": "test_profile"}
        persistence = FilterPersistence(config)

        with pytest.raises(ValueError, match="Filter criteria cannot be empty"):
            persistence.save_filter({})

    def test_filter_validation_against_schema(self):
        """Validate filter criteria against schema columns."""
        config = {"name": "test_profile"}
        persistence = FilterPersistence(config)

        schema_columns = ["name", "email", "status"]
        criteria = {"status": "active"}

        valid = persistence.validate_filter_criteria(criteria, schema_columns)
        assert valid is True

    def test_filter_validation_missing_column(self):
        """Validation fails if criteria references missing schema column."""
        config = {"name": "test_profile"}
        persistence = FilterPersistence(config)

        schema_columns = ["name", "email", "status"]
        criteria = {"missing_column": "value"}

        valid = persistence.validate_filter_criteria(criteria, schema_columns)
        assert valid is False

    def test_apply_filter_valid_criteria(self):
        """Apply filter with valid criteria."""
        config = {"name": "test_profile"}
        persistence = FilterPersistence(config)

        schema_columns = ["name", "email", "status"]
        criteria = {"status": "active"}

        result = persistence.apply_filter(criteria, schema_columns)
        assert result == criteria

    def test_apply_filter_invalid_criteria_returns_empty(self):
        """Apply filter skips invalid criteria, returns empty dict."""
        config = {"name": "test_profile"}
        persistence = FilterPersistence(config)

        schema_columns = ["name", "email", "status"]
        criteria = {"nonexistent": "value"}

        result = persistence.apply_filter(criteria, schema_columns)
        assert result == {}

    def test_clear_filters(self):
        """User can clear saved filters."""
        config = {
            "name": "test_profile",
            "filters": {"criteria": {"status": "active"}, "active": True}
        }
        persistence = FilterPersistence(config)

        persistence.clear_filters()
        assert "filters" not in config
