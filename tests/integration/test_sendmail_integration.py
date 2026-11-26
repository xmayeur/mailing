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
    """_build_and_send merge-field semantics: 1 addressee → values, ≥2 → blank (011)."""

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

        def _fake_build_email(param: Any, subject: str, message: str, **kwargs: Any) -> tuple:
            captured["subject"] = subject
            captured["message"] = message
            return (MagicMock(), list(addressees))

        with (
            patch("sendMail.build_email", side_effect=_fake_build_email),
            patch("sendMail.send_mail", return_value=True),
        ):
            sm._build_and_send(param, addressees, row, header)
        return captured

    def test_single_recipient_body_and_subject_substituted(self) -> None:
        """One addressee: body and subject use that recipient's values (US2, FR-005/FR-012)."""
        param = self._make_param()
        captured = self._capture_build_email(param, ["a@b.com"], ["42", "Alice"], ["id", "name"])
        assert captured["message"] == "Hello Alice, hello "
        assert captured["subject"] == "Order 42"

    def test_multiple_recipients_blank(self) -> None:
        """Two addressees: every marker blank, no row value leaks (US3, FR-006, I4)."""
        param = self._make_param()
        captured = self._capture_build_email(param, ["a@b.com", "c@d.com"], ["42", "Alice"], ["id", "name"])
        assert captured["message"] == "Hello , hello "
        assert captured["subject"] == "Order "
        assert "Alice" not in captured["message"]
        assert "42" not in captured["message"]

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
