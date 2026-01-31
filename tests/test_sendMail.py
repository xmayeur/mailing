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
sys.modules['gspread'] = MagicMock()
sys.modules['yaml'] = MagicMock()
sys.modules['bs4'] = MagicMock()
sys.modules['certifi'] = MagicMock()
sys.modules['getSecrets'] = MagicMock()
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
sys.modules['oauth2client'] = MagicMock()
sys.modules['oauth2client.service_account'] = MagicMock()
sys.modules['googleDriveLib'] = MagicMock()
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
        with patch('sendMail.magic') as mock_magic:
            mock_magic.from_file.return_value = "application/pdf"
            result = sendMail.guess_type("test.pdf")
            assert result == "application/pdf"

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


class TestBillit:
    """Tests for Billit invoice class"""

    @patch('sendMail.get_secret')
    def test_billit_init_prod(self, mock_secret):
        """Test Billit initialization in production mode"""
        mock_secret.return_value = {
            "token": "prod_token",
            "baseUrl": "https://prod.api.com",
            "devToken": "dev_token",
            "devBaseUrl": "https://dev.api.com"
        }

        invoice = sendMail.Billit(prod=True)
        assert invoice.token == "prod_token"
        assert invoice.base == "https://prod.api.com"

    @patch('sendMail.get_secret')
    def test_billit_init_dev(self, mock_secret):
        """Test Billit initialization in development mode"""
        mock_secret.return_value = {
            "token": "prod_token",
            "baseUrl": "https://prod.api.com",
            "devToken": "dev_token",
            "devBaseUrl": "https://dev.api.com"
        }

        invoice = sendMail.Billit(prod=False)
        assert invoice.token == "dev_token"
        assert invoice.base == "https://dev.api.com"


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


def test_module_imports():
    """Test that the module imports successfully"""
    assert hasattr(sendMail, 'Dict2Class')
    assert hasattr(sendMail, 'Billit')
    assert hasattr(sendMail, 'build_email')
    assert hasattr(sendMail, 'send_mail')
    assert hasattr(sendMail, 'generate_mailing')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
