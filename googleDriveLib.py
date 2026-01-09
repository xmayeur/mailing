"""

Based on : https://medium.com/@matheodaly.md/using-google-drive-api-with-python-and-a-service-account-d6ae1f6456c2

"""

import io
import logging
from os.path import join, basename

from getSecrets import get_secret
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials
import sys


def _init_log():
    """Configures shared logger for console and file"""
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


def connect_google_driver():
    try:
        scope = ["https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            get_secret("artscroisesServiceAccount"), scope
        )
        return build("drive", "v3", credentials=credentials)
    except HttpError as e:
        _log.error(e)
        return None


def get_files(service=None, folder_id=None):
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


def rename_file(service=None, fileId=None, newTitle=None):
    if service is None or fileId is None or newTitle is None:
        return
    body = {"name": newTitle}
    return service.files().update(fileId=fileId, body=body).execute()


def download_file(service=None, files=[], folder="input"):
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
                print(f"Download {int(status.progress() * 100)}.")

            file_retrieved = file.getvalue()
            with open(join(folder, f["name"]), "wb") as fd:
                fd.write(file_retrieved)

        except HttpError as error:
            _log.error(f'An error occurred: {error} with file {f["name"]}')


def upload_file(service, file, mimetype="text/csv"):
    fb = basename(file)
    file_metadata = {"name": fb}
    media = MediaFileUpload(file, mimetype)

    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )


if __name__ == "__main__":
    conn = connect_google_driver()
    id = get_secret("artscroisesmailing")["mailing_folder"]
    items = get_files(conn, folder_id=id)
    download_file(conn, items)
