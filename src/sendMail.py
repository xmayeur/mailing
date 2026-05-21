#!/usr/bin/env python
"""Bulk email campaign management system for organizations.

Provides functionality for sending email campaigns to subscribers via SMTP or Gmail API,
with support for:
- Google Sheets and CSV subscriber databases
- HTML email templates with inline image support
- Rate limiting and batch processing
- Google Drive integration for attachments
- Markdown to HTML conversion
- Flexible filtering based on subscriber attributes
- Email profiles with IMAP/SMTP configuration

Main usage:
    python src/sendMail.py --profile <profile_name> -s "Subject" [files...]

Key classes:
    Dict2Class: Convert dictionaries to objects

Key functions:
    build_email: Build MIME email message
    send_mail: Send email via SMTP
    send_gmail: Send email via Gmail API
    filter: Filter subscriber rows based on criteria
    generate_mailing: Generate and send campaign emails
"""
from __future__ import annotations

import argparse
import base64
import csv
import email.mime.application
import email.utils
import imaplib
import logging
import os
import re
import shutil
import ssl
import sys
import tempfile
import urllib.parse
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from getpass import getpass
from glob import glob
from os import getenv, mkdir
from os.path import exists, join
from pathlib import Path
from smtplib import SMTP, SMTPAuthenticationError, SMTPException
from time import sleep, time
from typing import Any, cast
from uuid import uuid4

import gspread
import markdown2 as md
import requests
import yaml
from bs4 import BeautifulSoup
from getSecrets import get_secret
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import errors
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image

import googleDriveLib as gd  # noqa: N813
from profile_manager import Profile, ProfileLoadError

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
_CSP_IMG_DOMAIN = "{_CSP_IMG_DOMAIN}"
_HTML_PARSER = "html.parser"
_CID_INLINE_DOMAIN = "inline.img"
_OP_IS_NOT_EMPTY = "is not empty"
_OP_IS_EQUAL_TO = "is equal to"
_OP_IS_NOT_EQUAL_TO = "is not equal to"
_OP_GREATER_THAN = "greater than"
_OP_LESS_THAN = "less than"
_OP_GREATER_THAN_OR_EQUAL = "greater than or equal to"
_OP_LESS_THAN_OR_EQUAL = "less than or equal to"
_OP_ONE_OF = "one of"
_OP_NOT_ONE_OF = "not one of"
_OP_MATCHES = "matches"
_OP_DOES_NOT_MATCH = "does not match"
_OP_CONTAINS = "contains"
_OP_DOES_NOT_CONTAIN = "does not contain"
_OP_STARTS_WITH = "starts with"
_OP_ENDS_WITH = "ends with"
_OP_IS = "is"
_OP_IS_NOT = "is not"
_OP_IS_BOUNCED = "is bounced"
_OP_IS_NOT_BOUNCED = "is not bounced"


def get_default_config_path() -> str | int:
    """Get default configuration file path based on OS home directory.

    Returns:
        str | int: Path to sendMail.yml in user's .config directory
        or -1 if file was created with defaults
    """
    home = getenv("USERPROFILE") if os.name == "nt" else getenv("HOME")
    home = home or ""
    cfg = join(home, ".config", "sendMail.yml")
    if not exists(cfg):
        config_dir = join(home, ".config")
        if not exists(config_dir):
            mkdir(config_dir)
        default = {
            "default": {
                "username": "jdoe",
                "password": "",
                "sender": "john.doe@example.com",
                "sendername": "John Doe",
                "database": "subscribers.csv",
                "domain": "example.com",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "sent_folder": "Sent",
                "pause": 1,
                "default_message": "Hello",
                "styles": "./css/styles.css",
                "filter": {
                    "email": _OP_IS_NOT_EMPTY,
                    "bounced": "is not bounced",
                    "cotisation": "greater than 0",
                    "first_name": 'one of "Jean", "Xavier"',
                },
                "filter_test": {"email": "is john.doe@example.com"},
            }
        }
        with open(cfg, "w") as f:
            yaml.dump(default, f)
        log.warning(
            f"Configuration file created at '{cfg}' with default values - Please configure your default parameters"
        )
        return -1
    return cfg


def init_log(log_file: str | None = None) -> logging.Logger:
    """Initialize logging configuration.

    Sets up logging with default format, level, and optional file handler.

    Args:
        log_file: Path to log file. If None, logs to console only (default: None)

    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Use absolute path for log file to work in bundled app
_log_path = str(Path.home() / "sendMail.log")
log = init_log(log_file=_log_path)


# for artscroises profile
def open_google_db_members_sheet(sa: str, sheet_id: str) -> Any:
    """Open Google Sheet and return spreadsheet object.

    Args:
        sa: Service account entry name in secret vault
        sheet_id: Google Sheet ID entry name in secret vault

    Returns:
        gspread Spreadsheet object for reading/writing data
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(get_secret(sa), scope)  # pyright: ignore
    gc = gspread.authorize(creds)  # pyright: ignore

    spreadsheet_id = get_secret(sheet_id)["ID"]
    wb = gc.open_by_key(spreadsheet_id)
    return wb


def read_all_sheet(wb: Any, sheet_name: str = "") -> list[list[Any]]:
    """Read all values from a Google Sheet.

    Args:
        wb: gspread Spreadsheet object
        sheet_name: Sheet name to read. If empty, reads first sheet

    Returns:
        List of lists containing all sheet values (array of arrays)
    """
    ws = wb.sheet1 if not sheet_name else wb.worksheet(sheet_name)
    return list(ws.get_all_values())


def get_google_sheets_schema(sa: str, sheet_id: str) -> list[str]:
    """Extract field names (header row) from Google Sheet for validation.

    Args:
        sa: Service account entry name in secret vault
        sheet_id: Google Sheet ID entry name in secret vault

    Returns:
        List of field names from first row of Google Sheet, or empty list on error
    """
    try:
        wb = open_google_db_members_sheet(sa, sheet_id)
        data = read_all_sheet(wb)
        if data and len(data) > 0:
            # First row contains field names
            headers = [h.strip() for h in data[0] if h.strip()]
            return headers
        return []
    except Exception as e:  # noqa: BLE001
        log.warning("Could not extract Google Sheets schema: %s", e)
        return []


class Dict2Class:
    """Convert dictionary to object with lowercase attribute names.

    Allows dict-like configs to be accessed as objects (obj.key instead of dict['key']).
    All keys are converted to lowercase attribute names.

    Args:
        my_dict: Dictionary to convert to object

    Example:
        config = Dict2Class({'Name': 'John', 'Email': 'j@example.com'})
        config.name  # 'John'
        config.email  # 'j@example.com'
    """

    def __init__(self, my_dict: dict[str, Any]) -> None:
        for key in my_dict:
            object.__setattr__(self, key.lower(), my_dict[key])

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)


def guess_type(filepath: str) -> str | None:
    """Detect MIME type of a file by content or extension.

    Tries magic-based detection first (file content), falls back to
    extension-based guessing if magic not available.

    Args:
        filepath: Path to file to identify

    Returns:
        MIME type string (e.g., 'image/png') or None if detection fails
    """
    try:
        import magic  # type: ignore

        result: str | None = magic.from_file(filepath, mime=True)
        return result
    except (ImportError, ModuleNotFoundError):
        import mimetypes

        # Initialize Office file MIME types (not registered on all platforms)
        mimetypes.add_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx")
        mimetypes.add_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx")
        mimetypes.add_type("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx")

        return mimetypes.guess_type(filepath)[0]


def file_to_base64(filepath: str) -> str:
    """Encode file contents as base64 string.

    Handles both local files and HTTP URLs.

    Args:
        filepath: Local file path or HTTP URL

    Returns:
        Base64 encoded file content as string, or empty string on error
    """
    import base64

    encoded_bytes: bytes
    if "http" in filepath:
        img = requests.get(filepath)
        if img.status_code != 200:
            return ""
        encoded_bytes = base64.b64encode(img.content)
    else:
        with open(filepath, "rb") as f:
            encoded_bytes = base64.b64encode(f.read())
    return encoded_bytes.decode("utf-8")


def make_html_images_inline(in_filepath: str, out_filepath: str | None = None) -> str:
    """
    Takes an HTML file and writes a new version with inline Base64 encoded
    images.
    :param in_filepath: Input file path (HTML)
    :type in_filepath: str
    :param out_filepath: Output file path (HTML) - if None, return the data
    :type out_filepath: str
    :returns the html data with inline images
    """
    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    with open(in_filepath) as file:
        soup = BeautifulSoup(file, _HTML_PARSER)
    for img in soup.find_all("img"):
        src = str(img.attrs["src"])
        if "http" in src:
            img_path = urllib.parse.unquote(src)
        else:
            img_path = urllib.parse.unquote(os.path.join(basepath, src))
        if re.match(r"data:[^;]+;base64,", src):
            # Already an inline base64 data URI — keep as-is
            pass
        else:
            mimetype = guess_type(img_path)
            img.attrs["src"] = f"data:{mimetype};base64,{file_to_base64(img_path)}"

    if out_filepath:
        with open(out_filepath, "w") as of:
            of.write(str(soup))
    return str(soup)


def prepare_html_for_cid(in_filepath: str) -> tuple[str, list[tuple[str, str]]]:
    """Prepare HTML content for embedding inline images as Content-ID (CID) references.

    This function processes an HTML file, reads its content, identifies the <img>
    tags, and replaces their `src` attributes with Content-ID (CID) references,
    allowing the images to be embedded inline in emails. It handles local image
    paths and excludes external or base64-encoded images. A mapping of the local
    image paths and the generated CIDs is returned.

    Args:
        in_filepath: File path to HTML file to process

    Returns:
        Tuple of modified HTML content and list of (path, CID) tuples for embedded images
    """
    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    with open(in_filepath, encoding="utf-8") as file:
        soup = BeautifulSoup(file, _HTML_PARSER)

    image_paths = []
    for img in soup.find_all("img"):
        src = str(img.attrs.get("src", ""))
        if "http" in src or src.startswith("data:"):
            continue

        # Résoudre le chemin local de l'image
        img_local_path = urllib.parse.unquote(os.path.join(basepath, src))
        if os.path.exists(img_local_path):
            # Créer un CID unique basé sur le nom du fichier ou un UUID
            cid = email.utils.make_msgid(domain=_CID_INLINE_DOMAIN)[1:-1]
            img.attrs["src"] = f"cid:{cid}"
            image_paths.append((img_local_path, cid))

    return str(soup), image_paths


def get_subscriber_reader(param: Any) -> tuple[Any, Any]:
    """
    Returns a reader object and file handle for retrieving subscriber
    data based on the given parameter. The function retrieves the data
    either from a Google Sheets document or a local CSV file, depending
    on the configuration in the parameter. If the database file is not
    found, it logs the error and returns None, None.

    :param param: The configuration object containing details for data
                  retrieval (e.g., Google Sheets credentials or CSV/XLS
                  database path).
    :type param: object
    :return: A tuple consisting of a data reader object (either for
             Google Sheets or CSV) and a file handle. If the database
             is not found, it returns (None, None).
    :rtype: tuple(iterator | None, file | None)
    """
    if param.database is None:
        wb = open_google_db_members_sheet(sa=param.sa, sheet_id=param.sheetid)
        return iter(read_all_sheet(wb)), None

    try:
        if param.database.endswith(".csv"):
            csvfile = open(param.database, newline="", encoding="utf-8-sig")
            return csv.reader(csvfile, delimiter=",", quotechar='"'), csvfile
        else:
            from python_calamine import CalamineWorkbook

            workbook = CalamineWorkbook.from_path(param.database)
            return iter(workbook.get_sheet_by_index(0).to_python()), workbook

    except FileNotFoundError:
        log.critical(f"Fichier introuvable : '{param.database}'")
        return None, None


def get_indices(header: list[Any]) -> dict[str, int]:
    """
    Create a dictionary that maps each header element to its corresponding
    index in the list of headers.

    Args:
        header: List of header values (strings or other types from CSV/sheets).

    Returns:
        Dictionary where keys are string representations of header elements
        and values are their corresponding indices.
    """
    return {str(h): i for i, h in enumerate(header)}


def get_smtp_connection(param: Any) -> SMTP | None:
    """Open SMTP connection with TLS.

    Creates connection to SMTP server, upgrades to TLS, and authenticates
    with provided credentials.

    Args:
        param: Configuration object with smtp_host, smtp_port, username, password

    Returns:
        SMTP connection object, or None if connection failed

    Raises:
        SystemExit: On authentication failure (logs critical error)
    """

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        conn = SMTP(param.smtp_host, param.smtp_port)
        conn.starttls(context=context)
        conn.ehlo()
        conn.login(param.username, param.password)
        return conn
    except SMTPAuthenticationError:
        log.critical("Invalid SMTP credentials")
        sys.exit(-1)
    except (OSError, SMTPException) as e:
        log.error(f"Failed to connect to SMTP: {e}")
        return None


def get_gmail_service(param: Any) -> Any:
    """
    Fetches and returns the Gmail service object by authenticating through OAuth2. If valid credentials
    are not found locally, the function retrieves them via authorized secrets or user authentication
    interaction.

    :param param: An object containing the following attributes:
        - token_file: A path to the file holding the user's token information.
        - scopes: A list of OAuth2 scopes required by the Gmail API.
        - token_id: Identifier for fetching the token via secret management.
        - credentials_id: Identifier for fetching OAuth2 client credentials via secret management.
        - SCOPES: A list of OAuth2 scopes required for the authentication process.
    :type param: object
    :return: A Google API client service object for accessing the Gmail API.
    :rtype: googleapiclient.discovery.Resource
    """
    if os.path.exists(param.token_file):
        creds = cast(Credentials, Credentials.from_authorized_user_file(param.token_file, param.scopes))
    else:
        creds = None
    # else:
    #     token = get_secret(param.token_id)
    #     creds = Credentials.from_authorized_user_info(token, param.scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials = get_secret(param.credentials_id)
            flow = InstalledAppFlow.from_client_config(credentials, param.scopes)
            creds = flow.run_local_server(port=0)
        with open(param.token_file, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def save_to_sent(param: Any, msg: MIMEMultipart) -> None:
    """Store message in IMAP Sent folder.

    Saves sent email to Sent folder for archival. Retries up to 3 times
    on failure with 10-second delays.

    Args:
        param: Configuration object with imap_host, imap_port, username,
               password, sent_folder, verbose
        msg: Email message (MIMEMultipart) to store
    """
    n = 3
    for attempt in range(n):
        try:
            imap = imaplib.IMAP4_SSL(param.imap_host, param.imap_port)
            imap.login(param.username, param.password)
            imap.append(
                param.sent_folder,
                "\\Seen",
                imaplib.Time2Internaldate(time()),
                msg.as_string().encode("utf8"),
            )
            imap.logout()
            if param.verbose:
                log.info("stored in sent folder")
            return
        except (OSError, imaplib.IMAP4.error) as e:
            if attempt < n - 1:
                log.warning(f"Retrying IMAP storage: {e}")
                sleep(10)
            else:
                log.error(f"Error copying to sent folder: {e}")


def _decode_base64_image(src: str, temp_dir: str) -> str | None:
    """Decode a base64-encoded ``data:`` image src and save it to *temp_dir*.

    :return: The path of the saved temp file, or None on error.
    """
    try:
        header, encoded = src.split(",", 1)
        img_data = base64.b64decode(encoded)
        ext = header.split("image/")[1].split(";")[0] if "image/" in header else "png"
        temp_name = email.utils.make_msgid(domain=_CID_INLINE_DOMAIN)[1:-1]
        temp_path = os.path.join(temp_dir, f"embedded_{temp_name}.{ext}")
        with open(temp_path, "wb") as f:
            f.write(img_data)
        return temp_path
    except (ValueError, OSError) as e:
        log.error(f"Impossible de traiter l'image en base64 : {e}")
        return None


def _resize_and_save_image(img_path: str, cid: str, temp_dir: str, max_width: int) -> str | None:
    """Resize *img_path* to *max_width* and save as a JPEG in *temp_dir*.

    :return: Path of the optimised file, or None on error.
    """
    try:
        with Image.open(img_path) as im:
            if im.width > max_width:
                ratio = max_width / float(im.width)
                new_height = int(float(im.height) * float(ratio))
                im = im.resize((max_width, new_height), Image.Resampling.LANCZOS)  # type: ignore[assignment]
            opt_img_path = os.path.join(temp_dir, f"{cid}.jpg")
            im.convert("RGB").save(opt_img_path, "JPEG", quality=75, optimize=True)
        return opt_img_path
    except OSError as e:
        log.error(f"Impossible de traiter l'image {img_path}: {e}")
        return None


def prepare_html_and_get_images(in_filepath: str, max_width: int = 800) -> tuple[str, list[Any], str]:
    """
    Processes an HTML file to embed inline images and resize them for optimized usage.

    :param in_filepath: The path to the input HTML file.
    :type in_filepath: str
    :param max_width: The maximum allowable width for images. Images wider than this will be resized.
                      Defaults to 800.
    :type max_width: int, optional
    :return: A tuple containing the modified HTML content as a string, a list of inline image metadata
             dictionaries with optimized file paths and their corresponding CID references, and the path
             to the temporary directory used for storing the optimized images.
    :rtype: tuple[str, list[dict[str, str]], str]
    """
    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    with open(in_filepath, encoding="utf-8") as file:
        soup = BeautifulSoup(file, _HTML_PARSER)

    inline_images = []
    temp_dir = tempfile.mkdtemp()

    for img in soup.find_all("img"):
        src = str(img.attrs.get("src", ""))
        if not src or src.startswith("http"):
            continue

        if src.startswith("data:"):
            img_path = _decode_base64_image(src, temp_dir)
            if img_path is None:
                continue
        else:
            img_path = urllib.parse.unquote(os.path.join(basepath, src))

        if not os.path.exists(img_path):
            continue

        cid = email.utils.make_msgid(domain=_CID_INLINE_DOMAIN)[1:-1]
        opt_img_path = _resize_and_save_image(img_path, cid, temp_dir, max_width)
        if opt_img_path:
            img.attrs["src"] = f"cid:{cid}"
            inline_images.append({"path": opt_img_path, "cid": cid})

    return str(soup), inline_images, temp_dir


def format_message(template: str, row: list[Any], header: list[str]) -> str:
    """Format message by replacing ${field} placeholders with row values.

    Substitutes template placeholders with subscriber data. Placeholders use
    syntax ${column_name} which maps to header column names.

    Args:
        template: Template string with ${field_name} placeholders
        row: List of subscriber values (one per column)
        header: List of column/field names (indices match row)

    Returns:
        Formatted message with values substituted, or original template on error
    """
    try:
        def _replace(m: re.Match[str]) -> str:
            key = m.group(1)
            return str(row[header.index(key)])

        return re.sub(r"\${(.*?)}", _replace, template)
    except (ValueError, IndexError):
        return template


def process_attachments(args: Any, config: dict[str, Any], folder: str = "input") -> tuple[list[str], Any, list[Any]]:
    """
    Processes attachments by either verifying file paths provided in the arguments or downloading files
    from a Google Drive folder and cleaning up the local folder. Returns processed file paths, the Google
    Drive service connection, and metadata about the downloaded files.

    :param args: Command-line arguments containing file paths or other configurations.
    :type args: Namespace
    :param config: Configuration dictionary containing keys like 'SA' for service account and
        'mailing_folder' for desired Google Drive folder ID.
    :type config: dict
    :param folder: Optional path to the local folder used for downloading files. Defaults to "input".
    :type folder: str
    :return: A tuple containing the list of processed file paths, the Google Drive service connection
        object (or None if unused), and metadata about files fetched from Google Drive.
    :rtype: tuple[list[str], Union[Resource, None], list[dict]]
    """
    service, google_drive_files, files = None, [], []
    if args.file:
        for f in args.file:
            if not os.path.isfile(f):
                log.critical(f"File not found: {f}")
                sys.exit(-1)
        files = args.file
    elif "SA" in config and "mailing_folder" in config:
        # Nettoyage et téléchargement depuis Google Drive
        for f in glob(f"{folder}/*.*"):
            os.remove(f)
        service = gd.connect_google_driver(config["SA"])
        if "mailing_folder" not in config:
            return [], service, []
        result = gd.get_files(service, folder_id=config["mailing_folder"])
        if result and "files" in result:
            google_drive_files = result["files"]
            gd.download_file(service, google_drive_files, folder)
        files = [f for f in glob(f"{folder}/*.*") if "published" not in f]

    return files, service, google_drive_files


def md2html(file_path: str, styles: str | None = None, embed_styles: bool = False) -> str | None:
    """
    Converts a Markdown file to an HTML file with optional styling.

    The function reads a Markdown file, converts its content to an HTML
    document using the `Markdown` library, and writes the resulting HTML
    to a new file. Default and optional CSS styles can be embedded in or
    linked from the resulting HTML document.

    :param file_path: The file path of the Markdown file to be converted.
    :type file_path: str
    :param styles: Optional path to a CSS file for custom styling.
                   Defaults to None.
    :type styles: str, optional
    :param embed_styles: Specifies whether to embed styles directly into
                         the HTML. If True and a valid `styles` path is
                         provided, the CSS content will be embedded as
                         inline styles. Defaults to False.
    :type embed_styles: bool
    :return: The file path of the created HTML file, or None if the process
             fails (e.g., if the Markdown file does not exist).
    :rtype: str or None
    """
    default_styles = """
        body {background-color: PapayaWhip;}
        h1  {color: red; text-align: center}
        h2  {color: darkred; padding-left: 20px;}
        h3, h4, h5  { padding-left: 20px;}
        h6  {color: skyblue;}
        p, b {color: DarkSlateGray;padding-left: 50px;}
        ul  {color: DarkSlateGray;padding-left: 80px;}
        li  {
            color: DarkSlateGray;
            padding-left: 10px;
            }
        img {
            max-width: 1000px;
            height: auto;   display: block;
            margin-left: auto;
            margin-right: auto;
        }
    """

    if not os.path.exists(file_path):
        log.error(f"Le fichier Markdown {file_path} n'existe pas.")
        return None
    else:
        with open(file_path) as f:
            data = f.read()

    converter = md.Markdown(extras=["tables", "header-ids", "cuddled-lists"])
    csp = f"default-src 'self' data:; img-src 'self' {_CSP_IMG_DOMAIN} data:;"

    if styles is None:
        head = f"""
    <!-- Add locale and title header -->
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Security-Policy" content="{csp}">
        <style>{default_styles}</style>
    </head>

"""
    elif embed_styles and os.path.exists(styles):
        with open(styles) as f:
            default_styles = f.read()
            head = f"""
                <!-- Add locale and title header -->
                <head>
                    <meta charset="UTF-8">
                    <meta http-equiv="Content-Security-Policy"
                          content="{csp}">
                    <style>{default_styles}</style>
                </head>

            """
    else:
        head = f"""
   <!-- Add locale and title header -->
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Security-Policy" content="{csp}">
        <link rel="stylesheet" href="{styles}">
    </head>
"""

    html = "<html>\n" + head + converter.convert(data) + "\n</html>"
    file_path = file_path.split(".")[0] + ".html"
    with open(file_path, "w") as f:
        f.write(html)
    return file_path


def _set_email_headers(
    msg: MIMEMultipart,
    param: Any,
    subject: str,
    to: str,
    cc: str,
    bcc: str | None,
) -> tuple[str | None, str | None]:
    """Populate standard headers on *msg* and return the (possibly swapped) to/bcc pair."""
    msg["Subject"] = subject
    msg["From"] = formataddr((param.sendername, param.sender))
    unsubscribe_mail = f"mailto:{param.sender}?subject=unsubscribe"
    msg["List-Unsubscribe"] = f"<{unsubscribe_mail}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    if param.max_addr_per_mail == 1:
        to = bcc  # type: ignore
        bcc = None
        msg["To"] = to
    else:
        msg["To"] = f"{to},{formataddr((param.sendername, param.sender))}"
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Date"] = email.utils.formatdate(localtime=True)
    if hasattr(param, "domain"):
        msg["Message-ID"] = email.utils.make_msgid(idstring=str(uuid4()), domain=param.domain)
    return to, bcc


def _process_html_attachment(att: str, param: Any, all_inline_images: list[Any], temp_dirs: list[str]) -> str:
    """Convert Markdown to HTML if needed, then extract inline images. Returns the HTML body."""
    is_md = att.endswith("md")
    if is_md:
        result = md2html(att, styles=param.styles if hasattr(param, "styles") else None, embed_styles=True)
        if result is None:
            return ""
        att = result
    html_content, found_images, t_dir = prepare_html_and_get_images(att)
    all_inline_images.extend(found_images)
    temp_dirs.append(t_dir)
    if is_md and not hasattr(param, "keep-html"):
        os.remove(att)  # pyright: ignore
    return html_content


def _process_binary_attachment(att: str, msg: MIMEMultipart) -> None:
    """Attach a PDF or TXT file directly to *msg*."""
    with open(att, "rb") as f:
        content = f.read()
    if att.endswith("pdf"):
        part = MIMEApplication(content, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=os.path.basename(att))
        msg.attach(part)
    elif att.endswith("txt"):
        msg.attach(MIMEText(content.decode()))


def _attach_body(msg: MIMEMultipart, msg_related: MIMEMultipart, message: str, all_inline_images: list[Any]) -> None:
    """Attach the message body and any inline images to *msg*."""
    if not message:
        return
    if "<html" in message:
        msg_related.attach(MIMEText(message, "html"))
        for img_info in all_inline_images:
            try:
                with open(img_info["path"], "rb") as f:
                    img_part = MIMEImage(f.read())
                img_part.add_header("Content-ID", f"<{img_info['cid']}>")
                img_part.add_header("Content-Disposition", "inline", filename=os.path.basename(img_info["path"]))
                msg_related.attach(img_part)
            except (OSError, TypeError) as e:
                log.error(f"Error attaching inline image {img_info['path']}: {e}")
        msg.attach(msg_related)
    else:
        msg.attach(MIMEText(message, "plain"))


def build_email(
        param: Any,
        subject: str = "",
        to: str = "",
        cc: str = "",
        bcc: str | None = None,
        message: str = "",
        images: str | list[str] | None = None,
        attachments: str | list[str] | None = None
) -> tuple[MIMEMultipart, list[str]]:
    """Build MIME email message with attachments and inline images.

    Constructs multipart email with headers, body, inline images, and
    attachments. Supports HTML/text bodies, inline CID images, and file
    attachments.

    Args:
        param: Configuration object with sender details
        subject: Email subject line
        to: Comma-separated To addresses
        cc: Comma-separated CC addresses
        bcc: Comma-separated BCC addresses
        message: HTML or text email body
        images: File path(s) of inline images (str or list)
        attachments: File path(s) of attachments (str or list)

    Returns:
        Tuple of (MIME message object, list of recipient addresses)
    """
    msg = MIMEMultipart("mixed")
    to, bcc = _set_email_headers(msg, param, subject, to, cc, bcc)  # type: ignore

    msg_related = MIMEMultipart("related")
    all_inline_images: list[dict[str, str]] = []
    temp_dirs: list[str] = []

    for img_path in [images] if isinstance(images, str) else (images or []):
        if os.path.exists(img_path):
            cid = email.utils.make_msgid(domain=_CID_INLINE_DOMAIN)[1:-1]
            all_inline_images.append({"path": img_path, "cid": cid})

    for att in [attachments] if isinstance(attachments, str) else (attachments or []):
        if att.endswith(("htm", "html", "md")):
            message = _process_html_attachment(att, param, all_inline_images, temp_dirs)
        else:
            _process_binary_attachment(att, msg)

    _attach_body(msg, msg_related, message, all_inline_images)

    recipients = [r.strip() for r in f"{to},{cc},{bcc}".split(",") if r.strip()]
    msg._temp_dirs = temp_dirs  # type: ignore

    return msg, recipients


def _build_and_send(param: Any, addressees: list[Any], row: list[Any], header: list[str]) -> bool:
    """Build one email batch and dispatch it via SMTP or Gmail, then clean up temp dirs.

    :return: True if the message was sent, False if sending was skipped or failed.
    :rtype: bool
    """
    msg_body = format_message(param.message, row, header)
    if param.donotsend:
        log.info("do not sent activated")
        return False
    # Combine HTML file + user-selected attachments (T016: Integrate attachments)
    # param.file is already a list (from editor.py line 1332)
    all_attachments: list[str] = list(param.file) if param.file else []
    if hasattr(param, "attachment") and param.attachment:
        if isinstance(param.attachment, list):
            all_attachments.extend(param.attachment)
        else:
            all_attachments.append(param.attachment)
    msg, recipients = build_email(
        param=param,
        subject=param.subject,
        message=msg_body,
        bcc=",".join(addressees),
        attachments=all_attachments if all_attachments else None,
    )
    try:
        if hasattr(param, "smtp_host"):
            result = send_mail(param=param, message=msg, recipients=recipients)
            return bool(result)
        else:
            return send_gmail(get_gmail_service(param), message=msg) is not None
    finally:
        for d in getattr(msg, "_temp_dirs", []):
            try:
                shutil.rmtree(d)
                if param.verbose:
                    log.info(f"Dossier temporaire supprimé : {d}")
            except OSError as e:
                log.error(f"Erreur lors du nettoyage de {d}: {e}")


def _skip_to_index(reader: Any, from_index: int) -> int:
    """Advance *reader* past records before *from_index* and return the updated row index."""
    log.debug(f"Reprise à l'index {from_index}")
    idx = 1
    for _ in range(2, from_index):
        next(reader, None)
        idx += 1
    return idx


def _flush_batch(param: Any, addressees: list[Any], row: list[Any], header: list[str], pause: int, recipient_count: int, max_mail_per_hour: int) -> None:
    """Dispatch the current addressee batch and enforce rate limiting."""
    _build_and_send(param, addressees, row, header)
    sleep(pause)
    if recipient_count % max_mail_per_hour == 0:
        log.info("Limite horaire atteinte. Pause d'une heure...")
        sleep(3600)


def generate_mailing(param: Any) -> str:
    """
    Generates and sends emails to a list of subscribers based on provided parameters and subscriber information.

    This function reads a list of recipients from a CSV file and sends them emails in batched groups. The
    function supports various profiles for filtering recipients, skipping initial records, and processing
    up to a certain index. It respects constraints like maximum recipients per email, maximum emails
    sent per hour, and pauses between batches. The email messages can include custom formatting, attachments,
    and can be sent using different email delivery methods based on the profile.

    If an error occurs during execution, the function logs the error and attempts to finish gracefully.

    :param param: An object containing configuration attributes required to generate, filter, and send emails.
                  The attributes include limits, filters, email parameters, and operational flags.
    :type param: Any
    :return: A string "OK" if email generation and sending complete successfully, or "Error" if an error occurs.
    :rtype: str
    """
    try:
        max_add = param.max_addr_per_mail
        pause = param.pause
        max_mail_per_hour = param.max_mails_per_hour
    except AttributeError as e:
        log.critical(f"Clé de configuration manquante : {e}")
        return "Config Key Error"

    reader, file_object = get_subscriber_reader(param)
    if not reader:
        return "Reader Error"

    try:
        header = next(reader, None)
        if not header:
            return "Header Error"
        indices = get_indices(header)

        current_row_idx = 1
        if param.from_index:
            current_row_idx = _skip_to_index(reader, int(param.from_index))

        addressees, recipient_count, mail_batch_count = [], 0, 0
        start_time = time()
        row = None

        for row in reader:
            current_row_idx += 1
            if param.to_index and current_row_idx > int(param.to_index):
                break
            if filter(param.filter, row, indices):
                continue

            addressees.append(row[indices["email"]])
            recipient_count += 1
            if len(addressees) >= max_add:
                log.info(f"Envoi à {len(addressees)} destinataires (Index: {current_row_idx})")
                _flush_batch(param, addressees, row, header, pause, recipient_count, max_mail_per_hour)
                addressees, mail_batch_count = [], mail_batch_count + 1

        if addressees:
            log.info(f"Envoi final à {len(addressees)} destinataires.")
            _build_and_send(param, addressees, row, header)  # type: ignore
            mail_batch_count += 1

        log.info(
            f"Terminé. {recipient_count} adresses traitées en {mail_batch_count} envois ({int(time() - start_time)}s)"
        )
        return "OK"
    finally:
        if file_object:
            file_object.close()


_FILTER_OPS = [
    # Longer operators first to avoid substring matches
    # E.g., "is equal to" before "is", "is not equal to" before "is not"
    "does not contain",
    "does not match",
    "does not",
    "is not empty",
    _OP_IS_NOT_EQUAL_TO,  # "is not equal to"
    "is not",
    "greater or equal to",
    "less or equal to",
    _OP_IS_EQUAL_TO,  # "is equal to"
    "greater than",
    "less than",
    "is empty",
    _OP_IS_NOT_EMPTY,  # "is not empty"
    "starts with",
    "ends with",
    "matches",
    "one of",
    "none of",
    "not in",
    "is",
    "in",
    "gt",
    "lt",
    "ge",
    "le",
    "eq",
    "ne",
    "contains",
]


def _parse_filter_expr(v: str, _k: str) -> tuple[str, Any]:
    """Parse operator and test value from a filter expression string.

    Raises ValueError when the operator is unrecognised.
    """
    if not v or not isinstance(v, str):
        raise ValueError("Filter value is empty or invalid")

    op = _FILTER_OPS[[v.find(x + " ") for x in _FILTER_OPS].index(0)]

    test_value: Any = v.split(op)[1].strip()
    if "not " in test_value:
        op += " not"
        test_value = test_value.split("not")[1].strip()
    if "empty" in test_value:
        op += " empty"
        test_value = None
    elif test_value and "," in test_value:
        test_value = test_value.replace(" ", "").split(",")
    return op, test_value


def _eval_numeric(fv: float, tv_raw: Any, op: str, _k: str) -> bool:
    """Evaluate a numeric comparison between *fv* and *tv_raw* using *op*."""
    try:
        tv = float(tv_raw)
    except (ValueError, TypeError):
        return False

    operators: dict[str, Any] = {
        "ge": lambda a, b: a >= b,
        "greater or equal to": lambda a, b: a >= b,
        _OP_GREATER_THAN_OR_EQUAL: lambda a, b: a >= b,
        "gt": lambda a, b: a > b,
        "greater than": lambda a, b: a > b,
        _OP_GREATER_THAN: lambda a, b: a > b,
        "le": lambda a, b: a <= b,
        "less or equal to": lambda a, b: a <= b,
        _OP_LESS_THAN_OR_EQUAL: lambda a, b: a <= b,
        "lt": lambda a, b: a < b,
        "less than": lambda a, b: a < b,
        _OP_LESS_THAN: lambda a, b: a < b,
        "eq": lambda a, b: a == b,
        _OP_IS_EQUAL_TO: lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        _OP_IS_NOT_EQUAL_TO: lambda a, b: a != b,
    }
    result: bool = operators.get(op, lambda a, b: True)(fv, tv)  # noqa: ARG005
    return result


def _eval_regex(test_value: Any, field_value: str, negate: bool = False) -> bool:
    """Evaluate regex match. Returns False on error, respecting negate flag."""
    if not test_value:
        return True if negate else False
    try:
        match = bool(re.search(test_value, field_value))
        return (not match) if negate else match
    except re.error:
        return True if negate else False


def _eval_string(field_value: str, test_value: Any, op: str) -> bool:
    """Evaluate a string/membership comparison."""
    return _do_string_eval(field_value, test_value, op)


def _do_string_eval(field_value: str, test_value: Any, op: str) -> bool:
    """Helper to evaluate string operations."""
    if op in ("in", "one of", _OP_ONE_OF):
        return bool(field_value in test_value)
    if op in ("not in", "none of", _OP_NOT_ONE_OF):
        return bool(field_value not in test_value)
    if op in ("is", _OP_IS_EQUAL_TO, _OP_IS):
        return bool(field_value == test_value)
    if op in ("is not", _OP_IS_NOT_EQUAL_TO, _OP_IS_NOT):
        return bool(field_value != test_value)
    if op in (_OP_IS_NOT_EMPTY, "is not empty"):
        return field_value != "" and field_value is not None
    if op in ("is empty", ):
        return field_value == "" or field_value is None
    if op in ("contains", _OP_CONTAINS):
        return bool(test_value in field_value) if test_value else False
    if op in ("does not contain", _OP_DOES_NOT_CONTAIN):
        return bool(test_value not in field_value) if test_value else True
    if op in ("starts with", _OP_STARTS_WITH):
        return bool(field_value.startswith(test_value)) if test_value else False
    if op in ("ends with", _OP_ENDS_WITH):
        return bool(field_value.endswith(test_value)) if test_value else False
    if op in ("matches", _OP_MATCHES):
        return _eval_regex(test_value, field_value, negate=False)
    if op in ("does not match", _OP_DOES_NOT_MATCH):
        return _eval_regex(test_value, field_value, negate=True)
    return True


def _evaluate_condition(field_value: str, op: str, test_value: Any, _k: str) -> bool:
    """Return True when *field_value* satisfies *op* against *test_value*."""
    try:
        return _eval_numeric(float(field_value), test_value, op, _k)
    except ValueError:
        return _eval_string(field_value, test_value, op)


def filter(filter: dict[str, str], row: list[Any], indices: dict[str, int]) -> bool:  # noqa: A001,A002
    """Filter row: return True if should be EXCLUDED, False if INCLUDED.

    Applies filter conditions to subscriber row. All filter conditions must
    match for row to be included (AND logic).

    Supported operations: is, is not, gt, lt, ge, le, in, not in,
    is empty, is not empty, contains, does not contain, starts with, ends with,
    matches, does not match, and their aliases (e.g., "greater than", "one of").

    Args:
        filter: Dict of {field_name: "operator value"} (e.g., {"status": "is active"})
        row: List of subscriber field values
        indices: Dict mapping field names to column indices

    Returns:
        True if row should be filtered OUT (excluded), False if INCLUDED
    """
    if not filter:
        return False

    result = True
    for k, v in filter.items():
        field_value = row[indices[k]] if k in indices and indices[k] < len(row) else None
        if field_value is None:
            return True
        try:
            op, test_value = _parse_filter_expr(v, k)
        except ValueError:
            return True
        res = _evaluate_condition(field_value, op, test_value, k)
        if not res:
            return True
        result = result and res

    return not result


def send_gmail(service: Any, message: Any = None) -> Any:
    """
    Sends an email message using the Gmail API.

    This function encodes the message in Base64 and uses the provided Gmail service
    to send the email. It handles errors and logs any failures.

    :param service: An authorized Gmail API service instance.
    :type service: googleapiclient.discovery.Resource
    :param message: The email message as a MIME object.
    :type message: MIMEMultipart or MIMEText
    :return: The sent message resource if successful, None otherwise.
    :rtype: dict or None
    """
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    body = {"raw": encoded_message}
    try:
        return service.users().messages().send(userId="me", body=body).execute()
    except errors.HttpError as error:
        log.error(f"Error sending message: {error} to {message['To']}")
        return None


def send_mail(param: Any = None, message: Any = None, recipients: Any = None) -> bool:
    """
    Send an email message to specified recipients using SMTP.

    This function attempts to send an email message to the specified list of
    recipients using an SMTP connection. It retries sending the email up to two
    times in case of a failure. Logging and other functionalities depend on the
    settings provided in the `param` object. The email is saved to the sent records
    if it is successfully sent.

    Args:
        param: Configuration object that determines the behavior of the email-sending process
        message: The email message to be sent with "From" field populated
        recipients: List of recipient email addresses

    Returns:
        Boolean indicating whether the email was successfully sent
    """
    if param.verbose:  # pyright: ignore
        log.info(f"Sending email to {recipients}")
    success = False
    for attempt in range(2):
        conn = get_smtp_connection(param)
        if conn:
            try:
                conn.sendmail(message["From"], recipients, message.as_string())  # pyright: ignore
                conn.quit()
                success = True
                if param.verbose:  # pyright: ignore
                    log.info("sent")
                break
            except SMTPException as e:
                log.error(f"SMTP error on attempt {attempt + 1}: {e}")
                if attempt == 0:
                    sleep(10)

    if success and message:
        save_to_sent(param, message)
    return success


def get_newsletter_name(files: list[str], args: Any) -> Any:
    """
    Parses given files and updates newsletter-related attributes in the provided arguments.

    The function analyses filenames and their extensions to infer newsletter-related details such as
    subject, newsletter name, and message body. It modifies the attributes of the provided `args`
    object accordingly.

    :param files: List of file paths to analyze
    :type files: list[str]
    :param args: Arguments object that holds properties like `subject`, `newsletter_name`, and `message`
    :type args: Any
    :return: Updated arguments object with inferred newsletter details
    :rtype: Any
    """
    # Analyse des fichiers pour le sujet et le corps
    for f in files:
        basename = os.path.basename(f)
        ext = basename.split(".")[-1].lower()
        name_part = basename.split(".")[0]

        if ext in ["pdf", "html", "md"]:
            if not args.subject:
                args.subject = name_part
            if "letter" in name_part.lower() or "lettre" in name_part.lower():
                args.newsletter_name = basename
            if ext == "html":
                args.message = "html"
        elif "body.txt" in basename:
            body_txt = open(f, encoding="utf-8").read()
            args.message = body_txt
            files.remove(f)
    return args


def _load_config_with_secrets(args: Any) -> dict[str, Any]:
    """Merge the profile config with any vault secrets and CLI overrides."""
    config = args.conf[args.profile]

    # Try Profile class for vault_key, fall back to legacy MAILCONFIG
    try:
        vault_key = config.get("vault_key") or config.get("MAILCONFIG") or config.get("mailconfig")
        if vault_key:
            profile = Profile(args.profile, config)
            secret = profile.load_smtp_from_vault()
        else:
            # No vault key configured, use legacy behavior
            secret = None
    except ProfileLoadError as e:
        log.error(f"Failed to load profile '{args.profile}': {str(e)}")
        raise
    except Exception as e:  # noqa: BLE001 — get_secret may raise any exception
        log.debug(f"No secret configuration found, using config file only: {e}")
        secret = None

    if secret is None:
        # Try legacy get_secret approach for backward compatibility
        try:
            secret = get_secret(config.get("MAILCONFIG", ""))
            if secret is None:
                log.warning("No secret configuration found")
                secret = {}
        except Exception as e:  # noqa: BLE001
            log.debug(f"No secret configuration found, using config file only: {e}")
            secret = {}

    config = {**secret, **config}
    for k, v in vars(args).items():
        if v is not None or k not in config:
            config.update({k: v})
    return config


def _prepare_message_body(param: Any, config: dict[str, Any], files: list[str]) -> Any:
    """Populate param.message from the default template when not already set."""
    body_txt = param.body if param.body else ""
    param.newsletter_name = ""
    param = get_newsletter_name(files, param)
    if not param.message:
        param.message = config["default_message"]
        param.message = param.message.replace("${newsletter_name}", param.newsletter_name)
        param.message = param.message.replace("${body}", body_txt)
    return param


def _post_send_cleanup(service: Any, google_drive_files: list[Any]) -> None:
    """Mark processed Google Drive files as published and clear the local input folder."""
    for f in google_drive_files:
        gd.rename_file(service, f["id"], f"published_{f['name']}")
    for f in glob("input/*.*"):
        os.remove(f)


def process_profile(args: Any) -> str:
    """
    Processes the user profile to configure and send a mailing task with attachments. The function
    integrates configurations, manages secrets, processes attachments, and dynamically generates
    and sends the mailing.

    :param args: The argparse.Namespace object containing the configurations and command-line
        arguments required for the mailing process.
    :return: A string indicating the success or failure of the process. Returns "OK" if the
        mailing was successfully sent in normal mode, "OK_TEST" if it was successfully sent
        in test mode, and "Error" otherwise.
    """
    config = _load_config_with_secrets(args)
    param = Dict2Class(config)

    if not check_mandatory_param(param):
        return "Error"

    files, service, google_drive_files = process_attachments(param, config)
    param.file = files
    param = _prepare_message_body(param, config, files)

    if not param.subject:
        log.error("No subject given - use -s 'some subject' argument")
        return "Error"

    if "password" not in config and hasattr(param, "smtp_host"):
        config["password"] = getpass("Enter mail user's password")

    if param.test:
        param.filter = param.filter_test

    # T036, T037: Use session-active filter if provided (from editor dialog)
    if hasattr(args, "session_filter") and isinstance(args.session_filter, dict):
        param.filter = args.session_filter

    if generate_mailing(param) == "OK":
        if param.test:
            log.info("Test mode: mailing sent successfully.")
            return "OK_TEST"
        _post_send_cleanup(service, google_drive_files)
        return "OK"
    return "Error"


def _check_common_params(param: Any) -> bool:
    """Return False and log errors for any missing common mandatory parameters."""
    ret = True
    for p in ("sender", "sendername"):
        if not hasattr(param, p) or getattr(param, p) is None:
            log.error(f"{p.replace('_', ' ').capitalize()} is mandatory")
            ret = False
    return ret


def _check_data_source(param: Any) -> bool:
    """Return False if neither a database path nor a (SA + sheetid) pair is configured."""
    if not hasattr(param, "database") and not (
            hasattr(param, "sa") and hasattr(param, "sheetid")
    ):
        log.error("Database path or (Service Account (SA) and SheetID) is mandatory")
        return False
    return True


def _check_smtp_imap_params(param: Any) -> bool:
    """Return False and log errors for missing SMTP/IMAP mandatory parameters."""
    required = ["smtp_port", "imap_host", "imap_port", "username", "password", "sent_folder"]
    ret = True
    for p in required:
        if not hasattr(param, p) or getattr(param, p) is None:
            log.error(f"{p.replace('_', ' ').upper()} is mandatory for SMTP/IMAP mode")
            ret = False
    return ret


def _check_gmail_params(param: Any) -> bool:
    """Return False and log errors for missing Gmail mandatory parameters."""
    ret = True
    for p in ("token_file", "scopes", "credentials_id"):
        if not hasattr(param, p) or getattr(param, p) is None:
            log.error(f"{p.replace('_', ' ').capitalize()} is mandatory for Gmail mode")
            ret = False
    return ret


def check_mandatory_param(param: Any) -> bool:
    """
    Validates that all mandatory parameters are present and correctly configured.

    This function ensures that required parameters for mailing operations are
    set and valid before proceeding with the mailing process. It checks for:

    - **Common Parameters**: subject, sender, sendername, message.
    - **Data Source**: either a CSV database path or (Google Service Account and Sheet ID).
    - **Mailing Method**:
        - *SMTP/IMAP mode*: smtp_host, smtp_port, imap_host, imap_port, username, password, sent_folder.
        - *Gmail mode*: token_file, scopes, credentials_id.

    :param param: An object containing configuration parameters.
    :type param: Dict2Class
    :return: True if all mandatory parameters are present, False otherwise.
    :rtype: bool
    """
    common_ok = _check_common_params(param)
    data_ok = _check_data_source(param)
    method_ok = _check_smtp_imap_params(param) if hasattr(param, "smtp_host") else _check_gmail_params(param)
    ret = common_ok and data_ok and method_ok

    if not ret:
        log.critical("Please check and update your configuration file")

    return ret


def setup_argparse() -> argparse.Namespace:
    """
    Sets up and parses command-line arguments for a mailing utility.

    This function configures an argument parser with various command-line options
    to customize email sending behavior. The options include mail subject, body,
    attachments, database indices, test mode, verbosity, and other configurations
    for controlling email sending and processing.

    :return: Parsed arguments from the command line
    :rtype: argparse.Namespace

    Options:
        - -cfg, --config: Path to the configuration file (default: User Home folder).
        - -s, --subject: Subject of the mail (default: None).
        - -m, --message: Text message of the mail (default: an empty string).
        - file: A list of files to attach to the mail (default: []).
        - -t, --test: Test mode flag; sends only to a tester group (default: False).
        - -v, --verbose: Flag to increase output verbosity (default: False).
        - -x, --doNotSend: Flag to disable mail sending (default: False).
        - -db, --database: Database path (default: None).
        - -f, --from_index: Starting index in the database (default: None).
        - -to, --to_index: Stopping index in the database (default: None).
        - -w, --wait: Waiting time in minutes before restarting mail sending
          (default: None).
        - --selected: Flag to send only selected mail (default: False).
        - --body: Specifies the email body (default: None).
        - -mh, --max-mails-per-hour: Maximum emails to send per hour (default:
          1000).
        - -na, --max_addr_per_mail: Maximum number of addresses per mail (default:
          50).
        - -p, --pause: Pause duration in seconds between operations (default: 3).
        - --md2html: Flag to convert input Markdown file to embedded HTML (default: False).
        - --keep-html: Flag to keep the generated HTML file (default: False).
        - --profile: Specifies the mail profile to use (default: None).
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-cfg", "--config", help="path to the config file", default=None
    )
    parser.add_argument("-s", "--subject", help="Subject of the mail")
    parser.add_argument("-m", "--message", help="Text message of the mail", default="")
    parser.add_argument("file", nargs="*", help="files to attach to the mail")
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="test mode - send only to the tester group",
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "-x", "--doNotSend", action="store_true", help="Do not send any mail"
    )
    parser.add_argument("-db", "--database", help="database path")
    parser.add_argument(
        "-f", "--from_index", help="Starting index in the database", default=None
    )
    parser.add_argument(
        "-to", "--to_index", help="Stopping index in the database", default=None
    )
    parser.add_argument(
        "-w", "--wait", help="Wait x minutes before restarting sending mail", type=int
    )
    parser.add_argument(
        "--selected", action="store_true", help="Only send selected mail", default=False
    )
    parser.add_argument("--body")
    parser.add_argument("-mh", "--max-mails-per-hour", default=1000, type=int)
    parser.add_argument("-na", "--max_addr_per_mail", default=50, type=int)
    parser.add_argument("-p", "--pause", default=3, type=int)
    parser.add_argument("--profile", help="mail profile", default="default")
    parser.add_argument(
        "--md2html", action="store_true", help="convert md file to html & exit"
    )
    parser.add_argument(
        "--keep-html", action="store_true", help="keep the generated html file"
    )
    return parser.parse_args()


def main() -> int:
    """
    Changes the current working directory to the directory of the executing file, parses
    command-line arguments, and loads configuration settings from a YAML file. Based on
    the specified profile in the arguments, it processes the respective profile logic.

    :return: None
    """
    if hasattr(sys, "frozen"):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(__file__)

    os.chdir(os.path.abspath(application_path))
    args = setup_argparse()
    args.conf = None
    if args.config:
        with open(args.config) as config_file:
            args.conf = yaml.safe_load(config_file)
    else:
        log.debug(get_default_config_path())
        with open(get_default_config_path()) as config_file:
            args.conf = yaml.safe_load(config_file)
    if args.conf is None:
        log.critical("No configuration file found")
        return -1

    if args.md2html and args.file[0].endswith(".md"):
        md2html(args.file[0], "../css/styles.css")
        file = args.file[0].replace(".md", ".html")
        make_html_images_inline(file, file)
        return -1

    if args.profile:
        return 0 if process_profile(args) in ("OK", "OK_TEST") else -1
    else:
        log.critical("No profile specified")
        return -1


if __name__ == "__main__":
    sys.exit(main())
