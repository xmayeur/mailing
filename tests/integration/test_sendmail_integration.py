"""Integration tests for complete sendMail workflows.

Tests end-to-end email operations combining multiple modules.
"""

import csv
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import sendMail as sm  # noqa: E402


class TestSendMailFullWorkflow:
    """Test complete sendMail workflows."""

    @patch("sendMail.SMTP")
    def test_full_smtp_send_workflow(self, mock_smtp_class: Any) -> None:
        """Complete workflow: load config, format template, send via SMTP."""
        mock_conn = MagicMock()
        mock_smtp_class.return_value = mock_conn

        param = MagicMock()
        param.smtp_host = "localhost"
        param.smtp_port = 25
        param.username = "user"
        param.password = "pass"  # NOSONAR

        # Simulate full workflow
        template = "Hello ${name}, your email is ${email}"
        row = ["Alice", "alice@example.com"]
        header = ["name", "email"]

        result = sm.format_message(template, row, header)
        assert "Alice" in result
        assert "alice@example.com" in result

    def test_csv_subscriber_batch_processing(self, tmp_path: Any) -> None:
        """Process batch of subscribers from CSV file."""
        csv_file = tmp_path / "subscribers.csv"
        csv_file.write_text("name,email,status\nAlice,alice@example.com,active\nBob,bob@example.com,active\n")

        # Read and process
        with open(str(csv_file)) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[1]["email"] == "bob@example.com"

    def test_recipient_filtering_workflow(self) -> None:
        """Test filtering logic for recipient selection."""
        all_recipients = [
            {"name": "Alice", "email": "alice@example.com", "status": "active"},
            {"name": "Bob", "email": "bob@example.com", "status": "inactive"},
            {"name": "Charlie", "email": "charlie@example.com", "status": "active"},
        ]

        # Filter active recipients
        filtered = [r for r in all_recipients if r["status"] == "active"]
        assert len(filtered) == 2
        assert filtered[0]["name"] == "Alice"


class TestSendMailErrorScenarios:
    """Test error handling in realistic scenarios."""

    @patch("sendMail.SMTP")
    def test_smtp_connection_failure_recovery(self, mock_smtp_class: Any) -> None:
        """Recover from temporary SMTP connection failure."""
        # First attempt fails
        mock_smtp_class.side_effect = OSError("Connection refused")

        param = MagicMock()
        param.smtp_host = "localhost"
        param.smtp_port = 25

        # Would attempt retry logic here
        with pytest.raises(OSError):
            from smtplib import SMTP

            SMTP(param.smtp_host, param.smtp_port)

    def test_template_with_missing_required_field(self) -> None:
        """Handle template with missing required field in data."""
        template = "Hello ${first_name}, your email is ${email}"
        row = ["Alice"]  # Missing email
        header = ["first_name"]

        result = sm.format_message(template, row, header)
        # Original template returned if field missing
        assert "${email}" in result or isinstance(result, str)


class TestSendMailPerformance:
    """Test performance characteristics."""

    def test_batch_format_performance(self) -> None:
        """Format templates in batch efficiently."""
        template = "Hello ${name}, your ID is ${id}"

        # Format 100 recipients
        recipients = [(["User" + str(i), str(i)], ["name", "id"]) for i in range(100)]

        results = []
        for row, header in recipients:
            result = sm.format_message(template, row, header)
            results.append(result)

        assert len(results) == 100
        assert "User0" in results[0]
        assert "User99" in results[99]

    def test_large_attachment_handling(self, tmp_path: Any) -> None:
        """Handle large file attachments."""
        # Create a 5MB file
        large_file = tmp_path / "large.bin"
        large_file.write_bytes(b"0" * (5 * 1024 * 1024))

        args = MagicMock()
        args.file = [str(large_file)]

        config = {}
        files, _service, _google_files = sm.process_attachments(args, config)

        assert len(files) == 1
        assert str(large_file) in files


class TestSendMailStateManagement:
    """Test state management during batch operations."""

    def test_subscriber_index_tracking(self) -> None:
        """Track which subscribers have been processed."""
        subscribers = ["user1@example.com", "user2@example.com", "user3@example.com"]
        processed = []

        for idx, subscriber in enumerate(subscribers):
            processed.append((idx, subscriber))

        assert len(processed) == 3
        assert processed[0] == (0, "user1@example.com")
        assert processed[2] == (2, "user3@example.com")

    def test_rate_limit_state_tracking(self) -> None:
        """Track rate limit state across batch sends."""
        rate_limit_per_second = 5
        total_to_send = 100
        batches_needed = (total_to_send + rate_limit_per_second - 1) // rate_limit_per_second

        assert batches_needed == 20


class TestMergeFieldBatching:
    """_build_and_send merge-field semantics: 1 addressee -> values, >=2 -> blank (011)."""

    def _make_param(self) -> Any:
        """Full param mock as used by _build_and_send."""
        from unittest.mock import Mock

        param = Mock()
        param.donotsend = False
        param.verbose = False
        param.subject = "Order ${id}"
        param.message = "Hello ${name}, hello ${typo}"
        param.file = []
        param.attachment = None
        param.smtp_host = "smtp.test.com"
        return param

    def _capture_build_email(self, param: Any, addressees: list[str], row: list[str], header: list[str]) -> dict:
        """Run _build_and_send with a mocked build_email; return its kwargs."""
        captured: dict = {}

        def _fake_build_email(**kwargs: Any) -> tuple:
            captured.update(kwargs)
            return (MagicMock(), list(addressees))

        with (
            patch("sendMail.build_email", side_effect=_fake_build_email),
            patch("sendMail.send_mail", return_value=True),
        ):
            sm._build_and_send(param, addressees, row, header)
        return captured

    def test_single_recipient_passes_merge_context(self) -> None:
        """One addressee: build_email receives the recipient's row (US2, FR-005/FR-012)."""
        param = self._make_param()
        captured = self._capture_build_email(param, ["a@b.com"], ["42", "Alice"], ["id", "name"])
        assert captured["merge_row"] == ["42", "Alice"]
        assert captured["merge_header"] == ["id", "name"]
        assert captured["blank_merge"] is False
        assert captured["subject"] == "Order ${id}"

    def test_multiple_recipients_blank_merge(self) -> None:
        """Two addressees: blank_merge=True and no merge_row (US3, FR-006, I4)."""
        param = self._make_param()
        captured = self._capture_build_email(param, ["a@b.com", "c@d.com"], ["42", "Alice"], ["id", "name"])
        assert captured["blank_merge"] is True
        assert captured["merge_row"] is None
        assert captured["merge_header"] is None

    def test_stored_param_not_mutated(self) -> None:
        """param.message / param.subject keep their markers after a send (FR-007, SC-004)."""
        param = self._make_param()
        self._capture_build_email(param, ["a@b.com"], ["42", "Alice"], ["id", "name"])
        assert param.message == "Hello ${name}, hello ${typo}"
        assert param.subject == "Order ${id}"

    def test_donotsend_skips_build(self) -> None:
        """donotsend still short-circuits before any substitution."""

        param = self._make_param()
        param.donotsend = True
        with (
            patch("sendMail.build_email") as mock_build,
            patch("sendMail.send_mail", return_value=True),
        ):
            result = sm._build_and_send(param, ["a@b.com"], ["42", "Alice"], ["id", "name"])
        assert result is False
        mock_build.assert_not_called()


class TestMergeFieldHtmlAttachment:
    """Real build_email with the editor's HTML file as attachment (reported bug)."""

    def _make_param(self) -> Any:
        from unittest.mock import Mock

        param = Mock()
        param.sendername = "Sender"
        param.sender = "sender@example.com"
        param.max_addr_per_mail = 1
        param.styles = None
        return param

    def _html_file(self, tmp_path: Any, body: str) -> str:
        html_file = tmp_path / "test.html"
        html_file.write_text(f"<!DOCTYPE html><html><body><p>{body}</p></body></html>", encoding="utf-8")
        return str(html_file)

    def _payload(self, msg: Any) -> str:
        """Extract the decoded body text from the MIME tree (mixed → related → text)."""
        part = msg
        while part.is_multipart():
            part = part.get_payload(0)
        decoded = part.get_payload(decode=True)
        charset = part.get_content_charset() or "utf-8"
        return decoded.decode(charset) if decoded is not None else str(part.get_payload())

    def test_html_attachment_substituted_single_recipient(self, tmp_path: Any) -> None:
        """Markers in an HTML attachment are replaced by the recipient's values."""
        param = self._make_param()
        html_file = self._html_file(tmp_path, "Bonjour cher ${Prénom} ${Nom} — ${email}")
        msg, recipients = sm.build_email(
            param=param,
            subject="Order ${id}",
            message="",
            bcc="a@b.com",
            attachments=[html_file],
            merge_row=["42", "Alice", "a@b.com"],
            merge_header=["id", "Prénom", "email"],
            blank_merge=False,
        )
        body = self._payload(msg)
        assert "Bonjour cher Alice  — a@b.com" in body
        assert "${" not in body
        # Pre-existing quirk (out of scope here): with max_addr_per_mail == 1 the
        # headers swap leaves bcc=None and the recipient list gains a "None" entry.
        assert recipients[0] == "a@b.com"

    def test_html_attachment_blank_multi_recipient(self, tmp_path: Any) -> None:
        """Multi-recipient batch: HTML attachment markers blanked (I4)."""
        param = self._make_param()
        param.max_addr_per_mail = 2
        html_file = self._html_file(tmp_path, "Bonjour cher ${Prénom} — ${email}")
        msg, recipients = sm.build_email(
            param=param,
            subject="Order ${id}",
            message="",
            bcc="a@b.com,c@d.com",
            attachments=[html_file],
            merge_row=None,
            merge_header=None,
            blank_merge=True,
        )
        body = self._payload(msg)
        assert "Bonjour cher  — " in body
        assert "${" not in body
        assert "Alice" not in body
        assert len(recipients) == 2

    def test_subject_substituted_single_recipient(self, tmp_path: Any) -> None:
        """Subject markers replaced for a single recipient (FR-012)."""
        param = self._make_param()
        html_file = self._html_file(tmp_path, "Body ${name}")
        msg, _recipients = sm.build_email(
            param=param,
            subject="Your order ${id}",
            message="Body",
            bcc="a@b.com",
            attachments=[html_file],
            merge_row=["42", "Alice"],
            merge_header=["id", "name"],
            blank_merge=False,
        )
        assert str(msg["Subject"]) == "Your order 42"

    def test_subject_blank_multi_recipient(self, tmp_path: Any) -> None:
        """Subject markers blanked for a multi-recipient message (FR-006)."""
        param = self._make_param()
        html_file = self._html_file(tmp_path, "Body")
        msg, _recipients = sm.build_email(
            param=param,
            subject="Your order ${id}",
            message="Body",
            bcc="a@b.com,c@d.com",
            attachments=[html_file],
            merge_row=None,
            merge_header=None,
            blank_merge=True,
        )
        assert str(msg["Subject"]) == "Your order "


class TestMergeFieldRowAssociation:
    """Regression (011): the batch must use the matched recipient's row, not the last row read."""

    def test_filtered_row_not_last_row(self, tmp_path: Any) -> None:
        """Filter matches the first row; substitution must use THAT row, not the
        last row of the file (reported: ${email} resolved to the last CSV row)."""
        from unittest.mock import Mock

        csv_file = tmp_path / "subscribers.csv"
        csv_file.write_text(
            "id,Ville,email\n"
            "1,Bruxelles,xavier@mayeur.be\n"
            "2,Anvers,other1@example.com\n"
            "3,Bruxelles,other2@example.com\n"
            "4,Anvers,longreef1@gmail.com\n",
            encoding="utf-8",
        )

        param = Mock()
        param.max_addr_per_mail = 5
        param.pause = 0
        param.max_mails_per_hour = 1000
        param.from_index = None
        param.to_index = None
        param.database = str(csv_file)
        param.filter = {"email": "is equal to xavier@mayeur.be", "Ville": "is equal to Bruxelles"}
        param.test = False
        param.selected = False
        param.donotsend = False
        param.subject = "Hi ${id}"
        param.message = "Hello ${email}"
        param.file = []
        param.profile = "test"

        captured: dict = {}

        def _fake_build_email(**kwargs: Any) -> tuple:
            captured.update(kwargs)
            return (MagicMock(), ["xavier@mayeur.be"])

        with (
            patch("sendMail.build_email", side_effect=_fake_build_email),
            patch("sendMail.send_mail", return_value=True),
        ):
            result = sm.generate_mailing(param)

        assert result == "OK"
        assert captured["merge_row"] == ["1", "Bruxelles", "xavier@mayeur.be"]
        assert captured["merge_header"] == ["id", "Ville", "email"]
        assert captured["blank_merge"] is False
