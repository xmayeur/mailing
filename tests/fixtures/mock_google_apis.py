"""Mock Google API clients for integration testing.

Provides reusable pytest fixtures that mock Google Sheets, Google Drive,
and Gmail API clients without requiring real credentials or network calls.

Usage:
    import pytest
    from tests.fixtures.mock_google_apis import mock_google_drive_service

    def test_with_mock_drive(mock_google_drive_service):
        service = mock_google_drive_service
        files = service.files().list().execute()
        assert isinstance(files, dict)
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_google_drive_service():
    """Mock Google Drive service client.

    Returns a MagicMock that behaves like googleapiclient.discovery.build()
    result for Google Drive API v3.

    Provides methods:
    - files().list().execute() → returns dict with 'files' list
    - files().get_media().execute() → returns bytes
    - files().create().execute() → returns dict with file metadata
    """
    service = MagicMock()

    # Mock files().list().execute()
    service.files().list().execute.return_value = {
        "files": [
            {"id": "file1", "name": "test.txt"},
            {"id": "file2", "name": "test.pdf"},
        ]
    }

    # Mock files().get_media().execute()
    service.files().get_media().execute.return_value = b"file content"

    # Mock files().create().execute()
    service.files().create().execute.return_value = {
        "id": "newfile123",
        "name": "uploaded.txt",
    }

    return service


@pytest.fixture
def mock_google_sheets_service():
    """Mock Google Sheets service client.

    Returns a MagicMock that behaves like googleapiclient.discovery.build()
    result for Google Sheets API v4.

    Provides methods:
    - spreadsheets().values().get().execute() → returns dict with values
    - spreadsheets().values().append().execute() → returns update response
    """
    service = MagicMock()

    # Mock spreadsheets().values().get().execute()
    service.spreadsheets().values().get().execute.return_value = {
        "values": [
            ["Name", "Email", "Status"],
            ["Alice", "alice@example.com", "active"],
            ["Bob", "bob@example.com", "inactive"],
        ]
    }

    # Mock spreadsheets().values().append().execute()
    service.spreadsheets().values().append().execute.return_value = {
        "spreadsheetId": "sheet123",
        "updates": {"updatedCells": 1},
    }

    return service


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service client.

    Returns a MagicMock that behaves like googleapiclient.discovery.build()
    result for Gmail API v1.

    Provides methods:
    - users().messages().send().execute() → returns dict with messageId
    - users().messages().get().execute() → returns dict with message data
    """
    service = MagicMock()

    # Mock users().messages().send().execute()
    service.users().messages().send().execute.return_value = {
        "id": "msg123",
        "threadId": "thread456",
    }

    # Mock users().messages().get().execute()
    service.users().messages().get().execute.return_value = {
        "id": "msg123",
        "threadId": "thread456",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Email"},
            ]
        },
    }

    return service


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth2 credentials.

    Returns a MagicMock that behaves like google.oauth2.credentials.Credentials.
    """
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "refresh_token_123"
    creds.to_json.return_value = '{"type": "authorized_user"}'
    return creds


@pytest.fixture
def mock_google_api_build(monkeypatch):
    """Fixture that patches googleapiclient.discovery.build.

    Automatically returns appropriate mock service based on serviceName:
    - 'drive' → mock_google_drive_service
    - 'sheets' → mock_google_sheets_service
    - 'gmail' → mock_gmail_service

    Usage:
        def test_with_build_patch(mock_google_api_build):
            from googleapiclient.discovery import build
            service = build('drive', 'v3', credentials=creds)
            # service is now a mock
    """
    from unittest.mock import MagicMock, patch

    drive_service = MagicMock()
    sheets_service = MagicMock()
    gmail_service = MagicMock()

    def _build(service_name, version, **kwargs):
        if service_name == "drive":
            return drive_service
        elif service_name == "sheets":
            return sheets_service
        elif service_name == "gmail":
            return gmail_service
        return MagicMock()

    with patch("googleapiclient.discovery.build", side_effect=_build):
        yield _build


# Fixture for gspread (higher-level Google Sheets library)
@pytest.fixture
def mock_gspread_client():
    """Mock gspread client for Google Sheets operations.

    Returns a MagicMock that behaves like gspread.Client.
    """
    client = MagicMock()

    # Mock open_by_key()
    spreadsheet = MagicMock()
    worksheet = MagicMock()

    worksheet.get_all_values.return_value = [
        ["Name", "Email", "Status"],
        ["Alice", "alice@example.com", "active"],
        ["Bob", "bob@example.com", "inactive"],
    ]

    spreadsheet.worksheets.return_value = [worksheet]
    client.open_by_key.return_value = spreadsheet

    return client


# Fixture for error scenarios
@pytest.fixture
def mock_google_api_errors():
    """Fixture providing common Google API error mocks.

    Returns dict with common error types:
    - auth_error: AuthenticationError (invalid credentials)
    - rate_limit_error: HttpError 429 (too many requests)
    - not_found_error: HttpError 404 (file not found)
    """
    from googleapiclient.errors import HttpError

    return {
        "not_found": HttpError(
            resp=MagicMock(status=404), content=b'{"error": {"message": "Not found"}}'
        ),
        "forbidden": HttpError(
            resp=MagicMock(status=403),
            content=b'{"error": {"message": "Access denied"}}',
        ),
        "rate_limit": HttpError(
            resp=MagicMock(status=429),
            content=b'{"error": {"message": "Rate limit exceeded"}}',
        ),
    }
