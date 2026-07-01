"""
Unit tests for src/googleDriveLib.py module
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add source directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "src")))

# Mock external dependencies before importing
mock_get_secret = MagicMock(return_value={"key": "value"})
sys.modules["getSecrets"] = MagicMock()
sys.modules["getSecrets"].get_secret = mock_get_secret  # type: ignore[attr-defined]


# Create a proper HttpError that inherits from Exception
class MockHttpError(Exception):
    pass


sys.modules["googleapiclient"] = MagicMock()
sys.modules["googleapiclient.discovery"] = MagicMock()
sys.modules["googleapiclient.errors"] = MagicMock()
sys.modules["googleapiclient.errors"].HttpError = MockHttpError  # type: ignore[attr-defined]
sys.modules["googleapiclient.http"] = MagicMock()
sys.modules["oauth2client"] = MagicMock()
sys.modules["oauth2client.service_account"] = MagicMock()

import googleDriveLib as gd  # noqa: E402,N813


class TestConnectGoogleDriver:
    """Tests for connect_google_driver function"""

    @patch("googleDriveLib.get_secret")
    @patch("googleDriveLib.ServiceAccountCredentials")
    @patch("googleDriveLib.build")
    def test_connect_success(self, mock_build, mock_creds, mock_secret):
        """Test successful connection to Google Drive"""
        mock_secret.return_value = {"key": "value"}
        mock_creds.from_json_keyfile_dict.return_value = Mock()
        mock_build.return_value = Mock()

        result = gd.connect_google_driver("test_account")

        assert result is not None
        mock_secret.assert_called_once_with("test_account")
        mock_build.assert_called_once()

    @patch("googleDriveLib.get_secret")
    @patch("googleDriveLib.ServiceAccountCredentials")
    @patch("googleDriveLib.build")
    @patch("googleDriveLib.HttpError", Exception)
    def test_connect_failure(self, mock_build, mock_creds, mock_secret):
        """Test failed connection to Google Drive"""
        mock_secret.return_value = {"key": "value"}
        mock_build.side_effect = Exception("Connection failed")

        result = gd.connect_google_driver("test_account")

        assert result is None

    @patch("googleDriveLib.get_secret")
    @patch("googleDriveLib.ServiceAccountCredentials")
    @patch("googleDriveLib.build")
    def test_connect_default_account(self, mock_build, mock_creds, mock_secret):
        """Test connection with default service account"""
        mock_secret.return_value = {"key": "value"}
        mock_creds.from_json_keyfile_dict.return_value = Mock()
        mock_build.return_value = Mock()

        gd.connect_google_driver()

        mock_secret.assert_called_once_with("artscroisesServiceAccount")


class TestGetFiles:
    """Tests for get_files function"""

    def test_get_files_success(self):
        """Test successful file listing"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        mock_service.files.return_value = mock_files
        mock_files.list.return_value = mock_list
        mock_list.execute.return_value = {"files": [{"id": "123", "name": "test.pdf"}]}

        result = gd.get_files(service=mock_service, folder_id="folder123")

        assert result is not None
        assert "files" in result
        assert len(result["files"]) == 1

    def test_get_files_no_service(self):
        """Test get_files with no service"""
        result = gd.get_files(service=None, folder_id="folder123")
        assert result is None

    def test_get_files_no_folder(self):
        """Test get_files with no folder_id"""
        mock_service = Mock()
        result = gd.get_files(service=mock_service, folder_id=None)
        assert result is None

    @patch("googleDriveLib.HttpError", Exception)
    def test_get_files_http_error(self):
        """Test get_files with HTTP error"""
        mock_service = Mock()
        mock_files = Mock()
        mock_list = Mock()
        mock_list.execute.side_effect = Exception("HTTP Error")

        mock_service.files.return_value = mock_files
        mock_files.list.return_value = mock_list

        result = gd.get_files(service=mock_service, folder_id="folder123")
        assert result is None


class TestRenameFile:
    """Tests for rename_file function"""

    def test_rename_file_success(self):
        """Test successful file renaming"""
        mock_service = Mock()
        mock_files = Mock()
        mock_update = Mock()
        mock_update.execute.return_value = {"id": "123", "name": "new_name.pdf"}

        mock_service.files.return_value = mock_files
        mock_files.update.return_value = mock_update

        result = gd.rename_file(service=mock_service, file_id="file123", new_title="new_name.pdf")

        assert result is not None
        mock_files.update.assert_called_once_with(fileId="file123", body={"name": "new_name.pdf"})

    def test_rename_file_no_service(self):
        """Test rename_file with no service"""
        result = gd.rename_file(service=None, file_id="123", new_title="new.pdf")
        assert result is None

    def test_rename_file_no_file_id(self):
        """Test rename_file with no file ID"""
        mock_service = Mock()
        result = gd.rename_file(service=mock_service, file_id=None, new_title="new.pdf")
        assert result is None

    def test_rename_file_no_title(self):
        """Test rename_file with no new title"""
        mock_service = Mock()
        result = gd.rename_file(service=mock_service, file_id="123", new_title=None)
        assert result is None


class TestDownloadFile:
    """Tests for download_file function"""

    @patch("googleDriveLib.MediaIoBaseDownload")
    @patch("googleDriveLib.io.BytesIO")
    @patch("builtins.open", create=True)
    def test_download_file_success(self, mock_open_file, mock_bytesio, mock_downloader_class):
        """Test successful file download"""
        mock_service = Mock()
        mock_files = Mock()
        mock_get_media = Mock()

        mock_service.files.return_value = mock_files
        mock_files.get_media.return_value = mock_get_media

        # Mock BytesIO
        mock_file = Mock()
        mock_file.getvalue.return_value = b"file content"
        mock_bytesio.return_value = mock_file

        # Mock downloader - next_chunk returns (status, done)
        mock_downloader = Mock()
        mock_status = Mock()
        mock_status.progress.return_value = 1.0
        # First call returns (status, False), second call returns (status, True)
        mock_downloader.next_chunk.side_effect = [
            (mock_status, False),
            (mock_status, True),
        ]
        mock_downloader_class.return_value = mock_downloader

        files = [{"id": "file123", "name": "test.pdf"}]

        gd.download_file(service=mock_service, files=files, folder="downloads")

        mock_files.get_media.assert_called_once_with(fileId="file123")

    def test_download_file_no_service(self):
        """Test download_file with no service"""
        files = [{"id": "123", "name": "test.pdf"}]
        result = gd.download_file(service=None, files=files)
        assert result is None

    def test_download_file_no_files(self):
        """Test download_file with no files"""
        mock_service = Mock()
        result = gd.download_file(service=mock_service, files=None)
        assert result is None

    def test_download_file_empty_list(self):
        """Test download_file with empty file list"""
        mock_service = Mock()
        gd.download_file(service=mock_service, files=[])
        # Should return None (nothing to process)
        # Function doesn't explicitly return but completes


class TestUploadFile:
    """Tests for upload_file function"""

    def test_upload_file_success(self):
        """Test successful file upload"""
        with (
            patch("googleDriveLib.MediaFileUpload") as mock_media_upload,
            patch("googleDriveLib.basename") as mock_basename,
        ):
            mock_service = Mock()
            mock_files = Mock()
            mock_create = Mock()

            mock_service.files.return_value = mock_files
            mock_files.create.return_value = mock_create
            mock_create.execute.return_value = {"id": "uploaded123"}

            mock_basename.return_value = "test.csv"
            mock_media_upload.return_value = Mock()

            gd.upload_file(service=mock_service, file="/path/to/test.csv", mimetype="text/csv")

            mock_files.create.assert_called_once()
            mock_media_upload.assert_called_once_with("/path/to/test.csv", "text/csv")

    def test_upload_file_custom_mimetype(self):
        """Test file upload with custom MIME type"""
        with (
            patch("googleDriveLib.MediaFileUpload") as mock_media_upload,
            patch("googleDriveLib.basename") as mock_basename,
        ):
            mock_service = Mock()
            mock_files = Mock()
            mock_create = Mock()
            mock_create.execute.return_value = {"id": "uploaded123"}

            mock_service.files.return_value = mock_files
            mock_files.create.return_value = mock_create

            mock_basename.return_value = "test.pdf"
            mock_media_upload.return_value = Mock()

            gd.upload_file(
                service=mock_service,
                file="/path/to/test.pdf",
                mimetype="application/pdf",
            )

            # Verify MediaFileUpload was called with the custom mimetype
            mock_media_upload.assert_called_once_with("/path/to/test.pdf", "application/pdf")


class TestInitLog:
    """Tests for _init_log function"""

    def test_init_log_creates_handlers(self):
        """Test that _init_log creates both handlers"""
        with (
            patch("logging.FileHandler") as mock_file,
            patch("logging.StreamHandler") as mock_stream,
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            mock_file.return_value = Mock()
            mock_stream.return_value = Mock()

            gd._init_log()

            # Verify logger setup
            mock_logger.setLevel.assert_called()
            assert mock_logger.addHandler.call_count == 2  # Should add both handlers


def test_module_imports():
    """Test that the module imports successfully"""
    assert hasattr(gd, "connect_google_driver")
    assert hasattr(gd, "get_files")
    assert hasattr(gd, "download_file")
    assert hasattr(gd, "upload_file")
    assert hasattr(gd, "rename_file")
    assert hasattr(gd, "_init_log")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
