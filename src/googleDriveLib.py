"""
Module for interacting with Google Drive APIs through Service Account credentials.

This module provides functionality to connect to Google Drive, retrieve file metadata,
download files, upload files, and rename existing files in a Google Drive account.
It uses the Google APIs Client Library for Python and requires `ServiceAccountCredentials`
for authentication.

Dependencies:
- googleapiclient.discovery
- googleapiclient.http
- oauth2client.service_account
- A function called `get_secret` for retrieving service account credentials.

Logger output is configured to display messages on the console and to save them to a file
called "sendMail.log".


Based on : https://medium.com/@matheodaly.md/using-google-drive-api-with-python-and-a-service-account-d6ae1f6456c2


"""

import io
import logging
import sys
from os.path import basename, join

from getSecrets import get_secret
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials


def _init_log():
    """
    Configures and initializes a logger for console and file output.

    Creates a logger that writes to both console (stdout) and a file named "sendMail.log".
    Sets the logging level to INFO for the root logger and DEBUG for both handlers.

    :return: Configured logger instance.
    :rtype: logging.Logger
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler("sendMail.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)

    return logger


_log = _init_log()


def connect_google_driver(service_account_id="artscroisesServiceAccount"):
    """
    Connects to Google Drive API using service account credentials.

    :param service_account_id: The ID of the service account to retrieve from secrets.
    :type service_account_id: str
    :return: Google Drive API service object, or None if connection fails.
    :rtype: googleapiclient.discovery.Resource or None
    """
    creds = get_secret(service_account_id)
    try:
        scope = ["https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)  # pyright: ignore
        return build("drive", "v3", credentials=credentials)
    except HttpError as e:
        _log.error(e)
        return None


def get_files(service=None, folder_id=None):
    """
    Retrieves a list of files from a specific Google Drive folder.

    Lists files that are not marked as "published" from the specified folder.
    Returns file metadata including ID, name, MIME type, size, and modification time.

    :param service: Google Drive API service object.
    :type service: googleapiclient.discovery.Resource
    :param folder_id: The ID of the Google Drive folder to retrieve files from.
    :type folder_id: str
    :return: Dictionary containing file metadata, or None if operation fails.
    :rtype: dict or None
    """
    if service is None or folder_id is None:
        return None

    try:
        return (
            service.files()
            .list(
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                q=f'"{folder_id}" in parents and not name contains "published" ',
            )
            .execute()
        )
    except HttpError as e:
        _log.error(e)
        return None


def rename_file(service=None, file_id=None, new_title=None):
    """
    Renames a file in Google Drive.

    :param service: Google Drive API service object.
    :type service: googleapiclient.discovery.Resource
    :param file_id: The ID of the file to rename.
    :type file_id: str
    :param new_title: The new name for the file.
    :type new_title: str
    :return: Updated file metadata, or None if parameters are invalid.
    :rtype: dict or None
    """
    if service is None or file_id is None or new_title is None:
        return
    body = {"name": new_title}
    return service.files().update(fileId=file_id, body=body).execute()


def download_file(service=None, files=None, folder="input"):
    """
    Downloads files from Google Drive to a local folder.

    Downloads each file from the provided list to the specified local folder.
    Progress is printed to console during download.

    :param service: Google Drive API service object.
    :type service: googleapiclient.discovery.Resource
    :param files: List of file metadata dictionaries containing at least 'id' and 'name'.
    :type files: list[dict]
    :param folder: Local folder path where files will be saved. Defaults to "input".
    :type folder: str
    :return: None
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
            _log.error(f"An error occurred: {error} with file {f['name']}")


def upload_file(service, file, mimetype="text/csv"):
    """
    Uploads a file to Google Drive.

    :param service: Google Drive API service object.
    :type service: googleapiclient.discovery.Resource
    :param file: Path to the local file to upload.
    :type file: str
    :param mimetype: MIME type of the file. Defaults to "text/csv".
    :type mimetype: str
    :return: Uploaded file metadata containing the file ID.
    :rtype: dict
    """
    fb = basename(file)
    file_metadata = {"name": fb}
    media = MediaFileUpload(file, mimetype)

    service.files().create(body=file_metadata, media_body=media, fields="id").execute()
