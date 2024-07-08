"""

Based on : https://medium.com/@matheodaly.md/using-google-drive-api-with-python-and-a-service-account-d6ae1f6456c2

"""

import io
import logging
from os.path import join

from getSecrets import get_secret, get_user_pwd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials


def _init_log():
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
        scope = ['https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(get_secret('artscroisesServiceAccount'), scope)
        return build('drive', 'v3', credentials=credentials)
    except HttpError as e:
        log.error(e)
        return None


def get_files(service):
    mailing_folder_id = "1KR_kQrTj0Cmej2GVYmv9qjQS2zXzBdWe"
    try:
        return service.files().list(pageSize=1000,
                                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                                    q=f'"{mailing_folder_id}" in parents and not name contains "published" ').execute()
    except HttpError as e:
        log.error(e)
        return None


def rename_file(service, fileId, newTitle):
    body = {'name': newTitle}
    return service.files().update(fileId=fileId, body=body).execute()


def download_file(service, files, folder='input'):

    for f in files:
        try:
            request_file = service.files().get_media(fileId=f["id"])
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request_file)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f'Download {int(status.progress() * 100)}.')

            file_retrieved = file.getvalue()
            with open(join(folder, f['name']), 'wb') as f:
                f.write(file_retrieved)
            renameFile(service, f['id'], 'published_'+f['name'])

        except HttpError as error:
            log.error(f'An error occurred: {error} with file {f["name"]}')


if __name__ == '__main__':

    conn = connect_google_driver()
    items = get_files(conn)
    download_file(conn, items)



