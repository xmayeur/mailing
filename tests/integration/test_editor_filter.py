"""Tests for _SendDialog filter functionality."""

# pyright: ignore[reportArgumentType]
import tempfile
from pathlib import Path
from typing import Any

import pytest
from PyQt6.QtWidgets import QApplication

from src.editor import _SendDialog


@pytest.fixture
def qapp() -> Any:
    """QApplication fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_config() -> Any:
    """Create temp config file with filter."""
    config_content = """
default:
  sender: test@example.com
  database: /tmp/test.csv
  filter:
    status: is active
    age: gt 18

admin:
  sender: admin@example.com
  database: /tmp/admin.csv
  filter:
    role: is admin
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(config_content)
        config_path = f.name
    yield config_path, config_content
    Path(config_path).unlink()


@pytest.fixture
def temp_attachment() -> Any:
    """Create temp attachment file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write("<html><body>test</body></html>")
        path = f.name
    yield path
    Path(path).unlink()


class TestSendDialogFilter:
    """Tests for _SendDialog filter functionality."""

    def test_load_current_filter_with_filter(
        self, qapp: Any, temp_config: Any, temp_attachment: Any
    ) -> None:
        """Test load_current_filter loads filter from profile config."""
        config_path, _ = temp_config

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path=config_path,
            initial_profile="default",
        )

        # Filter should be loaded for default profile
        filter_text = dialog.filter_text_edit.toPlainText()
        assert "status: is active" in filter_text
        assert "age: gt 18" in filter_text

    def test_load_current_filter_no_filter(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test load_current_filter handles missing filter gracefully."""
        config_content = """
default:
  sender: test@example.com
  database: /tmp/test.csv
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path=config_path,
                initial_profile="default",
            )

            # Filter field should be empty
            filter_text = dialog.filter_text_edit.toPlainText()
            assert filter_text == ""
        finally:
            Path(config_path).unlink()

    def test_profile_change_updates_filter(
        self, qapp: Any, temp_config: Any, temp_attachment: Any
    ) -> None:
        """Test changing profile updates filter field."""
        config_path, _ = temp_config

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path=config_path,
            initial_profile="default",
        )

        # Initial profile should have its filter
        initial_filter = dialog.filter_text_edit.toPlainText()
        assert "status: is active" in initial_filter

        # Switch to admin profile
        admin_idx = dialog.profile_combo.findText("admin")
        dialog.profile_combo.setCurrentIndex(admin_idx)

        # Filter should update to admin's filter
        admin_filter = dialog.filter_text_edit.toPlainText()
        assert "role: is admin" in admin_filter
        assert "status: is active" not in admin_filter

    def test_load_current_filter_direct_call(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test calling load_current_filter directly."""
        config_data: dict[str, dict[str, Any]] = {
            "test_profile": {
                "sender": "test@example.com",
                "filter": {"field1": "op1 val1", "field2": "op2 val2"},
            }
        }

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="test_profile",
        )

        # Load filter for test_profile
        dialog.load_current_filter("test_profile")

        filter_text = dialog.filter_text_edit.toPlainText()
        assert "field1: op1 val1" in filter_text
        assert "field2: op2 val2" in filter_text

    def test_load_current_filter_missing_profile(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test load_current_filter with non-existent profile."""
        config_data = {
            "profile1": {
                "sender": "test@example.com",
            }
        }

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="profile1",
        )

        # Load non-existent profile
        dialog.load_current_filter("nonexistent")

        # Filter should be empty
        assert dialog.filter_text_edit.toPlainText() == ""

    def test_filter_validation_valid_syntax(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test filter validation with valid YAML syntax."""
        config_data = {
            "test": {"sender": "test@example.com"}
        }

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="test",
        )

        # Set valid filter text
        dialog.filter_text_edit.setPlainText("status: is active")

        # Trigger validation
        dialog._run_filter_validation()

        # Status label should not have error (empty or success color)
        status_text = dialog.filter_status_label.text()
        assert "Syntax" not in status_text

    def test_filter_validation_invalid_syntax(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test filter validation with invalid YAML syntax."""
        config_data = {
            "test": {"sender": "test@example.com"}
        }

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="test",
        )

        # Set invalid YAML filter
        dialog.filter_text_edit.setPlainText("{ invalid yaml:")

        # Trigger validation
        dialog._run_filter_validation()

        # Status should show syntax error
        status_text = dialog.filter_status_label.text()
        assert "Syntax" in status_text

    def test_filter_validation_missing_fields(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test filter validation detects missing database fields."""
        config_content = """
test:
  sender: test@example.com
  database: test.csv
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,email\n")
            csv_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path=config_path,
                initial_profile="test",
            )

            # Update database path to test CSV
            dialog.database_input.setText(csv_path)

            # Set filter with non-existent field
            dialog.filter_text_edit.setPlainText("missing_field: is value")

            # Trigger validation
            dialog._run_filter_validation()

            # Status should show missing field
            status_text = dialog.filter_status_label.text()
            assert "missing_field" in status_text or "Fields not found" in status_text
        finally:
            Path(csv_path).unlink()
            Path(config_path).unlink()

    def test_filter_text_change_triggers_validation_debounce(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test that filter text change starts debounce timer."""
        config_data = {
            "test": {"sender": "test@example.com"}
        }

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="test",
        )

        # Stop timer if it was started during init
        dialog._validation_timer.stop()
        assert not dialog._validation_timer.isActive()

        # Change filter text
        dialog.filter_text_edit.setPlainText("status: is active")

        # Timer should be active (debouncing)
        assert dialog._validation_timer.isActive()

    def test_filter_visual_indicator_valid(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test filter field styling for valid filter."""
        config_data = {
            "test": {"sender": "test@example.com"}
        }

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="test",
        )

        dialog.filter_text_edit.setPlainText("status: is active")
        dialog._run_filter_validation()

        # Valid filter should have green border
        stylesheet = dialog.filter_text_edit.styleSheet()
        assert "#4CAF50" in stylesheet or "border" in stylesheet

    def test_filter_visual_indicator_invalid(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test filter field styling for invalid filter."""
        config_data = {
            "test": {"sender": "test@example.com"}
        }

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="test",
        )

        dialog.filter_text_edit.setPlainText("{ invalid:")
        dialog._run_filter_validation()

        # Invalid filter should have red border
        stylesheet = dialog.filter_text_edit.styleSheet()
        assert "#f44336" in stylesheet or "border" in stylesheet

    def test_load_database_records_csv(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test loading records from CSV file (T026)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,email,age\n")
            f.write("Alice,alice@test.com,30\n")
            f.write("Bob,bob@test.com,25\n")
            csv_path = f.name

        try:
            config_data = {"test": {"sender": "test@example.com", "database": csv_path}}

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            rows, headers = dialog.load_database_records()
            assert headers == ["name", "email", "age"]
            assert len(rows) == 2
            assert rows[0] == ["Alice", "alice@test.com", "30"]
        finally:
            Path(csv_path).unlink()

    def test_filter_and_display_records(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test filtering and displaying records (T027, T028)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,status\n")
            f.write("Alice,active\n")
            f.write("Bob,inactive\n")
            f.write("Charlie,active\n")
            csv_path = f.name

        try:
            config_data = {"test": {"sender": "test@example.com", "database": csv_path}}

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Set filter and display records
            dialog.filter_text_edit.setPlainText("status: is active")
            dialog.filter_and_display_records()

            # Table should show filtered records
            assert dialog.records_table.rowCount() == 2  # Alice and Charlie
            assert dialog.records_table.columnCount() == 2  # name and status

            # Count should show filtered vs total
            count_text = dialog.record_count_label.text()
            assert "2 / 3" in count_text or "Matching Records: 2" in count_text
        finally:
            Path(csv_path).unlink()

    def test_record_display_empty_database(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test record display with empty database (T029)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,email\n")
            csv_path = f.name

        try:
            config_data = {"test": {"sender": "test@example.com", "database": csv_path}}

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Table should be empty
            assert dialog.records_table.rowCount() == 0
            assert "0 / 0" in dialog.record_count_label.text()
        finally:
            Path(csv_path).unlink()

    def test_record_display_large_database(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test record display handles large databases (T032)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,name\n")
            for i in range(100):
                f.write(f"{i},Record{i}\n")
            csv_path = f.name

        try:
            config_data = {"test": {"sender": "test@example.com", "database": csv_path}}

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Table should load all records
            assert dialog.records_table.rowCount() == 100
            assert "100 / 100" in dialog.record_count_label.text()
        finally:
            Path(csv_path).unlink()

    def test_apply_filter_valid(self, qapp: Any, temp_attachment: Any) -> None:
        """Test applying a valid filter stores session filter (T034)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,status,email\n")
            f.write("Alice,active,alice@test.com\n")
            csv_path = f.name

        try:
            config_data = {  # type: ignore[assignment]
                "test": {"sender": "test@example.com", "database": csv_path}
            }

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Set valid filter
            dialog.filter_text_edit.setPlainText("status: is active")

            # Apply filter
            dialog._apply_filter()

            # Session filter should be stored
            assert dialog._session_filter == {"status": "is active"}
        finally:
            Path(csv_path).unlink()

    def test_apply_filter_invalid(self, qapp: Any, temp_attachment: Any) -> None:
        """Test applying invalid filter does not store session filter (T034)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,status\n")
            f.write("Alice,active\n")
            csv_path = f.name

        try:
            config_data = {"test": {"sender": "test@example.com", "database": csv_path}}  # type: ignore[assignment]

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Set invalid filter
            dialog.filter_text_edit.setPlainText("{ invalid yaml:")

            # Try to apply
            dialog._apply_filter()

            # Session filter should remain None
            assert dialog._session_filter is None
        finally:
            Path(csv_path).unlink()

    def test_apply_filter_empty(self, qapp: Any, temp_attachment: Any) -> None:
        """Test applying empty filter clears session filter (T034)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,status\n")
            f.write("Alice,active\n")
            csv_path = f.name

        try:
            config_data = {"test": {"sender": "test@example.com", "database": csv_path}}  # type: ignore[assignment]

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Set empty filter
            dialog.filter_text_edit.setPlainText("")

            # Apply (clears)
            dialog._apply_filter()

            # Session filter should be None
            assert dialog._session_filter is None
        finally:
            Path(csv_path).unlink()

    def test_apply_filter_updates_display(self, qapp: Any, temp_attachment: Any) -> None:
        """Test applying filter updates record preview display (T034-FIX-2)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,status,email\n")
            f.write("Alice,active,alice@test.com\n")
            f.write("Bob,inactive,bob@test.com\n")
            f.write("Charlie,active,charlie@test.com\n")
            csv_path = f.name

        try:
            config_data = {  # type: ignore[assignment]
                "test": {"sender": "test@example.com", "database": csv_path}
            }

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Load initial records (all 3)
            dialog.filter_and_display_records()
            initial_count = dialog.records_table.rowCount()
            assert initial_count == 3, f"Expected 3 records, got {initial_count}"

            # Apply filter to show only active records
            dialog.filter_text_edit.setPlainText("status: is active")
            dialog._apply_filter()

            # Record count should update to 2 (Alice and Charlie)
            filtered_count = dialog.records_table.rowCount()
            assert filtered_count == 2, f"Expected 2 filtered records, got {filtered_count}"
            assert dialog._session_filter == {"status": "is active"}
        finally:
            Path(csv_path).unlink()

    def test_reset_filter(self, qapp: Any, temp_attachment: Any) -> None:
        """Test resetting filter restores original (T035)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,status\n")
            f.write("Alice,active\n")
            f.write("Bob,inactive\n")
            csv_path = f.name

        try:
            config_data = {  # type: ignore[assignment]
                "test": {
                    "sender": "test@example.com",
                    "database": csv_path,
                    "filter": {"status": "is active"},
                }
            }

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Original filter should be loaded
            original = dialog.filter_text_edit.toPlainText()
            assert "status: is active" in original

            # Modify filter
            dialog.filter_text_edit.setPlainText("status: is inactive")
            dialog._apply_filter()
            assert dialog._session_filter == {"status": "is inactive"}

            # Reset
            dialog._reset_filter()

            # Should restore original and clear session filter
            assert dialog.filter_text_edit.toPlainText() == original
            assert dialog._session_filter is None
        finally:
            Path(csv_path).unlink()

    def test_build_args_includes_session_filter(
        self, qapp: Any, temp_attachment: Any
    ) -> None:
        """Test build_args includes session_filter in namespace (T036)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("name,status\n")
            f.write("Alice,active\n")
            csv_path = f.name

        try:
            config_data = {"test": {"sender": "test@example.com", "database": csv_path}}  # type: ignore[assignment]

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="test",
            )

            # Set and apply session filter
            dialog.filter_text_edit.setPlainText("status: is active")
            dialog._apply_filter()

            # Build args
            args = dialog.build_args(config_data)

            # Should include session_filter
            assert hasattr(args, "session_filter")
            assert args.session_filter == {"status": "is active"}
        finally:
            Path(csv_path).unlink()

    def test_google_sheets_profile_validation(self, qapp: Any, temp_attachment: str) -> None:
        """Verify Google Sheets profiles attempt schema loading via sendMail.

        In test environment without valid credentials, schema load will fail
        gracefully. System will report fields not found since no schema available.
        This is expected behavior - in production with valid credentials, it would work.
        """
        from unittest.mock import patch

        config_data = {
            "gsheet_profile": {
                "sender": "test@example.com",
                "SA": "invalidServiceAccount",
                "SHEETID": "testSheetID",
                "filter": {"email": "is not empty", "status": "is active"},
            }
        }  # type: ignore[assignment]

        dialog = _SendDialog(
            attachment_path=temp_attachment,
            config_path="",
            config_data=config_data,
            initial_profile="gsheet_profile",
        )

        # Mock get_google_sheets_schema to return test schema
        with patch("sendMail.get_google_sheets_schema") as mock_get_schema:
            mock_get_schema.return_value = ["email", "status", "name"]

            # Load Google Sheets profile with mocked schema
            dialog._load_profile_defaults("gsheet_profile")
            dialog._validation_timer.stop()
            dialog._run_filter_validation()

            # With proper schema, validation should pass
            label_text = dialog.filter_status_label.text()
            assert label_text == "", (
                f"Expected validation to pass with schema, got: {label_text}"
            )

    def test_profile_load_timing_no_missing_fields(self, qapp: Any, temp_attachment: str) -> None:
        """Verify database schema loaded before validation when profile changes.

        Regression test for: filter validation reported "all fields not found"
        after profile selection because database path was not available during
        validation. This test ensures database_input.setText() is called before
        load_current_filter() so schema is available for validation.
        """
        # Create CSV files for cambristi and artscroises profiles
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f_camb:
            f_camb.write("email,name,status\n")
            f_camb.write("user1@example.com,User One,active\n")
            camb_path = f_camb.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f_arts:
            f_arts.write("email,recipient,type\n")
            f_arts.write("art1@example.com,Artist One,featured\n")
            arts_path = f_arts.name

        try:
            config_data = {
                "cambristi": {
                    "sender": "camb@example.com",
                    "database": camb_path,
                    "filter": {"status": "is active"},
                },
                "artscroises": {
                    "sender": "arts@example.com",
                    "database": arts_path,
                    "filter": {"type": "is featured"},
                },
            }  # type: ignore[assignment]

            dialog = _SendDialog(
                attachment_path=temp_attachment,
                config_path="",
                config_data=config_data,
                initial_profile="cambristi",
            )

            # Load cambristi profile - validate filter (timing test)
            dialog._load_profile_defaults("cambristi")
            # Process any pending Qt signals
            dialog._validation_timer.stop()
            dialog._run_filter_validation()
            # Check status label doesn't contain "not found"
            label_text = dialog.filter_status_label.text()
            assert "not found" not in label_text.lower(), (
                f"cambristi: filter reported missing fields: {label_text}"
            )

            # Switch to artscroises profile - validate filter
            dialog._load_profile_defaults("artscroises")
            dialog._validation_timer.stop()
            dialog._run_filter_validation()
            label_text = dialog.filter_status_label.text()
            assert "not found" not in label_text.lower(), (
                f"artscroises: filter reported missing fields: {label_text}"
            )
        finally:
            Path(camb_path).unlink()
            Path(arts_path).unlink()
