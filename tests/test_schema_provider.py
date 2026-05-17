"""Tests for schema_provider module."""

import tempfile
from pathlib import Path

import pytest

from src.schema_provider import DatabaseSchemaProvider


class TestDatabaseSchemaProvider:
    """Tests for DatabaseSchemaProvider class."""

    def test_from_csv_valid(self) -> None:
        """Test extracting schema from valid CSV."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,email,age\n")
            f.write("John,john@example.com,30\n")
            temp_path = f.name

        try:
            headers = DatabaseSchemaProvider.from_csv(temp_path)
            assert headers == ["name", "email", "age"]
        finally:
            Path(temp_path).unlink()

    def test_from_csv_with_whitespace(self) -> None:
        """Test CSV headers with whitespace are trimmed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("  name  , email , age  \n")
            temp_path = f.name

        try:
            headers = DatabaseSchemaProvider.from_csv(temp_path)
            assert headers == ["name", "email", "age"]
        finally:
            Path(temp_path).unlink()

    def test_from_csv_file_not_found(self) -> None:
        """Test handling missing CSV file."""
        headers = DatabaseSchemaProvider.from_csv("/nonexistent/file.csv")
        assert headers == []

    def test_from_csv_empty_file(self) -> None:
        """Test extracting schema from empty CSV."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = f.name

        try:
            headers = DatabaseSchemaProvider.from_csv(temp_path)
            assert headers == []
        finally:
            Path(temp_path).unlink()

    def test_from_csv_single_column(self) -> None:
        """Test CSV with single column."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("email\n")
            f.write("test@example.com\n")
            temp_path = f.name

        try:
            headers = DatabaseSchemaProvider.from_csv(temp_path)
            assert headers == ["email"]
        finally:
            Path(temp_path).unlink()

    def test_from_google_sheets_no_service(self) -> None:
        """Test Google Sheets extraction with no service returns empty."""
        headers = DatabaseSchemaProvider.from_google_sheets(None, "spreadsheet_id")
        assert headers == []

    def test_detect_and_extract_csv(self) -> None:
        """Test auto-detection and extraction for CSV."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,email\n")
            temp_path = f.name

        try:
            headers = DatabaseSchemaProvider.detect_and_extract(temp_path)
            assert headers == ["name", "email"]
        finally:
            Path(temp_path).unlink()

    def test_detect_and_extract_empty_path(self) -> None:
        """Test detection with empty path."""
        headers = DatabaseSchemaProvider.detect_and_extract("")
        assert headers == []

    def test_detect_and_extract_unknown_type(self) -> None:
        """Test detection with unknown file type."""
        headers = DatabaseSchemaProvider.detect_and_extract("/path/to/file.txt")
        assert headers == []
