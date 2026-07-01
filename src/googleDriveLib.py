"""Google Drive API integration using service account credentials.

Provides functions to:
- Connect to Google Drive via service account
- List files from Drive folders
- Download files to local folder
- Upload files to Drive
- Rename Drive files

Uses service account credentials stored in secrets vault.
Logs output to console and sendMail.log file.
"""

import io
import logging
import sys
from os.path import basename, join
from typing import Any, cast

from getSecrets import get_secret
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials


def _init_log() -> logging.Logger:
    """Initialize logger for console and file output.

    Creates logger that writes to both stdout and sendMail.log file.

    Returns:
        Configured Logger instance with both handlers
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    # Use absolute path for log file to work in bundled app
    from pathlib import Path

    log_path = Path.home() / "sendMail.log"
    file_handler = logging.FileHandler(str(log_path))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)

    return logger


_log = _init_log()


def connect_google_driver(service_account_id: str = "artscroisesServiceAccount") -> Any:
    """Connect to Google Drive API using service account credentials.

    Retrieves service account credentials from secrets vault and builds
    Drive API service object.

    Args:
        service_account_id: Service account key name in secrets vault

    Returns:
        Google Drive API service object, or None if connection fails
    """
    creds = get_secret(service_account_id)
    try:
        scope = ["https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, cast(Any, scope))
        return build("drive", "v3", credentials=credentials)
    except HttpError as e:
        _log.exception(e)
        return None


def get_files(service: Any = None, folder_id: str | None = None) -> dict[str, Any] | None:
    """List files from Google Drive folder (excluding published files).

    Args:
        service: Google Drive API service object
        folder_id: Google Drive folder ID to list files from

    Returns:
        Dict with 'files' key containing list of file metadata dicts,
        or None if operation fails or parameters missing
    """
    if service is None or folder_id is None:
        return None

    try:
        result = (
            service.files()
            .list(
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                q=f'"{folder_id}" in parents and not name contains "published" ',
            )
            .execute()
        )
        return result  # type: ignore[no-any-return]
    except HttpError as e:
        _log.exception(e)
        return None


def rename_file(service: Any = None, file_id: str | None = None, new_title: str | None = None) -> dict[str, Any] | None:
    """Rename file in Google Drive.

    Args:
        service: Google Drive API service object
        file_id: ID of file to rename
        new_title: New name for the file

    Returns:
        Updated file metadata dict, or None if any parameter is missing
    """
    if service is None or file_id is None or new_title is None:
        return None
    body = {"name": new_title}
    return service.files().update(fileId=file_id, body=body).execute()  # type: ignore[no-any-return]


def download_file(
    service: Any = None,
    files: list[dict[str, Any]] | None = None,
    folder: str = "input",
) -> None:
    """Download files from Google Drive to local folder.

    Downloads each file in the list with progress reporting.

    Args:
        service: Google Drive API service object
        files: List of file metadata dicts with 'id' and 'name' keys
        folder: Local folder path to save files to (default: "input")
    """
    if service is None or files is None or folder is None:
        return
    for f in files:
        try:
            request_file = service.files().get_media(fileId=f["id"])
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request_file)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                _log.debug(f"Download {int(status.progress() * 100)}%")

            file_retrieved = file.getvalue()
            with open(join(folder, f["name"]), "wb") as fd:
                fd.write(file_retrieved)

        except HttpError as error:
            _log.exception(f"An error occurred: {error} with file {f['name']}")


def upload_file(service: Any, file: str, mimetype: str = "text/csv") -> None:
    """Upload file to Google Drive.

    Args:
        service: Google Drive API service object
        file: Path to local file to upload
        mimetype: MIME type of file (default: "text/csv")
    """
    fb = basename(file)
    file_metadata = {"name": fb}
    media = MediaFileUpload(file, mimetype)

    service.files().create(body=file_metadata, media_body=media, fields="id").execute()
