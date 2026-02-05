"""
Unit tests for sendMail.py module
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, mock_open
from email.mime.multipart import MIMEMultipart

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies
# Note: googleDriveLib is tested separately in test_googleDriveLib.py
# We mock its dependencies here to allow it to import properly
mock_get_secret = MagicMock(return_value={"key": "value"})

sys.modules['gspread'] = MagicMock()
sys.modules['yaml'] = MagicMock()
sys.modules['bs4'] = MagicMock()
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


class TestDict2Class:
    """Tests for Dict2Class utility class"""

    def test_dict_to_class_conversion(self):
        """Test dictionary to class conversion"""
        test_dict = {"name": "Test", "value": 123}
        obj = sendMail.Dict2Class(test_dict)
        assert obj.name == "Test"
        assert obj.value == 123

    def test_lowercase_conversion(self):
        """Test that keys are converted to lowercase"""
        test_dict = {"NAME": "Test", "VALUE": 123}
        obj = sendMail.Dict2Class(test_dict)
        assert obj.name == "Test"
        assert obj.value == 123


class TestFileUtilities:
    """Tests for file utility functions"""

    def test_guess_type_with_magic(self):
        """Test MIME type guessing with magic library"""
        mock_magic = MagicMock()
        mock_magic.from_file.return_value = "application/pdf"
        with patch.dict('sys.modules', {'magic': mock_magic}):
            result = sendMail.guess_type("test.pdf")
            assert result == "application/pdf"
            mock_magic.from_file.assert_called_once_with("test.pdf", mime=True)

    def test_guess_type_without_magic(self):
        """Test MIME type guessing without magic library"""
        with patch.dict('sys.modules', {'magic': None}):
            result = sendMail.guess_type("test.pdf")
            # Should fall back to mimetypes
            assert result is not None

    def test_file_to_base64_local_file(self):
        """Test Base64 encoding of local file"""
        test_content = b"test content"
        with patch('builtins.open', mock_open(read_data=test_content)):
            result = sendMail.file_to_base64("/path/to/file.txt")
            assert isinstance(result, str)
            assert len(result) > 0

    @patch('sendMail.requests.get')
    def test_file_to_base64_http_file(self, mock_get):
        """Test Base64 encoding of HTTP file"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_get.return_value = mock_response

        result = sendMail.file_to_base64("http://example.com/file.txt")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch('sendMail.requests.get')
    def test_file_to_base64_http_404(self, mock_get):
        """Test Base64 encoding with HTTP 404 error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = sendMail.file_to_base64("http://example.com/missing.txt")
        assert result == ''


class TestIndicesHelper:
    """Tests for _get_indices helper function"""

    def test_get_indices_basic(self):
        """Test basic index mapping"""
        header = ["name", "email", "status"]
        result = sendMail._get_indices(header)
        assert result == {"name": 0, "email": 1, "status": 2}

    def test_get_indices_empty(self):
        """Test with empty header"""
        header = []
        result = sendMail._get_indices(header)
        assert result == {}


class TestFormatMessage:
    """Tests for message formatting function"""

    def test_format_message_basic(self):
        """Test basic message variable substitution"""
        template = "Hello ${name}, welcome!"
        row = ["John", "john@example.com"]
        header = ["name", "email"]

        result = sendMail._format_message(template, row, header)
        assert "John" in result

    def test_format_message_multiple_vars(self):
        """Test multiple variable substitution"""
        template = "Dear ${first_name} ${last_name}"
        row = ["John", "Doe", "john@example.com"]
        header = ["first_name", "last_name", "email"]

        result = sendMail._format_message(template, row, header)
        assert "John" in result
        assert "Doe" in result

    def test_format_message_invalid(self):
        """Test message formatting with invalid variable"""
        template = "Hello ${invalid_var}"
        row = ["John"]
        header = ["name"]

        # Should return original template on error
        result = sendMail._format_message(template, row, header)
        assert result == template

class TestFilterFunctions:
    """Tests for filtering functions"""

    def test_filter_artscroises_active_selected(self):
        """Test Arts Croisés filter with active, selected member"""
        param = Mock()
        param.test = False
        param.selected = True

        row = ["active", "Test Group", "x", "test@example.com"]
        indices = {"status": 0, "group": 1, "selected": 2, "email": 3}

        result = sendMail._filter_artscroises(param, row, indices)
        assert result == False  # Should NOT be filtered (passes filter)

    def test_filter_artscroises_inactive(self):
        """Test Arts Croisés filter with inactive member"""
        param = Mock()
        param.test = False
        param.selected = False

        row = ["inactive", "Group", "", "test@example.com"]
        indices = {"status": 0, "group": 1, "selected": 2, "email": 3}

        result = sendMail._filter_artscroises(param, row, indices)
        assert result == True  # Should be filtered (doesn't pass)

    def test_filter_cambristi_member(self):
        """Test Cambristi filter with member"""
        param = Mock()

        row = ["member", "John", "Doe", "test@example.com"]
        indices = {"title": 0, "nom": 1, "prenom": 2, "email": 3}

        result = sendMail._filter_cambristi(param, row, indices, test=False)
        assert result == False  # Should NOT be filtered

    def test_filter_cambristi_test_mode(self):
        """Test Cambristi filter in test mode"""
        param = Mock()

        row = ["test", "John", "Doe", "test@example.com"]
        indices = {"title": 0, "nom": 1, "prenom": 2, "email": 3}

        result = sendMail._filter_cambristi(param, row, indices, test=True)
        assert result == False  # Should NOT be filtered


class TestEmailBuilding:
    """Tests for email building functions"""

    def test_build_email_basic(self):
        """Test basic email building"""
        param = Mock()
        param.sendername = "Test Sender"
        param.sender = "sender@example.com"
        param.cotisation = False
        param.max_addr_per_mail = 50
        param.profile = "test"

        msg, recipients = sendMail.build_email(
            param=param,
            subject="Test Subject",
            to="recipient@example.com",
            message="Test message"
        )

        assert isinstance(msg, MIMEMultipart)
        assert msg["Subject"] == "Test Subject"
        assert "recipient@example.com" in recipients

    def test_build_email_with_bcc(self):
        """Test email building with BCC recipients"""
        param = Mock()
        param.sendername = "Test Sender"
        param.sender = "sender@example.com"
        param.cotisation = False
        param.max_addr_per_mail = 50
        param.profile = "test"

        msg, recipients = sendMail.build_email(
            param=param,
            subject="Test Subject",
            to="to@example.com",
            bcc="bcc@example.com",
            message="Test message"
        )

        assert "bcc@example.com" in recipients
        assert "to@example.com" in recipients


class TestArgumentParser:
    """Tests for argument parser setup"""

    @patch('sys.argv', ['sendMail.py', '--profile', 'artscroises', '-s', 'Test'])
    def test_setup_argparse_basic(self):
        """Test basic argument parsing"""
        args = sendMail.setup_argparse()
        assert args.profile == "artscroises"
        assert args.subject == "Test"

    @patch('sys.argv', ['sendMail.py', '--profile', 'test', '-t', '-v'])
    def test_setup_argparse_flags(self):
        """Test flag arguments"""
        args = sendMail.setup_argparse()
        assert args.test == True
        assert args.verbose == True


class TestHTMLProcessing:
    """Tests for HTML processing functions"""

    @patch('builtins.open', mock_open(read_data='<html><body><img src="test.jpg"/></body></html>'))
    @patch('os.path.exists')
    @patch('os.path.join')
    @patch('sendMail.BeautifulSoup')
    def test_prepare_html_for_cid(self, mock_bs, mock_join, mock_exists):
        """Test HTML CID preparation"""
        mock_exists.return_value = True
        mock_join.return_value = "/basepath/test.jpg"

        # Create a mock img tag
        mock_img = Mock()
        mock_img.attrs = {"src": "test.jpg"}

        # Create a mock soup object
        mock_soup = Mock()
        mock_soup.find_all.return_value = [mock_img]
        mock_soup.__str__ = Mock(return_value='<html><body><img src="cid:test@inline.img"/></body></html>')

        mock_bs.return_value = mock_soup

        html, images = sendMail.prepare_html_for_cid("/basepath/test.html")

        assert "cid:" in html
        assert len(images) > 0
        assert images[0][0] == "/basepath/test.jpg"

    @patch('builtins.open', mock_open(read_data='<html><body><img src="http://example.com/test.jpg"/></body></html>'))
    @patch('os.path.exists')
    def test_prepare_html_for_cid_external_images(self, mock_exists):
        """Test HTML CID preparation skips external images"""
        mock_exists.return_value = True

        html, images = sendMail.prepare_html_for_cid("/basepath/test.html")

        assert len(images) == 0  # External images should be skipped

    @patch('builtins.open', mock_open(read_data='<html><body><img src="test.jpg"/></body></html>'))
    @patch('os.path.exists')
    @patch('os.path.join')
    @patch('tempfile.mkdtemp')
    @patch('sendMail.Image')
    @patch('sendMail.BeautifulSoup')
    def test_prepare_html_and_get_images(self, mock_bs, mock_image, mock_temp, mock_join, mock_exists):
        """Test HTML processing with image optimization"""
        mock_exists.return_value = True
        mock_join.return_value = "/basepath/test.jpg"
        mock_temp.return_value = "/tmp/test_dir"

        # Mock PIL Image
        mock_img = Mock()
        mock_img.width = 1000
        mock_img.height = 800
        mock_img.resize.return_value = mock_img
        mock_img.convert.return_value = mock_img
        mock_image.open.return_value.__enter__.return_value = mock_img

        # Create a mock img tag
        mock_img_tag = Mock()
        mock_img_tag.attrs = {"src": "test.jpg"}

        # Create a mock soup object
        mock_soup = Mock()
        mock_soup.find_all.return_value = [mock_img_tag]
        mock_soup.__str__ = Mock(return_value='<html><body><img src="cid:test@inline.img"/></body></html>')

        mock_bs.return_value = mock_soup

        html, images, temp_dir = sendMail.prepare_html_and_get_images("/basepath/test.html")

        assert "cid:" in html
        assert len(images) > 0
        assert temp_dir == "/tmp/test_dir"

    @patch('sendMail.open', new_callable=mock_open, read_data='<html><body><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="/></body></html>')
    @patch('os.path.exists')
    @patch('tempfile.mkdtemp')
    @patch('sendMail.Image')
    @patch('sendMail.BeautifulSoup')
    @patch('email.utils.make_msgid')
    def test_prepare_html_and_get_images_base64(self, mock_msgid, mock_bs, mock_image, mock_temp, mock_exists, m_open):
        """Test HTML processing with base64 image"""
        mock_exists.return_value = True
        mock_temp.return_value = "/tmp/test_dir"
        # make_msgid returns with brackets, [1:-1] removes them.
        mock_msgid.side_effect = ["<cid1@inline.img>", "<cid2@inline.img>"]

        # Mock PIL Image
        mock_img = Mock()
        mock_img.width = 100
        mock_img.height = 100
        mock_img.resize.return_value = mock_img
        mock_img.convert.return_value = mock_img
        mock_image.open.return_value.__enter__.return_value = mock_img

        # Create a mock img tag
        mock_img_tag = Mock()
        mock_img_tag.attrs = {"src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="}

        # Create a mock soup object
        mock_soup = Mock()
        mock_soup.find_all.return_value = [mock_img_tag]
        mock_soup.__str__ = Mock(return_value='<html><body><img src="cid:cid2@inline.img"/></body></html>')

        mock_bs.return_value = mock_soup

        # We need PIL.Image.save to NOT call open if possible, or we just ignore its calls.
        # Let's mock the save method to avoid it calling open.
        mock_img.save = Mock()

        html, images, temp_dir = sendMail.prepare_html_and_get_images("/basepath/test.html")

        assert "cid:" in html
        assert len(images) > 0
        assert temp_dir == "/tmp/test_dir"
        
        # The base64 image is first saved to embedded_<cid1>.<ext>
        m_open.assert_any_call(os.path.join(temp_dir, "embedded_cid1@inline.img.png"), "wb")
        
        # The optimized image is saved by PIL.Image.save
        mock_img.save.assert_called()
        # Verify the path passed to save()
        args, kwargs = mock_img.save.call_args
        assert args[0] == os.path.join(temp_dir, "cid2@inline.img.jpg")

    @patch('builtins.open', mock_open(read_data='<html><body><img src="data:image/png;base64,INVALID"/></body></html>'))
    @patch('os.path.exists')
    @patch('tempfile.mkdtemp')
    @patch('sendMail.BeautifulSoup')
    @patch('sendMail.log')
    def test_prepare_html_and_get_images_base64_error(self, mock_log, mock_bs, mock_temp, mock_exists):
        """Test HTML processing with invalid base64 image"""
        mock_exists.return_value = True
        mock_temp.return_value = "/tmp/test_dir"

        # Create a mock img tag
        mock_img_tag = Mock()
        mock_img_tag.attrs = {"src": "data:image/png;base64,INVALID"}

        # Create a mock soup object
        mock_soup = Mock()
        mock_soup.find_all.return_value = [mock_img_tag]
        mock_soup.__str__ = Mock(return_value='<html><body><img src="data:image/png;base64,INVALID"/></body></html>')

        mock_bs.return_value = mock_soup

        html, images, temp_dir = sendMail.prepare_html_and_get_images("/basepath/test.html")

        # Should skip the image and log error
        assert len(images) == 0
        mock_log.error.assert_called()


class TestAttachmentProcessing:
    """Tests for attachment processing"""

    @patch('os.path.isfile')
    def test_process_attachments_with_files(self, mock_isfile):
        """Test processing with file arguments"""
        mock_isfile.return_value = True

        args = Mock()
        args.file = ["test1.pdf", "test2.pdf"]
        config = {}

        files, service, gd_files = sendMail.process_attachments(args, config)

        assert len(files) == 2
        assert service is None
        assert gd_files == []

    @patch('os.path.isfile')
    def test_process_attachments_file_not_found(self, mock_isfile):
        """Test processing with missing file"""
        mock_isfile.return_value = False

        args = Mock()
        args.file = ["missing.pdf"]
        config = {}

        with pytest.raises(SystemExit):
            sendMail.process_attachments(args, config)


class TestSMTPConnection:
    """Tests for SMTP connection handling"""

    @patch('sendMail.SMTP')
    @patch('ssl.create_default_context')
    def test_get_smtp_connection_success(self, mock_ssl, mock_smtp):
        """Test successful SMTP connection"""
        param = Mock()
        param.smtp_host = "smtp.example.com"
        param.smtp_port = 587
        param.username = "user@example.com"
        param.password = "password123"

        mock_conn = Mock()
        mock_smtp.return_value = mock_conn

        result = sendMail._get_smtp_connection(param)

        assert result == mock_conn
        mock_conn.starttls.assert_called_once()
        mock_conn.login.assert_called_once_with("user@example.com", "password123")

    @patch('sendMail.SMTP')
    @patch('ssl.create_default_context')
    def test_get_smtp_connection_auth_error(self, mock_ssl, mock_smtp):
        """Test SMTP connection with authentication error"""
        from smtplib import SMTPAuthenticationError

        param = Mock()
        param.smtp_host = "smtp.example.com"
        param.smtp_port = 587
        param.username = "user@example.com"
        param.password = "wrong_password"

        mock_conn = Mock()
        mock_conn.login.side_effect = SMTPAuthenticationError(535, "Authentication failed")
        mock_smtp.return_value = mock_conn

        with pytest.raises(SystemExit):
            sendMail._get_smtp_connection(param)


class TestEmailSending:
    """Tests for email sending functions"""

    @patch('sendMail.imaplib.IMAP4_SSL', side_effect=Exception('fail'))
    @patch('sendMail.sleep')
    def test_save_to_sent_failure_retries_and_logs(self, mock_sleep, mock_imap):
        param = Mock()
        param.imap_host = "imap.example.com"
        param.imap_port = 993
        param.username = "user@example.com"
        param.password = "password123"
        param.sent_folder = "Sent"
        param.verbose = False

        msg = Mock()
        msg.as_string.return_value = "email content"

        # Should not raise; it logs error after retries
        sendMail._save_to_sent(param, msg)
        # sleep should have been called twice (between 3 attempts)
        assert mock_sleep.call_count == 2

    @patch('sendMail._get_smtp_connection')
    @patch('sendMail._save_to_sent')
    def test_send_mail_success(self, mock_save, mock_conn_func):
        """Test successful email sending"""
        param = Mock()
        param.verbose = False

        mock_conn = Mock()
        mock_conn_func.return_value = mock_conn

        msg = MagicMock()
        msg.__getitem__.return_value = "sender@example.com"
        msg.as_string.return_value = "email content"

        recipients = ["recipient@example.com"]

        result = sendMail.send_mail(param=param, message=msg, recipients=recipients)

        mock_conn.sendmail.assert_called_once()
        mock_conn.quit.assert_called_once()
        mock_save.assert_called_once()

    @patch('sendMail._get_smtp_connection')
    def test_send_mail_connection_failure(self, mock_conn_func):
        """Test email sending with connection failure"""
        param = Mock()
        param.verbose = False

        mock_conn_func.return_value = None

        msg = Mock()
        recipients = ["recipient@example.com"]

        # Should handle gracefully without raising exception
        sendMail.send_mail(param=param, message=msg, recipients=recipients)

    @patch('sendMail.imaplib.IMAP4_SSL')
    @patch('sendMail.time')
    def test_save_to_sent_success(self, mock_time, mock_imap):
        """Test saving message to sent folder"""
        param = Mock()
        param.imap_host = "imap.example.com"
        param.imap_port = 993
        param.username = "user@example.com"
        param.password = "password123"
        param.sent_folder = "Sent"
        param.verbose = False

        mock_time.return_value = 1234567890

        mock_conn = Mock()
        mock_imap.return_value = mock_conn

        msg = Mock()
        msg.as_string.return_value = "email content"

        sendMail._save_to_sent(param, msg)

        mock_conn.login.assert_called_once()
        mock_conn.append.assert_called_once()
        mock_conn.logout.assert_called_once()


class TestGmailFunctions:
    """Tests for Gmail API functions"""

    @patch('sendMail.base64.urlsafe_b64encode')
    def test_send_gmail_success(self, mock_b64):
        """Test successful Gmail sending"""
        mock_b64.return_value.decode.return_value = "encoded_message"

        mock_service = Mock()
        mock_service.users().messages().send().execute.return_value = {"id": "12345"}

        msg = MagicMock()
        msg.as_bytes.return_value = b"email content"
        msg.__getitem__.return_value = "recipient@example.com"

        result = sendMail.send_gmail(mock_service, msg)

        assert result is not None
        assert result["id"] == "12345"

class TestGetSubscriberReader:
    """Tests for subscriber reader function"""

    @patch('sendMail.openGoogleDBMembersSheet')
    @patch('sendMail.readAllSheet')
    def test_get_subscriber_reader_google_sheets(self, mock_read, mock_open):
        """Test getting subscriber reader from Google Sheets"""
        param = Mock()
        param.database = None
        param.sa = "service_account"
        param.sheetid = "sheet_id"

        mock_wb = Mock()
        mock_open.return_value = mock_wb
        mock_read.return_value = [["header1", "header2"], ["data1", "data2"]]

        reader, csvfile = sendMail._get_subscriber_reader(param)

        assert csvfile is None
        assert reader is not None

    @patch('builtins.open', mock_open(read_data="name,email\nJohn,john@example.com"))
    def test_get_subscriber_reader_csv(self):
        """Test getting subscriber reader from CSV"""
        param = Mock()
        param.database = "test.csv"

        reader, csvfile = sendMail._get_subscriber_reader(param)

        assert reader is not None
        assert csvfile is not None


class TestMailingGeneration:
    """Tests for generate_mailing function"""

    @patch('sendMail._get_subscriber_reader')
    @patch('sendMail._get_indices')
    @patch('sendMail._format_message')
    @patch('sendMail.build_email')
    @patch('sendMail.send_mail')
    @patch('sendMail.send_gmail')
    @patch('sendMail.get_gmail_service')
    @patch('sendMail.sleep')
    @patch('sendMail._filter_artscroises')
    def test_generate_mailing_artscroises_success(self, mock_filter, mock_sleep, mock_get_gmail, mock_send_gmail, mock_send_mail,
                                                 mock_build, mock_format, mock_indices, mock_reader_func):
        """Test successful mailing generation for ArtsCroises profile"""
        param = Mock()
        param.max_addr_per_mail = 2
        param.pause = 0
        param.max_mails_per_hour = 100
        param.from_index = None
        param.to_index = None
        param.profile = 'artscroises'
        param.verbose = False
        param.donotsend = False
        param.message = "Template"
        param.subject = "Subject"
        param.file = None

        # Mock reader to return header and three rows
        header = ["email", "status", "group", "selected"]
        rows = [
            ["user1@example.com", "active", "Group", "x"],
            ["user2@example.com", "active", "Group", "x"],
            ["user3@example.com", "active", "Group", "x"]
        ]
        
        # We need to return an iterator that yields header then rows
        # The code does: header = next(reader, None); for row in reader:
        class Reader:
            def __init__(self, data):
                self.data = iter(data)
            def __next__(self):
                return next(self.data)
            def __iter__(self):
                return self
        
        mock_reader = Reader([header] + rows)
        mock_reader_func.return_value = (mock_reader, None)
        
        mock_indices.return_value = {"email": 0, "status": 1, "group": 2, "selected": 3}
        mock_format.return_value = "Formatted Message"
        mock_filter.return_value = False # Do not filter out anyone
        
        mock_msg = MagicMock()
        mock_msg._temp_dirs = []
        mock_build.return_value = (mock_msg, ["user1@example.com", "user2@example.com"])

        result = sendMail.generate_mailing(param)

        assert result == "OK"
        # Should be called twice: once for the first 2 users (in the loop), once for the remaining 1 user (after the loop)
        assert mock_send_mail.call_count == 2
        assert mock_build.call_count == 2

    @patch('sendMail._get_subscriber_reader')
    def test_generate_mailing_missing_config(self, mock_reader_func):
        """Test generate_mailing with missing configuration"""
        param = Mock(spec=[]) # No attributes
        
        result = sendMail.generate_mailing(param)
        assert result == "Error"

    @patch('sendMail._get_subscriber_reader')
    def test_generate_mailing_no_reader(self, mock_reader_func):
        """Test generate_mailing when reader fails to initialize"""
        param = Mock()
        param.max_addr_per_mail = 10
        param.pause = 0
        param.max_mails_per_hour = 100
        
        mock_reader_func.return_value = (None, None)
        
        result = sendMail.generate_mailing(param)
        assert result == "Error"

class TestGoogleSheetHelpers:
    """Tests for Google Sheets helper functions"""

    @patch('sendMail.ServiceAccountCredentials')
    @patch('sendMail.gspread')
    @patch('sendMail.get_secret')
    def test_open_google_db_members_sheet(self, mock_get_secret, mock_gspread, mock_sac):
        sa_key = 'sa_key'
        id_key = 'id_key'
        # Mock secrets
        def secret_side_effect(arg):
            if arg == sa_key:
                return {"type": "service_account", "client_email": "x@y"}
            if arg == id_key:
                return {"ID": "SHEET_ID"}
            return {}
        mock_get_secret.side_effect = secret_side_effect

        creds = Mock()
        mock_sac.from_json_keyfile_dict.return_value = creds

        wb = Mock()
        mock_gc = Mock()
        mock_gc.open_by_key.return_value = wb
        mock_gspread.authorize.return_value = mock_gc

        result = sendMail.openGoogleDBMembersSheet(sa_key, id_key)
        assert result == wb
        mock_gspread.authorize.assert_called_once_with(creds)
        mock_gc.open_by_key.assert_called_once_with('SHEET_ID')

    def test_read_all_sheet_default(self):
        ws = Mock()
        ws.get_all_values.return_value = [["h1", "h2"], ["a", "b"]]
        wb = Mock()
        wb.sheet1 = ws
        result = sendMail.readAllSheet(wb)
        assert result == [["h1", "h2"], ["a", "b"]]
        ws.get_all_values.assert_called_once()

    def test_read_all_sheet_named(self):
        ws = Mock()
        ws.get_all_values.return_value = [["x"]]
        wb = Mock()
        wb.worksheet.return_value = ws
        result = sendMail.readAllSheet(wb, sheet_name='Sheet2')
        assert result == [["x"]]
        wb.worksheet.assert_called_once_with('Sheet2')

class TestGetGmailService:
    """Tests for get_gmail_service function"""

    @patch('sendMail.os.path.exists', return_value=True)
    @patch('sendMail.Credentials')
    @patch('sendMail.build')
    def test_get_gmail_service_with_token_file(self, mock_build, mock_credentials, mock_exists):
        param = Mock()
        param.token_file = 'token.json'
        param.scopes = ['scope1']

        creds = Mock()
        creds.valid = True
        mock_credentials.from_authorized_user_file.return_value = creds

        service = sendMail.get_gmail_service(param)
        assert service == mock_build.return_value
        mock_credentials.from_authorized_user_file.assert_called_once_with('token.json', ['scope1'])
        mock_build.assert_called_once()

    @patch('sendMail.os.path.exists', return_value=False)
    @patch('sendMail.get_secret')
    @patch('sendMail.Credentials')
    @patch('sendMail.InstalledAppFlow')
    @patch('sendMail.build')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_gmail_service_oauth_flow(self, mock_file, mock_build, mock_flow_cls, mock_credentials, mock_get_secret, mock_exists):
        param = Mock()
        param.token_file = 'token.json'
        param.scopes = ['scope1']
        param.token_id = 'token_id'
        param.credentials_id = 'creds_id'
        param.SCOPES = ['scope1']

        # First get creds from secret (no token file)
        token_info = {'token': 'abc'}
        mock_get_secret.side_effect = [token_info, {'client_id': 'x'}]
        creds = Mock()
        creds.valid = False
        creds.expired = False
        creds.refresh_token = None
        creds.to_json.return_value = '{}'
        mock_credentials.from_authorized_user_info.return_value = creds

        flow = Mock()
        flow.run_local_server.return_value = creds
        mock_flow_cls.from_client_config.return_value = flow

        service = sendMail.get_gmail_service(param)
        assert service == mock_build.return_value
        # Should have written token file
        mock_file.assert_called_once_with('token.json', 'w')

class TestProcessFunctions:
    """Tests for process_artscroises and process_cambristi"""

    @patch('sendMail.get_secret')
    @patch('sendMail.process_attachments')
    @patch('sendMail.generate_mailing')
    @patch('sendMail.getpass')
    @patch('builtins.open', new_callable=mock_open, read_data="key: value")
    def test_process_artscroises_success(self, mock_file, mock_getpass, mock_generate, mock_proc_attach, mock_get_secret):
        """Test process_artscroises success path"""
        args = Mock()
        args.config = "config.yml"
        args.profile = "artscroises"
        args.conf = {
            "artscroises": {
                "MAILCONFIG": "secret_id",
                "max_mails_per_hour": 100,
                "max_addr_per_mail": 10,
                "pause": 1
            }
        }
        args.body = None
        args.subject = None
        args.wait = None
        args.test = False
        
        mock_get_secret.return_value = {"password": "secret_password"}
        mock_proc_attach.return_value = (["test.pdf"], None, [])
        mock_generate.return_value = "OK"
        
        result = sendMail.process_artscroises(args)
        assert result is None # returns None
        mock_generate.assert_called_once()

    @patch('sendMail.get_secret')
    @patch('sendMail.process_attachments')
    @patch('sendMail.generate_mailing')
    def test_process_cambristi_success(self, mock_generate, mock_proc_attach, mock_get_secret):
        """Test process_cambristi success path"""
        args = Mock()
        args.profile = "cambristi"
        args.conf = {
            "cambristi": {
                "MAILCONFIG": "secret_id"
            }
        }
        
        mock_get_secret.return_value = {"some": "config"}
        mock_proc_attach.return_value = (["test.html"], None, [])
        mock_generate.return_value = "OK"
        
        result = sendMail.process_cambristi(args)
        assert result is None
        mock_generate.assert_called_once()


def test_module_imports():
    """Test that the module imports successfully"""
    assert hasattr(sendMail, 'Dict2Class')
    assert hasattr(sendMail, 'build_email')
    assert hasattr(sendMail, 'send_mail')
    assert hasattr(sendMail, 'generate_mailing')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
