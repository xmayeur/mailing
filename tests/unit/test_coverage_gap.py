import os
import sys
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# Add source directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "src")))

# Mock external dependencies before importing sendMail
mock_get_secret = MagicMock(return_value={"key": "value"})
sys.modules["gspread"] = MagicMock()
# Note: do NOT mock "yaml" globally — it's a real installed dependency and
# replacing it in sys.modules pollutes other test modules that import yaml
# (e.g. tests/test_editor.py uses `import yaml as real_yaml`).
# sys.modules['bs4'] = MagicMock()
sys.modules["certifi"] = MagicMock()
sys.modules["getSecrets"] = MagicMock()
sys.modules["getSecrets"].get_secret = mock_get_secret  # type: ignore[attr-defined]
sys.modules["google"] = MagicMock()
sys.modules["google.auth"] = MagicMock()
sys.modules["google.auth.transport"] = MagicMock()
sys.modules["google.auth.transport.requests"] = MagicMock()
sys.modules["google.oauth2"] = MagicMock()
sys.modules["google.oauth2.credentials"] = MagicMock()
sys.modules["google_auth_oauthlib"] = MagicMock()
sys.modules["google_auth_oauthlib.flow"] = MagicMock()
sys.modules["googleapiclient"] = MagicMock()
sys.modules["googleapiclient.discovery"] = MagicMock()
sys.modules["googleapiclient.errors"] = MagicMock()
sys.modules["googleapiclient.http"] = MagicMock()
sys.modules["oauth2client"] = MagicMock()
sys.modules["oauth2client.service_account"] = MagicMock()
sys.modules["PIL"] = MagicMock()

import sendMail  # noqa: E402


class TestCoverageGap:
    """Tests to cover identified gaps in src/sendMail.py"""

    @patch("sendMail.os.path.exists", return_value=True)
    @patch("sendMail.BeautifulSoup")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='<html><img src="http://example.com/img.png"><img src="data:image/png;base64,abc"></html>',
    )
    def test_prepare_html_for_cid_external_and_data(
            self, mock_file, mock_bs, mock_exists
    ):
        """Cover line 198: continue on http or data: images"""
        soup = MagicMock()
        img1 = MagicMock()
        img1.attrs = {"src": "http://example.com/img.png"}
        img2 = MagicMock()
        img2.attrs = {"src": "data:image/png;base64,abc"}
        soup.find_all.return_value = [img1, img2]
        mock_bs.return_value = soup

        html, paths = sendMail.prepare_html_for_cid("test.html")
        assert len(paths) == 0

    @patch("sendMail.open_google_db_members_sheet")
    def test_get_subscriber_reader_google_success(self, mock_open_sheet):
        """Cover line 230: Google Sheets reader"""
        param = Mock()
        param.database = None
        param.sa = "sa"
        param.sheetid = "id"
        mock_wb = Mock()
        mock_open_sheet.return_value = mock_wb

        with patch("sendMail.read_all_sheet", return_value=[["header"], ["row"]]):
            reader, handle = sendMail.get_subscriber_reader(param)
            assert handle is None
            assert list(reader) == [["header"], ["row"]]  # type: ignore[arg-type]

    def test_get_subscriber_reader_file_not_found(self):
        """Cover lines 235-237: FileNotFoundError in subscriber reader"""
        param = Mock()
        param.database = "nonexistent.csv"
        with patch("sendMail.log") as mock_log:
            reader, handle = sendMail.get_subscriber_reader(param)
            assert reader is None
            assert handle is None
            mock_log.critical.assert_called_once()

    @patch("sendMail.SMTP")
    def test_get_smtp_connection_exception(self, mock_smtp):
        """Cover lines 270-272: Exception in SMTP connection"""
        param = Mock()
        param.smtp_host = "host"
        param.smtp_port = 587
        mock_smtp.side_effect = OSError("Connection error")
        with patch("sendMail.log") as mock_log:
            conn = sendMail.get_smtp_connection(param)
            assert conn is None
            mock_log.error.assert_called_once()

    @patch("sendMail.os.path.exists", return_value=True)
    @patch("sendMail.Credentials")
    @patch("sendMail.Request")
    @patch("sendMail.build")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_gmail_service_refresh(
            self, mock_file, mock_build, mock_request, mock_creds, mock_exists
    ):
        """Cover line 299: creds.refresh(Request()) and token write"""
        param = Mock()
        param.token_file = "token.json"
        param.scopes = ["scope"]
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "refresh"
        creds.to_json.return_value = "{}"
        mock_creds.from_authorized_user_file.return_value = creds

        sendMail.get_gmail_service(param)
        creds.refresh.assert_called_once()
        mock_file.assert_called_with("token.json", "w")

    @patch("sendMail.imaplib.IMAP4_SSL")
    def test_save_to_sent_verbose(self, mock_imap_ssl):
        """Cover line 331: verbose logging in _save_to_sent"""
        param = Mock()
        param.verbose = True
        param.imap_host = "host"
        param.imap_port = 993
        param.username = "user"
        param.password = "pass"
        param.sent_folder = "Sent"
        msg = Mock()
        msg.as_string.return_value = "msg"

        mock_imap = MagicMock()
        mock_imap_ssl.return_value = mock_imap

        with patch("sendMail.log") as mock_log:
            sendMail.save_to_sent(param, msg)
            mock_log.info.assert_called_with("stored in sent folder")

    @patch("sendMail.BeautifulSoup")
    @patch("sendMail.tempfile.mkdtemp", return_value="/tmp/dir")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='<html><img src="foo.png"></html>',
    )
    def test_prepare_html_and_get_images_skip_empty_or_external(
            self, mock_file, mock_temp, mock_bs
    ):
        """Cover lines 366-367: skip empty or external images in prepare_html_and_get_images"""
        soup = MagicMock()
        img1 = MagicMock()
        img1.attrs = {"src": ""}
        img2 = MagicMock()
        img2.attrs = {"src": "http://example.com"}
        soup.find_all.return_value = [img1, img2]
        mock_bs.return_value = soup

        html, images, tdir = sendMail.prepare_html_and_get_images("test.html")
        assert len(images) == 0

    @patch("sendMail.Image.open")
    @patch("sendMail.os.path.exists", return_value=True)
    @patch("sendMail.BeautifulSoup")
    @patch("sendMail.tempfile.mkdtemp", return_value="/tmp/dir")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='<html><img src="foo.png"></html>',
    )
    def test_prepare_html_and_get_images_resize_and_error(
            self, mock_file, mock_temp, mock_bs, mock_exists, mock_img_open
    ):
        """Cover lines 377-380 (resize) and 390-393 (exception)"""
        soup = MagicMock()
        img1 = MagicMock()
        img1.attrs = {"src": "resize.png"}
        img2 = MagicMock()
        img2.attrs = {"src": "error.png"}
        soup.find_all.return_value = [img1, img2]
        mock_bs.return_value = soup

        # Image 1: needs resize
        mock_im1 = MagicMock()
        mock_im1.width = 1000
        mock_im1.height = 500
        mock_im1.resize.return_value = mock_im1

        # Provide context manager for Image.open
        def open_side_effect(path):
            if "resize.png" in path:
                ctx = MagicMock()
                ctx.__enter__.return_value = mock_im1
                ctx.__exit__.return_value = False
                return ctx
            raise OSError("Bad image")

        mock_img_open.side_effect = open_side_effect

        with patch("sendMail.log") as mock_log:
            html, images, tdir = sendMail.prepare_html_and_get_images(
                "test.html", max_width=800
            )
            assert len(images) == 1
            mock_im1.resize.assert_called()
            mock_log.error.assert_called_once()

    def test_build_email_variants(self):
        """Cover lines 506-508 (max_addr_per_mail=1), 512 (Cc), 517 (artscroises Message-ID)"""
        param = Mock()
        param.sendername = "Sender"
        param.sender = "sender@example.com"
        param.max_addr_per_mail = 1
        param.domain = "artscroises.be"

        msg, recipients = sendMail.build_email(
            param,
            to="to@example.com",
            cc="cc@example.com",
            bcc="bcc@example.com",
            message="Hi",
        )
        assert msg["To"] == "bcc@example.com"
        assert msg["Cc"] == "cc@example.com"
        assert "artscroises.be" in msg["Message-ID"]

    @patch("sendMail.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"data")
    def test_build_email_attachments(self, mock_file, mock_exists):
        """Cover lines 530-532 (inline images), 547-550 (PDF), 551-552 (TXT)"""
        param = Mock()
        param.sendername = "Sender"
        param.sender = "sender@example.com"
        param.max_addr_per_mail = 10
        param.profile = "other"

        # Test images and attachments
        msg, recipients = sendMail.build_email(
            param,
            message="<html></html>",
            images=["img.png"],
            attachments=["doc.pdf", "notes.txt"],
        )

        # 1 image + 1 html part + 1 pdf + 1 txt = 4 parts expected in some structure
        # Mixed -> [Related -> [HTML, Image], PDF, TXT]
        assert len(msg.get_payload()) >= 2  # Mixed contains Related and others

    @patch("sendMail.get_subscriber_reader")
    def test_generate_mailing_missing_config(self, mock_reader):
        """Cover lines 610-611: AttributeError in generate_mailing"""
        param = Mock()
        # Missing max_addr_per_mail
        del param.max_addr_per_mail
        with patch("sendMail.log") as mock_log:
            res = sendMail.generate_mailing(param)
            assert res == "Config Key Error"
            mock_log.critical.assert_called_once()

    @patch("sendMail.get_subscriber_reader")
    @patch("sendMail.sleep")
    @patch("sendMail.send_mail")
    @patch("sendMail.build_email")
    def test_generate_mailing_indexing_and_pause(
            self, mock_build, mock_send, mock_sleep, mock_reader_func
    ):
        """Cover lines 625-628 (from_index), 638 (to_index), 679-680 (hourly limit)"""
        param = Mock()
        param.max_addr_per_mail = 1
        param.pause = 0
        param.max_mails_per_hour = 1
        param.from_index = 2
        param.to_index = 2
        param.profile = "artscroises"
        param.donotsend = False
        param.verbose = False
        param.message = "Hello ${name}"
        param.subject = "Subject"
        param.file = []
        param.test = False
        param.selected = False
        param.filter = {"email": "is not empty", "status": "is active"}

        # Header + 3 rows
        reader = iter(
            [
                ["email", "name", "status", "group", "selected"],
                ["a1@ex.com", "N1", "active", "G1", "x"],  # index 2
                ["a2@ex.com", "N2", "active", "G1", "x"],  # index 3
                ["a3@ex.com", "N3", "active", "G1", "x"],  # index 4
            ]
        )
        mock_reader_func.return_value = (reader, None)

        m = Mock()
        m._temp_dirs = []
        mock_build.return_value = (m, ["a1@ex.com"])

        res = sendMail.generate_mailing(param)
        assert res == "OK"
        # Should have skipped to index 2, processed it, and stopped because current_row_idx(2) > to_index(2) is false,
        # but next iteration current_row_idx(3) > to_index(2) is true.
        # Wait, current_row_idx starts at 1. Header is 1. Skip range(2, 2) is empty.
        # Row 1 (a1) is index 2.

        # Test hourly limit
        param.to_index = 10
        param.max_mails_per_hour = 1
        reader = iter(
            [
                ["email", "name", "status", "group", "selected"],
                ["a1@ex.com", "N1", "active", "G1", "x"],
                ["a2@ex.com", "N2", "active", "G1", "x"],
            ]
        )
        mock_reader_func.return_value = (reader, None)
        sendMail.generate_mailing(param)
        # 1st mail sent -> recipient_count = 1. if 1 % 1 == 0 -> sleep(3600)
        mock_sleep.assert_any_call(3600)

    def test_filter_cambristi_errors(self):
        """Cover lines 757-759 and 765-766: IndexError in _filter_cambristi"""
        # Test mode with missing title index but valid nom/prenom indices to avoid secondary errors
        filter_rules = {
            "title": "in member, participant, inactive",
            "email": "is not empty",
            "emailBounced": "if False",
        }
        res = sendMail.filter(
            filter_rules, ["x", "Doe", "John"], {"title": 50, "nom": 1, "prenom": 2}
        )
        assert res is True

        # Normal mode with missing title index
        res = sendMail.filter(filter_rules, ["member"], {"title": 50})
        assert res is True

    def test_send_gmail_error(self):
        """Cover lines 788-790: HttpError in send_gmail"""
        service = MagicMock()

        class MyHttpError(Exception):
            pass

        # Patch sendMail.errors to have our custom HttpError
        with patch.object(
                sendMail, "errors", new=type("E", (), {"HttpError": MyHttpError})
        ):
            service.users().messages().send().execute.side_effect = MyHttpError("boom")

            class Msg:
                def __init__(self):
                    self._h = {"To": "to@ex.com"}

                def __getitem__(self, k):
                    return self._h[k]

                def as_bytes(self):
                    return b"raw"

            message = Msg()

            with patch("sendMail.log") as mock_log:
                res = sendMail.send_gmail(service, message)
                assert res is None
                mock_log.error.assert_called_once()

    @patch("sendMail.get_smtp_connection")
    def test_send_mail_error(self, mock_get_conn):
        """Cover lines 828-831: SMTPException in send_mail"""
        param = Mock()
        param.verbose = False
        conn = MagicMock()
        conn.sendmail.side_effect = sendMail.SMTPException("Error")
        mock_get_conn.return_value = conn

        class Msg:
            def __init__(self):
                self._h = {"From": "me@ex.com"}

            def __getitem__(self, k):
                return self._h[k]

            def as_string(self):
                return "raw"

        msg = Msg()
        with patch("sendMail.log") as mock_log:
            with patch("sendMail.sleep") as mock_sleep:
                sendMail.send_mail(param, msg, ["to@ex.com"])
                mock_log.error.assert_called()
                mock_sleep.assert_called_with(10)


class TestCoverageGap2:
    """Additional tests to push coverage above 80%."""

    def test_get_google_sheets_schema_exception(self):
        """Cover lines 226-236: exception in get_google_sheets_schema."""
        with patch("sendMail.open_google_db_members_sheet", side_effect=Exception("API error")):
            result = sendMail.get_google_sheets_schema("sa", "sheet_id")
        assert result == []

    def test_get_google_sheets_schema_empty_data(self):
        """Cover line 233: empty data returns []."""
        with patch("sendMail.open_google_db_members_sheet") as mock_open, \
             patch("sendMail.read_all_sheet", return_value=[]):
            mock_open.return_value = MagicMock()
            result = sendMail.get_google_sheets_schema("sa", "sheet_id")
        assert result == []

    def test_process_attachments_google_drive_path(self):
        """Cover lines 671-680: process_attachments downloads from Google Drive."""
        args = Mock()
        args.file = None
        config = {"SA": "sa_key", "mailing_folder": "folder_id"}

        mock_service = MagicMock()
        mock_files = [{"id": "f1", "name": "news.html"}]

        with patch("sendMail.gd.connect_google_driver", return_value=mock_service), \
             patch("sendMail.gd.get_files", return_value={"files": mock_files}), \
             patch("sendMail.gd.download_file"), \
             patch("sendMail.glob", return_value=[]), \
             patch("sendMail.os.remove"):
            files, service, gd_files = sendMail.process_attachments(args, config)

        assert service is mock_service
        assert gd_files == mock_files

    def test_attach_body_with_inline_images(self, tmp_path):
        """Cover lines 843-845: _attach_body attaches inline images."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)

        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("mixed")
        msg_related = MIMEMultipart("related")

        all_inline_images = [{"path": str(img_file), "cid": "img001"}]
        sendMail._attach_body(msg, msg_related, "<html><body>test</body></html>", all_inline_images)

        # related part should have been attached to msg
        assert msg.get_payload()

    def test_attach_body_inline_image_error(self):
        """Cover line 847: OSError when opening inline image."""
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("mixed")
        msg_related = MIMEMultipart("related")

        all_inline_images = [{"path": "/nonexistent/img.png", "cid": "img001"}]
        with patch("sendMail.log") as mock_log:
            sendMail._attach_body(msg, msg_related, "<html><body>test</body></html>", all_inline_images)
        mock_log.error.assert_called_once()

    def test_build_and_send_temp_dir_cleanup_verbose(self, tmp_path):
        """Cover lines 933-938: temp dir cleanup with verbose logging."""
        import shutil
        temp_dir = str(tmp_path / "tmpdir")
        os.makedirs(temp_dir, exist_ok=True)

        param = Mock()
        param.donotsend = False
        param.verbose = True
        param.subject = "Test"
        param.message = "Hello"
        param.file = []
        param.smtp_host = "smtp.test.com"

        mock_msg = Mock()
        mock_msg._temp_dirs = [temp_dir]
        mock_recipients = ["to@test.com"]

        with patch("sendMail.build_email", return_value=(mock_msg, mock_recipients)), \
             patch("sendMail.send_mail", return_value=True), \
             patch("sendMail.log") as mock_log, \
             patch("sendMail.shutil.rmtree") as mock_rmtree:
            sendMail._build_and_send(param, ["to@test.com"], ["to@test.com"], ["email"])

        mock_rmtree.assert_called_once_with(temp_dir)
        mock_log.info.assert_any_call(f"Dossier temporaire supprimé : {temp_dir}")

    def test_build_and_send_temp_dir_oserror(self, tmp_path):
        """Cover line 937-938: OSError during temp dir cleanup."""
        param = Mock()
        param.donotsend = False
        param.verbose = False
        param.subject = "Test"
        param.message = "Hello"
        param.file = []
        param.smtp_host = "smtp.test.com"

        mock_msg = Mock()
        mock_msg._temp_dirs = ["/nonexistent/dir"]
        mock_recipients = ["to@test.com"]

        with patch("sendMail.build_email", return_value=(mock_msg, mock_recipients)), \
             patch("sendMail.send_mail", return_value=True), \
             patch("sendMail.shutil.rmtree", side_effect=OSError("no such dir")), \
             patch("sendMail.log") as mock_log:
            sendMail._build_and_send(param, ["to@test.com"], ["to@test.com"], ["email"])

        mock_log.error.assert_called()

    def test_generate_mailing_empty_header(self):
        """Cover line 993: return 'Header Error' when reader yields nothing."""
        param = Mock()
        param.max_addr_per_mail = 1
        param.pause = 0
        param.max_mails_per_hour = 100
        param.from_index = None

        with patch("sendMail.get_subscriber_reader", return_value=(iter([]), None)):
            result = sendMail.generate_mailing(param)
        assert result == "Header Error"

    def test_generate_mailing_closes_file_object(self):
        """Cover line 1029: file_object.close() in finally block."""
        param = Mock()
        param.max_addr_per_mail = 1
        param.pause = 0
        param.max_mails_per_hour = 100
        param.from_index = None
        param.to_index = None
        param.filter = {}
        param.test = False
        param.selected = False
        param.verbose = False
        param.donotsend = False
        param.subject = "Sub"
        param.message = "Hi ${email}"
        param.file = []
        param.profile = "test"

        mock_file = MagicMock()
        rows = [["email"], ["a@b.com"]]

        mock_msg = Mock()
        mock_msg._temp_dirs = []
        mock_recipients = ["a@b.com"]

        with patch("sendMail.get_subscriber_reader", return_value=(iter(rows), mock_file)), \
             patch("sendMail.build_email", return_value=(mock_msg, mock_recipients)), \
             patch("sendMail.send_mail", return_value=True):
            result = sendMail.generate_mailing(param)

        mock_file.close.assert_called_once()

    def test_parse_filter_expr_empty_raises(self):
        """Cover line 1068: ValueError for empty filter value."""
        with pytest.raises(ValueError, match="empty or invalid"):
            sendMail._parse_filter_expr("", "field")

    def test_parse_filter_expr_non_string_raises(self):
        """Cover line 1068: ValueError for non-string filter value."""
        with pytest.raises(ValueError, match="empty or invalid"):
            sendMail._parse_filter_expr(None, "field")

    def test_eval_regex_empty_test_value_negate_true(self):
        """Cover line 1116: empty test_value + negate=True returns True."""
        result = sendMail._eval_regex(None, "anything", negate=True)
        assert result is True

    def test_eval_regex_empty_test_value_negate_false(self):
        """Cover line 1116: empty test_value + negate=False returns False."""
        result = sendMail._eval_regex("", "anything", negate=False)
        assert result is False

    def test_do_string_eval_default_true(self):
        """Cover line 1155: _do_string_eval returns True for unknown op."""
        # 'unknown_op' is not in any of the checked strings, so falls through to default True
        result = sendMail._do_string_eval("hello", "world", "unknown_op")
        assert result is True

    def test_post_send_cleanup(self, tmp_path):
        """Cover lines 1337, 1339: _post_send_cleanup renames files and removes input."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        input_file = input_dir / "test.html"
        input_file.write_text("content")

        mock_service = MagicMock()
        google_drive_files = [{"id": "f1", "name": "news.html"}]

        with patch("sendMail.gd.rename_file") as mock_rename, \
             patch("sendMail.glob", return_value=[str(input_file)]), \
             patch("sendMail.os.remove") as mock_remove:
            sendMail._post_send_cleanup(mock_service, google_drive_files)

        mock_rename.assert_called_once_with(mock_service, "f1", "published_news.html")
        mock_remove.assert_called_once_with(str(input_file))

    def test_process_profile_session_filter_applied(self):
        """Cover line 1376: session_filter from args overrides param.filter."""
        from unittest.mock import call

        args = Mock()
        args.session_filter = {"status": "is active"}
        args.profile = "test"
        args.conf = {"test": {"sender": "me@test.com", "sendername": "Me",
                               "subject": "Sub", "message": "Body",
                               "database": "data.csv"}}
        args.subject = "Sub"
        args.test = False
        args.verbose = False
        args.doNotSend = False
        args.database = "data.csv"
        args.file = []
        args.from_index = None
        args.to_index = None
        args.wait = None
        args.max_mails_per_hour = 100
        args.max_addr_per_mail = 10
        args.pause = 0
        args.config = None
        args.md2html = False
        args.body = None

        filter_applied = {}

        def capture_filter(param):
            filter_applied["filter"] = param.filter
            return "OK"

        with patch("sendMail._load_config_with_secrets", return_value={
            "sender": "me@test.com", "sendername": "Me", "subject": "Sub",
            "message": "Body", "database": "data.csv", "filter": {"email": "is not empty"},
            "test": False,
        }), \
        patch("sendMail.check_mandatory_param", return_value=True), \
        patch("sendMail.process_attachments", return_value=(["file.html"], None, [])), \
        patch("sendMail._prepare_message_body", side_effect=lambda p, c, f: p), \
        patch("sendMail.generate_mailing", side_effect=capture_filter), \
        patch("sendMail._post_send_cleanup"):
            sendMail.process_profile(args)

        assert filter_applied.get("filter") == {"status": "is active"}

    def test_process_profile_generate_mailing_error(self):
        """Cover line 1384: return 'Error' when generate_mailing != 'OK'."""
        args = Mock()
        args.session_filter = None
        args.profile = "test"

        with patch("sendMail._load_config_with_secrets", return_value={
            "sender": "me@test.com", "sendername": "Me", "subject": "Sub",
            "message": "Body", "database": "data.csv", "test": False,
        }), \
        patch("sendMail.check_mandatory_param", return_value=True), \
        patch("sendMail.process_attachments", return_value=(["file.html"], None, [])), \
        patch("sendMail._prepare_message_body", side_effect=lambda p, c, f: p), \
        patch("sendMail.generate_mailing", return_value="Error"):
            result = sendMail.process_profile(args)
        assert result == "Error"

    def test_check_data_source_with_database(self):
        """Cover line 1404: _check_data_source returns True when database attr present."""
        param = Mock(spec=["database"])
        param.database = "data.csv"
        assert sendMail._check_data_source(param) is True

    def test_check_smtp_imap_params_all_present(self):
        """Cover lines 1409-1415: _check_smtp_imap_params with all params set."""
        param = Mock()
        param.smtp_port = 587
        param.imap_host = "imap.test.com"
        param.imap_port = 993
        param.username = "user"
        param.password = "pass"
        param.sent_folder = "Sent"
        result = sendMail._check_smtp_imap_params(param)
        assert result is True

    def test_check_smtp_imap_params_missing_param(self):
        """Cover loop body: _check_smtp_imap_params with missing param."""
        param = Mock(spec=["smtp_port"])  # Only smtp_port, rest missing
        param.smtp_port = 587
        with patch("sendMail.log") as mock_log:
            result = sendMail._check_smtp_imap_params(param)
        assert result is False
        mock_log.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
