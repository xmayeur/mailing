import os
import sys
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies before importing sendMail
mock_get_secret = MagicMock(return_value={"key": "value"})
sys.modules['gspread'] = MagicMock()
sys.modules['yaml'] = MagicMock()
# sys.modules['bs4'] = MagicMock()
sys.modules['certifi'] = MagicMock()
sys.modules['getSecrets'] = MagicMock()
sys.modules['getSecrets'].get_secret = mock_get_secret
sys.modules['google'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.transport'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['google_auth_oauthlib'] = MagicMock()
sys.modules['google_auth_oauthlib.flow'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.errors'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()
sys.modules['oauth2client'] = MagicMock()
sys.modules['oauth2client.service_account'] = MagicMock()
sys.modules['PIL'] = MagicMock()

import sendMail

class TestCoverageGap:
    """Tests to cover identified gaps in sendMail.py"""

    @patch('sendMail.os.path.exists', return_value=True)
    @patch('sendMail.BeautifulSoup')
    @patch('builtins.open', new_callable=mock_open, read_data='<html><img src="http://example.com/img.png"><img src="data:image/png;base64,abc"></html>')
    def test_prepare_html_for_cid_external_and_data(self, mock_file, mock_bs, mock_exists):
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

    @patch('sendMail.openGoogleDBMembersSheet')
    def test_get_subscriber_reader_google_success(self, mock_open_sheet):
        """Cover line 230: Google Sheets reader"""
        param = Mock()
        param.database = None
        param.sa = "sa"
        param.sheetid = "id"
        mock_wb = Mock()
        mock_open_sheet.return_value = mock_wb
        
        with patch('sendMail.readAllSheet', return_value=[['header'], ['row']]):
            reader, handle = sendMail.get_subscriber_reader(param)
            assert handle is None
            assert list(reader) == [['header'], ['row']]

    def test_get_subscriber_reader_file_not_found(self):
        """Cover lines 235-237: FileNotFoundError in subscriber reader"""
        param = Mock()
        param.database = "nonexistent.csv"
        with patch('sendMail.log') as mock_log:
            reader, handle = sendMail.get_subscriber_reader(param)
            assert reader is None
            assert handle is None
            mock_log.critical.assert_called_once()

    @patch('sendMail.SMTP')
    def test_get_smtp_connection_exception(self, mock_smtp):
        """Cover lines 270-272: Exception in SMTP connection"""
        param = Mock()
        param.smtp_host = "host"
        param.smtp_port = 587
        mock_smtp.side_effect = Exception("Connection error")
        with patch('sendMail.log') as mock_log:
            conn = sendMail.get_smtp_connection(param)
            assert conn is None
            mock_log.error.assert_called_once()

    @patch('sendMail.os.path.exists', return_value=True)
    @patch('sendMail.Credentials')
    @patch('sendMail.Request')
    @patch('sendMail.build')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_gmail_service_refresh(self, mock_file, mock_build, mock_request, mock_creds, mock_exists):
        """Cover line 299: creds.refresh(Request()) and token write"""
        param = Mock()
        param.token_file = "token.json"
        param.scopes = ["scope"]
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "refresh"
        creds.to_json.return_value = '{}'
        mock_creds.from_authorized_user_file.return_value = creds
        
        sendMail.get_gmail_service(param)
        creds.refresh.assert_called_once()
        mock_file.assert_called_with('token.json', 'w')

    @patch('sendMail.imaplib.IMAP4_SSL')
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
        
        with patch('sendMail.log') as mock_log:
            sendMail.save_to_sent(param, msg)
            mock_log.info.assert_called_with("stored in sent folder")

    @patch('sendMail.BeautifulSoup')
    @patch('sendMail.tempfile.mkdtemp', return_value="/tmp/dir")
    @patch('builtins.open', new_callable=mock_open, read_data='<html><img src="foo.png"></html>')
    def test_prepare_html_and_get_images_skip_empty_or_external(self, mock_file, mock_temp, mock_bs):
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

    @patch('sendMail.Image.open')
    @patch('sendMail.os.path.exists', return_value=True)
    @patch('sendMail.BeautifulSoup')
    @patch('sendMail.tempfile.mkdtemp', return_value="/tmp/dir")
    @patch('builtins.open', new_callable=mock_open, read_data='<html><img src="foo.png"></html>')
    def test_prepare_html_and_get_images_resize_and_error(self, mock_file, mock_temp, mock_bs, mock_exists, mock_img_open):
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
            raise Exception("Bad image")
        
        mock_img_open.side_effect = open_side_effect
        
        with patch('sendMail.log') as mock_log:
            html, images, tdir = sendMail.prepare_html_and_get_images("test.html", max_width=800)
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
        
        msg, recipients = sendMail.build_email(param, to="to@example.com", cc="cc@example.com", bcc="bcc@example.com", message="Hi")
        assert msg["To"] == "bcc@example.com"
        assert msg["Cc"] == "cc@example.com"
        assert "artscroises.be" in msg["Message-ID"]

    @patch('sendMail.os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=b"data")
    def test_build_email_attachments(self, mock_file, mock_exists):
        """Cover lines 530-532 (inline images), 547-550 (PDF), 551-552 (TXT)"""
        param = Mock()
        param.sendername = "Sender"
        param.sender = "sender@example.com"
        param.max_addr_per_mail = 10
        param.profile = "other"
        
        # Test images and attachments
        msg, recipients = sendMail.build_email(param, message="<html></html>", images=["img.png"], attachments=["doc.pdf", "notes.txt"])
        
        # 1 image + 1 html part + 1 pdf + 1 txt = 4 parts expected in some structure
        # Mixed -> [Related -> [HTML, Image], PDF, TXT]
        assert len(msg.get_payload()) >= 2 # Mixed contains Related and others
        
    @patch('sendMail._get_subscriber_reader')
    def test_generate_mailing_missing_config(self, mock_reader):
        """Cover lines 610-611: AttributeError in generate_mailing"""
        param = Mock()
        # Missing max_addr_per_mail
        del param.max_addr_per_mail
        with patch('sendMail.log') as mock_log:
            res = sendMail.generate_mailing(param)
            assert res == "Error"
            mock_log.critical.assert_called_once()

    @patch('sendMail._get_subscriber_reader')
    @patch('sendMail.sleep')
    @patch('sendMail.send_mail')
    @patch('sendMail.build_email')
    def test_generate_mailing_indexing_and_pause(self, mock_build, mock_send, mock_sleep, mock_reader_func):
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
        param.filter = {
            "email": "is not empty",
            "status": "is active"
        }
        
        # Header + 3 rows
        reader = iter([
            ["email", "name", "status", "group", "selected"],
            ["a1@ex.com", "N1", "active", "G1", "x"], # index 2
            ["a2@ex.com", "N2", "active", "G1", "x"], # index 3
            ["a3@ex.com", "N3", "active", "G1", "x"], # index 4
        ])
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
        reader = iter([
            ["email", "name", "status", "group", "selected"],
            ["a1@ex.com", "N1", "active", "G1", "x"],
            ["a2@ex.com", "N2", "active", "G1", "x"],
        ])
        mock_reader_func.return_value = (reader, None)
        sendMail.generate_mailing(param)
        # 1st mail sent -> recipient_count = 1. if 1 % 1 == 0 -> sleep(3600)
        mock_sleep.assert_any_call(3600)

    def test_filter_cambristi_errors(self):
        """Cover lines 757-759 and 765-766: IndexError in _filter_cambristi"""
        # Test mode with missing title index but valid nom/prenom indices to avoid secondary errors
        filter = {
            "title": "in member, participant, inactive",
            "email": "is not empty",
            "emailBounced": "if False"
        }
        with patch('sendMail.log') as mock_log:
            res = sendMail.filter(filter, ["x", "Doe", "John"], {"title": 50, "nom": 1, "prenom": 2})
            assert res is True
            mock_log.warning.assert_called_once()
            
        # Normal mode with missing title index
        res = sendMail.filter(filter, ["member"], {"title": 50})
        assert res is True

    def test_send_gmail_error(self):
        """Cover lines 788-790: HttpError in send_gmail"""
        service = MagicMock()
        
        class MyHttpError(Exception):
            pass
        
        # Patch sendMail.errors to have our custom HttpError
        with patch.object(sendMail, 'errors', new=type('E', (), {'HttpError': MyHttpError})):
            service.users().messages().send().execute.side_effect = MyHttpError("boom")
            
            class Msg:
                def __init__(self):
                    self._h = {"To": "to@ex.com"}
                def __getitem__(self, k):
                    return self._h[k]
                def as_bytes(self):
                    return b"raw"
            message = Msg()
            
            with patch('sendMail.log') as mock_log:
                res = sendMail.send_gmail(service, message)
                assert res is None
                mock_log.error.assert_called_once()

    @patch('sendMail._get_smtp_connection')
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
        with patch('sendMail.log') as mock_log:
            with patch('sendMail.sleep') as mock_sleep:
                send_res = sendMail.send_mail(param, msg, ["to@ex.com"])
                mock_log.error.assert_called()
                mock_sleep.assert_called_with(10)


if __name__ == "__main__":
    pytest.main([__file__])
