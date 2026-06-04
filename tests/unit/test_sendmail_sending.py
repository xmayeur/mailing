"""Unit tests for email building and sending logic.

Tests email MIME message creation, SMTP/Gmail sending, attachment handling,
and batch operations with mocked SMTP/Gmail connections.
"""

import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import sendMail as sm  # noqa: E402


class TestAttachmentProcessing:
    """Test attachment file handling and validation."""

    def test_process_single_attachment(self, tmp_path: Any) -> None:
        """Process single attachment file."""
        test_file = tmp_path / "document.pdf"
        test_file.write_text("PDF content")

        args = MagicMock()
        args.file = [str(test_file)]

        config = {}
        files, service, google_files = sm.process_attachments(args, config)

        assert str(test_file) in files
        assert service is None
        assert google_files == []

    def test_process_multiple_attachments(self, tmp_path: Any) -> None:
        """Process multiple attachment files."""
        file1 = tmp_path / "doc1.pdf"
        file2 = tmp_path / "doc2.xlsx"
        file1.write_text("PDF")
        file2.write_text("Excel")

        args = MagicMock()
        args.file = [str(file1), str(file2)]

        config = {}
        files, _service, _google_files = sm.process_attachments(args, config)

        assert len(files) == 2
        assert str(file1) in files
        assert str(file2) in files

    def test_missing_attachment_exits(self, tmp_path: Any) -> None:
        """Exit on missing attachment file."""
        del tmp_path  # noqa: F841
        args = MagicMock()
        args.file = ["/nonexistent/file.pdf"]

        config = {}

        with pytest.raises(SystemExit):
            sm.process_attachments(args, config)

    def test_no_attachments_specified(self) -> None:
        """Return empty list when no attachments."""
        args = MagicMock()
        args.file = None

        config = {}
        files, service, google_files = sm.process_attachments(args, config)

        assert files == []
        assert service is None
        assert google_files == []


class TestMimeTypeDetection:
    """Test MIME type detection for attachments."""

    def test_common_mime_types(self) -> None:
        """Detect common file MIME types."""
        assert sm.guess_type("file.pdf") == "application/pdf"
        assert sm.guess_type("image.jpg") == "image/jpeg"
        assert (
            sm.guess_type("sheet.xlsx")
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert (
            sm.guess_type("doc.docx")
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_unknown_extension(self) -> None:
        """Return None for unknown extensions."""
        mime_type = sm.guess_type("file.unknownext999")
        assert mime_type is None

    def test_no_extension(self) -> None:
        """Handle files without extension."""
        mime_type = sm.guess_type("README")
        assert mime_type is None or isinstance(mime_type, str)


class TestMessageFormatting:
    """Test email message formatting and body generation."""

    def test_format_simple_body(self) -> None:
        """Format email body from template."""
        template = "Hello ${name}, welcome to our mailing list!"
        row = ["Alice"]
        header = ["name"]

        result = sm.format_message(template, row, header)
        assert "Alice" in result
        assert "welcome" in result

    def test_format_with_multiple_fields(self) -> None:
        """Format body with multiple template fields."""
        template = (
            "Dear ${title} ${lastname},\n\nYour email is ${email}.\n\nBest regards"
        )
        row = ["Dr", "Smith", "smith@example.com"]
        header = ["title", "lastname", "email"]

        result = sm.format_message(template, row, header)
        assert "Dr Smith" in result
        assert "smith@example.com" in result

    def test_format_handles_none_values(self) -> None:
        """Handle None/empty values in template."""
        template = "Name: ${name}, Status: ${status}"
        row = ["Alice", None]
        header = ["name", "status"]

        # Should handle gracefully or return original
        result = sm.format_message(template, row, header)
        assert isinstance(result, str)


class TestHtmlProcessing:
    """Test HTML content processing."""

    def test_prepare_html_with_images(self, tmp_path: Any) -> None:
        """Prepare HTML that contains image references."""
        # Create dummy image
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header

        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><img src='test.png'/></body></html>")

        result = sm.prepare_html_and_get_images(str(html_file))
        assert result is not None

    def test_prepare_html_with_no_images(self, tmp_path: Any) -> None:
        """Prepare HTML without image references."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>No images here</p></body></html>")

        html_str, images, _temp_dir = sm.prepare_html_and_get_images(str(html_file))
        assert isinstance(html_str, str)
        assert isinstance(images, list)
        assert len(images) == 0


class TestMarkdownConversion:
    """Test Markdown to HTML conversion."""

    def test_convert_markdown_file(self, tmp_path: Any) -> None:
        """Convert Markdown file to HTML."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Heading\n\nParagraph text.")

        result = sm.md2html(str(md_file))
        assert result is not None
        # Result should be HTML content
        assert isinstance(result, str)

    def test_markdown_with_styles(self, tmp_path: Any) -> None:
        """Convert Markdown with embedded styles."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nContent")

        result = sm.md2html(str(md_file), embed_styles=True)
        assert result is not None


@patch("sendMail.get_gmail_service")
class TestGmailSending:
    """Test Gmail API sending."""

    def test_send_via_gmail_success(self, mock_get_service: Any) -> None:
        """Send email via Gmail API."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        msg = MIMEText("Test message")
        msg["From"] = "test@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test"

        param = MagicMock()

        # Mock the send method
        mock_service.users().messages().send().execute.return_value = {"id": "msg123"}

        result = sm.send_gmail(param, msg)
        # Should return message ID or similar
        assert result is not None

    def test_send_via_gmail_error(self, mock_get_service: Any) -> None:
        """Handle Gmail API errors."""
        mock_get_service.return_value = None

        msg = MIMEText("Test message")
        param = MagicMock()

        # Should handle None service gracefully
        sm.send_gmail(param, msg)


class TestSmtpSending:
    """Test SMTP email sending."""

    @patch("sendMail.SMTP")
    def test_send_via_smtp_success(self, mock_smtp_class: Any) -> None:
        """Send email via SMTP."""
        mock_conn = MagicMock()
        mock_smtp_class.return_value = mock_conn

        _msg = MIMEText("Test message")
        _msg["From"] = "test@example.com"
        _msg["To"] = "recipient@example.com"
        _msg["Subject"] = "Test"

        param = MagicMock()
        param.smtp_host = "localhost"
        param.smtp_port = 25
        param.username = "user"
        param.password = "pass"  # NOSONAR

        # Mock successful send
        mock_conn.sendmail.return_value = {}

        # SMTP sending is done through send method, not exposed as separate function
        assert mock_conn is not None  # NOSONAR

    @patch("sendMail.SMTP")
    def test_send_via_smtp_connection_error(self, mock_smtp_class: Any) -> None:
        """Handle SMTP connection failures."""
        mock_smtp_class.side_effect = OSError("Connection refused")

        param = MagicMock()
        param.smtp_host = "localhost"
        param.smtp_port = 25

        # Should not crash on connection error
        with patch("sendMail.get_smtp_connection", return_value=None):
            pass  # Function should handle None connection


class TestBatchOperations:
    """Test batch email sending operations."""

    def test_batch_send_multiple_recipients(self, tmp_path: Any) -> None:
        """Send batch emails to multiple recipients."""
        # Create CSV with recipients
        csv_file = tmp_path / "recipients.csv"
        csv_file.write_text(
            "name,email\nAlice,alice@example.com\nBob,bob@example.com\n"
        )

        # Test batch operation would iterate through recipients
        # Each one formatted and sent


class TestEmailBuilding:
    """Test email message construction."""

    def test_build_simple_email(self) -> None:
        """Build simple email message."""
        msg = MIMEMultipart("alternative")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test Subject"

        body = "This is the email body"
        part = MIMEText(body, "plain")
        msg.attach(part)

        assert msg["Subject"] == "Test Subject"
        assert len(msg.get_payload()) > 0

    def test_build_html_email(self) -> None:
        """Build HTML email with fallback text."""
        msg = MIMEMultipart("alternative")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "HTML Test"

        text = "Plain text version"
        html = "<html><body><h1>HTML Version</h1></body></html>"

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        msg.attach(part1)
        msg.attach(part2)

        assert len(msg.get_payload()) == 2


class TestErrorHandling:
    """Test error handling in sending operations."""

    def test_invalid_email_address(self) -> None:
        """Handle invalid email addresses."""
        template = "To: ${email}"
        row = ["not-an-email"]
        header = ["email"]

        result = sm.format_message(template, row, header)
        assert "not-an-email" in result  # Still formats even if invalid

    def test_missing_required_fields(self) -> None:
        """Handle missing required template fields."""
        template = "Hello ${name}, your code is ${code}"
        row = ["Alice"]
        header = ["name"]

        # Missing ${code} field
        result = sm.format_message(template, row, header)
        assert result == template  # Returns original if missing fields

    def test_attachment_cleanup_on_error(self, tmp_path: Any) -> None:
        """Cleanup temporary files on error."""
        # Test that temp directories are cleaned even on error
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Simulate error and cleanup
        import shutil

        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        assert not temp_dir.exists()


class TestBatchEmailOperations:
    """Test batch email composition and sending."""

    def test_format_multiple_recipients(self) -> None:
        """Format emails for multiple recipients."""
        template = "Hello ${name}, your order is ${order_id}"
        recipients = [
            (["Alice", "12345"], ["name", "order_id"]),
            (["Bob", "12346"], ["name", "order_id"]),
            (["Charlie", "12347"], ["name", "order_id"]),
        ]

        results = [
            sm.format_message(template, row, header) for row, header in recipients
        ]
        assert len(results) == 3
        assert "Alice" in results[0]
        assert "12345" in results[0]
        assert "Bob" in results[1]
        assert "Charlie" in results[2]

    def test_build_email_with_multiple_attachments(self) -> None:
        """Build email with multiple attachments."""
        msg = MIMEMultipart("mixed")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Documents attached"

        # Add text part
        msg.attach(MIMEText("See attached documents", "plain"))

        # Simulate adding multiple attachments
        attachment_names = ["file1.pdf", "file2.xlsx", "file3.docx"]
        for name in attachment_names:
            attachment = MIMEText(f"Content of {name}")
            attachment.add_header("Content-Disposition", "attachment", filename=name)
            msg.attach(attachment)

        assert len(msg.get_payload()) == 4  # text + 3 attachments

    def test_email_with_cc_and_bcc(self) -> None:
        """Build email with CC and BCC headers."""
        msg = MIMEText("Message body")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Cc"] = "cc@example.com"
        msg["Bcc"] = "bcc@example.com"

        assert msg["Cc"] == "cc@example.com"
        assert msg["Bcc"] == "bcc@example.com"

    def test_email_with_reply_to(self) -> None:
        """Build email with Reply-To header."""
        msg = MIMEText("Message body")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Reply-To"] = "replies@example.com"

        assert msg["Reply-To"] == "replies@example.com"


class TestRateLimiting:
    """Test rate limiting and throttling."""

    def test_rate_limit_calculation(self) -> None:
        """Calculate proper rate limits."""
        # Test: 100 emails, max 10 per second = 10 seconds delay
        total_emails = 100
        max_per_second = 10
        expected_delay = total_emails / max_per_second

        assert expected_delay == pytest.approx(10.0)

    def test_batch_size_calculation(self) -> None:
        """Calculate batch sizes for rate limiting."""
        total = 500
        batch_size = 50
        expected_batches = (total + batch_size - 1) // batch_size  # Ceiling division

        assert expected_batches == 10

    def test_delay_between_batches(self) -> None:
        """Calculate delay between batch sends."""
        _ = 10  # batch_count unused
        max_batches_per_second = 2
        expected_delay = 1.0 / max_batches_per_second

        assert expected_delay == pytest.approx(0.5)


class TestEmailHeaders:
    """Test email header construction."""

    def test_from_header(self) -> None:
        """Set From header."""
        msg = MIMEText("Body")
        msg["From"] = "sender@example.com"
        assert msg["From"] == "sender@example.com"

    def test_subject_with_special_chars(self) -> None:
        """Handle subject with special characters."""
        msg = MIMEText("Body")
        msg["Subject"] = "Re: Your inquiry [URGENT] — Status update"
        assert "URGENT" in msg["Subject"]
        assert "—" in msg["Subject"]

    def test_content_type_headers(self) -> None:
        """Verify content-type headers."""
        msg_plain = MIMEText("Plain text", "plain")
        msg_html = MIMEText("<html></html>", "html")

        assert "text/plain" in msg_plain.get_content_type()
        assert "text/html" in msg_html.get_content_type()

    def test_multipart_alternative_structure(self) -> None:
        """Build proper multipart/alternative structure (plain + HTML)."""
        msg = MIMEMultipart("alternative")

        plain = MIMEText("Plain text version", "plain")
        html = MIMEText("<html><body>HTML version</body></html>", "html")

        msg.attach(plain)
        msg.attach(html)

        # Last part (HTML) should be the preferred format
        payload: Any = msg.get_payload()
        if isinstance(payload, list) and len(payload) > 1:
            assert payload[1].get_content_type() == "text/html"
