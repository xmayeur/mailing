"""Unit tests for core sendMail email engine functionality.

Tests recipient filtering, template substitution, email building, and sending logic.
Mocks Google APIs and SMTP connections to avoid external dependencies.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import sendMail as sm  # noqa: E402


class TestGetDefaultConfigPath:
    """Test default configuration path resolution."""

    def test_returns_string(self):
        """get_default_config_path returns a string."""
        path = sm.get_default_config_path()
        assert isinstance(path, str)
        assert len(path) > 0

    def test_contains_sendmail_yml(self):
        """Default path contains sendMail.yml filename."""
        path = sm.get_default_config_path()
        assert "sendMail.yml" in path


class TestFormatMessage:
    """Test template variable substitution."""

    def test_simple_substitution(self):
        """Replace single variable with value."""
        template = "Hello ${name}"
        row = ["Alice"]
        header = ["name"]
        result = sm.format_message(template, row, header)
        assert result == "Hello Alice"

    def test_multiple_substitutions(self):
        """Replace multiple variables in template."""
        template = "Hello ${name}, your email is ${email}"
        row = ["Alice", "alice@example.com"]
        header = ["name", "email"]
        result = sm.format_message(template, row, header)
        assert result == "Hello Alice, your email is alice@example.com"

    def test_missing_variable(self):
        """Return original template if variable not in header."""
        template = "Hello ${name}, age ${age}"
        row = ["Alice"]
        header = ["name"]
        result = sm.format_message(template, row, header)
        assert result == template  # Original unchanged

    def test_empty_row(self):
        """Handle empty row gracefully."""
        template = "Hello ${name}"
        row = []
        header = ["name"]
        result = sm.format_message(template, row, header)
        assert result == template  # Original unchanged

    def test_no_placeholders(self):
        """Return template unchanged if no placeholders."""
        template = "This is a plain text message"
        row = ["Alice"]
        header = ["name"]
        result = sm.format_message(template, row, header)
        assert result == template


class TestGetIndices:
    """Test header to index mapping."""

    def test_simple_header(self):
        """Create mapping from header list."""
        header = ["name", "email", "status"]
        indices = sm.get_indices(header)
        assert indices == {"name": 0, "email": 1, "status": 2}

    def test_empty_header(self):
        """Handle empty header."""
        header = []
        indices = sm.get_indices(header)
        assert indices == {}

    def test_numeric_header(self):
        """Convert numeric headers to strings."""
        header = ["name", 123, "email"]
        indices = sm.get_indices(header)
        assert "123" in indices
        assert indices["123"] == 1


class TestGuessType:
    """Test MIME type detection."""

    def test_pdf_detection(self):
        """Detect PDF files."""
        mime_type = sm.guess_type("document.pdf")
        assert mime_type == "application/pdf"

    def test_image_detection(self):
        """Detect common image types."""
        assert sm.guess_type("image.png") == "image/png"
        assert sm.guess_type("image.jpg") == "image/jpeg"
        assert sm.guess_type("image.gif") == "image/gif"

    def test_text_detection(self):
        """Detect text files."""
        assert sm.guess_type("file.txt") == "text/plain"

    def test_unknown_type(self):
        """Return None for unknown types."""
        mime_type = sm.guess_type("file.unknown")
        assert mime_type is None


class TestFileToBase64:
    """Test file to base64 encoding."""

    def test_encode_small_file(self, tmp_path):
        """Encode small file to base64."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        b64 = sm.file_to_base64(str(test_file))
        assert isinstance(b64, str)
        assert len(b64) > 0
        # Should be valid base64 (only alphanumeric + / + = + whitespace)
        assert all(
            c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n"
            for c in b64
        )

    def test_file_not_found(self):
        """Handle missing file gracefully."""
        with pytest.raises(FileNotFoundError):
            sm.file_to_base64("/nonexistent/file.txt")


class TestGetSubscriberReader:
    """Test subscriber data reader."""

    def test_csv_reader(self, tmp_path):
        """Create CSV reader for subscriber file."""
        csv_file = tmp_path / "subscribers.csv"
        csv_file.write_text("name,email\nAlice,alice@example.com\n")

        param = MagicMock()
        param.database = str(csv_file)

        reader, handle = sm.get_subscriber_reader(param)
        assert reader is not None
        assert handle is not None

        rows = list(reader)
        assert len(rows) >= 2  # Header + at least 1 row

        handle.close()

    def test_missing_database(self):
        """Return None for missing database."""
        param = MagicMock()
        param.database = "/nonexistent/file.csv"

        reader, handle = sm.get_subscriber_reader(param)
        assert reader is None
        assert handle is None

    @patch("sendMail.open_google_db_members_sheet")
    @patch("sendMail.read_all_sheet")
    def test_google_sheets_reader(self, mock_read_sheet, mock_open_sheet):
        """Create reader for Google Sheets."""
        mock_sheet = MagicMock()
        mock_open_sheet.return_value = mock_sheet
        mock_read_sheet.return_value = [
            ["name", "email"],
            ["Alice", "alice@example.com"],
        ]

        param = MagicMock()
        param.database = None
        param.sa = "service_account.json"
        param.sheetid = "sheet123"

        reader, handle = sm.get_subscriber_reader(param)
        assert reader is not None
        assert handle is None


class TestGetSmtpConnection:
    """Test SMTP connection establishment."""

    @patch("sendMail.SMTP")
    def test_successful_connection(self, mock_smtp_class):
        """Create successful SMTP connection."""
        mock_conn = MagicMock()
        mock_smtp_class.return_value = mock_conn

        param = MagicMock()
        param.smtp_host = "localhost"
        param.smtp_port = 25
        param.username = "user"
        param.password = "pass"  # NOSONAR

        conn = sm.get_smtp_connection(param)
        assert conn is not None
        mock_smtp_class.assert_called_once()

    @patch("sendMail.SMTP")
    def test_auth_failure(self, mock_smtp_class):
        """Exit on authentication failure."""
        from smtplib import SMTPAuthenticationError

        mock_conn = MagicMock()
        mock_conn.login.side_effect = SMTPAuthenticationError(
            530, "Authentication required"
        )
        mock_smtp_class.return_value = mock_conn

        param = MagicMock()
        param.smtp_host = "localhost"
        param.smtp_port = 25
        param.username = "user"
        param.password = "badpass"  # NOSONAR

        with pytest.raises(SystemExit):
            sm.get_smtp_connection(param)

    @patch("sendMail.SMTP")
    def test_connection_error(self, mock_smtp_class):
        """Return None on connection error."""
        mock_smtp_class.side_effect = OSError("Connection refused")

        param = MagicMock()
        param.smtp_host = "localhost"
        param.smtp_port = 25
        param.username = "user"
        param.password = "pass"  # NOSONAR

        conn = sm.get_smtp_connection(param)
        assert conn is None


class TestPrepareHtmlForCid:
    """Test HTML preparation for CID image references."""

    def test_prepare_html(self, tmp_path):
        """Prepare HTML with image references."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>Test HTML</p></body></html>")

        result = sm.prepare_html_for_cid(str(html_file))
        # prepare_html_for_cid returns (html_string, images_list) tuple
        assert isinstance(result, (str, tuple))
        if isinstance(result, tuple):
            html_str, images = result
            assert isinstance(html_str, str)
            assert isinstance(images, list)
        else:
            assert len(result) > 0

    def test_nonexistent_file(self):
        """Handle missing HTML file."""
        with pytest.raises(FileNotFoundError):
            sm.prepare_html_for_cid("/nonexistent/file.html")


# Edge cases and integration scenarios
class TestEmailEngineEdgeCases:
    """Test email engine edge cases."""

    def test_empty_subscriber_row(self):
        """Handle empty subscriber row."""
        template = "Hello ${name}"
        row = []
        header = ["name"]
        result = sm.format_message(template, row, header)
        assert result == template

    def test_special_characters_in_data(self):
        """Handle special characters in subscriber data."""
        template = "Hello ${name}, email: ${email}"
        row = ["José García", "josé@españa.es"]
        header = ["name", "email"]
        result = sm.format_message(template, row, header)
        assert "José García" in result
        assert "josé@españa.es" in result

    def test_very_long_subscriber_row(self):
        """Handle large subscriber rows."""
        template = "${col0},${col1},${col5}"
        row = [f"val{i}" for i in range(100)]
        header = [f"col{i}" for i in range(100)]
        result = sm.format_message(template, row, header)
        assert "val0,val1,val5" in result
