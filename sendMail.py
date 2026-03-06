#!/usr/bin/env python
# coding: utf-8
"""
Utilities to handle logging, Google Sheets, file manipulation, and API interactions.

This module provides functions and classes for initializing logging, working with Google Sheets,
manipulating files (e.g., determining MIME types or encoding files in Base64), and API interactions
such as those for invoicing with a third-party service. It also includes utilities for processing
HTML content and converting data structures.

"""


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
from smtplib import SMTP, SMTPAuthenticationError, SMTPException
from time import time, sleep
from uuid import uuid4

import gspread
import markdown2 as md
import requests
import yaml
from PIL import Image
from bs4 import BeautifulSoup
from getSecrets import get_secret
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import errors
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import googleDriveLib as gd

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


def init_log(log_file=None):
    """
    Initializes and configures a logger for logging messages. The logger writes
    messages to the console and optionally to a log file, using a predefined
    format for log messages. This function sets the logger's default level to
    INFO and the file handler's level to DEBUG if a file logger is enabled.

    :param log_file: Path to the file where log messages will be stored. If None,
        no file logging is enabled. Optional.
    :type log_file: str, optional
    :return: Configured logger instance.
    :rtype: logging.Logger
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


log = init_log(log_file="sendMail.log")


# for artscroises profile
def openGoogleDBMembersSheet(sa, id):
    """
    Open  a Google Sheet and return it as a spreadsheet object
    :param sa: Service Account entry name in secret vault
    :param id: Google Sheet ID entry name in secret vault
    :return: a workbook spreadsheet object
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(get_secret(sa), scope)
    gc = gspread.authorize(creds)

    spreadsheet_id = get_secret(id)["ID"]
    wb = gc.open_by_key(spreadsheet_id)
    return wb


def readAllSheet(wb, sheet_name: str = ""):
    """
    Read all ranges of a sheet
    :param wb: workbook object
    :param sheet_name: sheet name - default=sheet1
    :return: range of value (array of arrays)
    """
    ws = wb.sheet1 if not sheet_name else wb.worksheet(sheet_name)
    return ws.get_all_values()


class Dict2Class:
    """
    Convert a dict to a class
    """

    def __init__(self, my_dict):
        for key in my_dict:
            setattr(self, key.lower(), my_dict[key])


def guess_type(filepath):
    """
    Return the mimetype of a file, given its path.
    This is a wrapper around two alternative methods - Unix 'file'-style
    magic which guesses the type based on file content (if available),
    and simple guessing based on the file extension (eg .jpg).
    :param filepath: Path to the file.
    :type filepath: str
    :return: Mimetype string.
    :rtype: str
    """
    try:
        import magic  # python-magic
        return magic.from_file(filepath, mime=True)
    except ImportError:
        import mimetypes
        return mimetypes.guess_type(filepath)[0]


def file_to_base64(filepath):
    """
    Returns the content of a file as a Base64 encoded string.
    :param filepath: Path to the file.
    :type filepath: str
    :return: The file content, Base64 encoded.
    :rtype: str
    """
    import base64

    encoded_str = ""
    if 'http' in filepath:
        img = requests.get(filepath)
        if img.status_code != 200:
            return ''
        encoded_str = base64.b64encode(img.content)
    else:
        with open(filepath, "rb") as f:
            encoded_str = base64.b64encode(f.read())
    return encoded_str.decode("utf-8")


def make_html_images_inline(in_filepath, out_filepath=None) -> str:
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
    with open(in_filepath, "r") as file:
        soup = BeautifulSoup(file, "html.parser")
    for img in soup.find_all("img"):
        if 'http' in img.attrs["src"]:
            img_path = urllib.parse.unquote(img.attrs["src"])
        else:
            img_path = urllib.parse.unquote(os.path.join(basepath, img.attrs["src"]))
        mimetype = guess_type(img_path)
        if ";base64," not in img_path:
            img.attrs["src"] = f"data:{mimetype};base64,{file_to_base64(img_path)}"

        else:
            # TODO Change by a regex to ensure the string start with data:.*?;base64...
            img.attrs["src"] = img_path[6:]

    if out_filepath:
        with open(out_filepath, "w") as of:
            of.write(str(soup))
    return str(soup)


def prepare_html_for_cid(in_filepath):
    """
    Prepare HTML content for embedding inline images as Content-ID (CID) references.

    This function processes an HTML file, reads its content, identifies the <img>
    tags, and replaces their `src` attributes with Content-ID (CID) references,
    allowing the images to be embedded inline in emails. It handles local image
    paths and excludes external or base64-encoded images. A mapping of the local
    image paths and the generated CIDs is returned.

    :param in_filepath: The file path to the HTML file to be processed.
    :type in_filepath: str
    :return: A tuple containing the modified HTML content as a string and a list
        of tuples, where each tuple includes the local image file path and its
        associated CID.
    :rtype: tuple[str, list[tuple[str, str]]]
    """
    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    with open(in_filepath, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    image_paths = []
    for img in soup.find_all("img"):
        src = img.attrs.get("src", "")
        if 'http' in src or src.startswith("data:"):
            continue

        # Résoudre le chemin local de l'image
        img_local_path = urllib.parse.unquote(os.path.join(basepath, src))
        if os.path.exists(img_local_path):
            # Créer un CID unique basé sur le nom du fichier ou un UUID
            cid = email.utils.make_msgid(domain="inline.img")[1:-1]
            img.attrs["src"] = f"cid:{cid}"
            image_paths.append((img_local_path, cid))

    return str(soup), image_paths


def get_subscriber_reader(param):
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
        wb = openGoogleDBMembersSheet(sa=param.sa, id=param.sheetid)
        return iter(readAllSheet(wb)), None

    try:
        if param.database.endswith(".csv"):
            csvfile = open(param.database, "r", newline="", encoding="utf-8-sig")
            return csv.reader(csvfile, delimiter=",", quotechar='"'), csvfile
        else:
            from python_calamine import CalamineWorkbook
            workbook = CalamineWorkbook.from_path(param.database)  # type: ignore[arg-type]
            return iter(workbook.get_sheet_by_index(0).to_python()), workbook

    except FileNotFoundError:
        log.critical(f"Fichier introuvable : '{param.database}'")
        return None, None


def get_indices(header):
    """
    Create a dictionary that maps each header element to its corresponding
    index in the list of headers.

    :param header: List of header strings.
    :type header: list
    :return: A dictionary where keys are elements from the header list and
             values are their corresponding indices.
    :rtype: dict
    """
    return {h: i for i, h in enumerate(header)}


def get_smtp_connection(param):
    """
    Open a connection to the SMTP server.
    :param param:
    :return:
    """
    context = ssl.create_default_context()
    try:
        conn = SMTP(param.smtp_host, param.smtp_port)
        conn.starttls(context=context)
        conn.ehlo()
        conn.login(param.username, param.password)
        return conn
    except SMTPAuthenticationError:
        log.critical("Invalid SMTP credentials")
        sys.exit(-1)
    except Exception as e:
        log.error(f"Failed to connect to SMTP: {e}")
        return None


def get_gmail_service(param):
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
        creds = Credentials.from_authorized_user_file(param.token_file, param.scopes)
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
            # flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_ID, SCOPES)
            flow = InstalledAppFlow.from_client_config(credentials, param.scopes)
            creds = flow.run_local_server(port=0)
        with open(param.token_file, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def save_to_sent(param, msg):
    """
    Store the message in the Sent folder using IMAP.
    :param param:
    :param msg:
    :return:
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
        except Exception as e:
            if attempt < n-1 :
                log.warning(f"Retrying IMAP storage: {e}")
                sleep(10)
            else:
                log.error(f"Error copying to sent folder: {e}")


def prepare_html_and_get_images(in_filepath, max_width=800):
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
    with open(in_filepath, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    inline_images = []
    # Créer un dossier temporaire pour les images optimisées
    temp_dir = tempfile.mkdtemp()

    for img in soup.find_all("img"):
        src = img.attrs.get("src", "")
        if not src or src.startswith('http'):
            continue

        if src.startswith('data:'):
            # Traitement des images intégrées en base64
            try:
                # Format attendu : data:image/[type];base64,[data]
                header, encoded = src.split(",", 1)
                img_data = base64.b64decode(encoded)
                # On essaie de deviner l'extension à partir du header
                ext = "png" # par défaut
                if "image/" in header:
                    ext = header.split("image/")[1].split(";")[0]
                
                cid = email.utils.make_msgid(domain="inline.img")[1:-1]
                temp_img_path = os.path.join(temp_dir, f"embedded_{cid}.{ext}")
                with open(temp_img_path, "wb") as f:
                    f.write(img_data)
                
                img_path = temp_img_path
            except Exception as e:
                log.error(f"Impossible de traiter l'image en base64 : {e}")
                continue
        else:
            img_path = urllib.parse.unquote(os.path.join(basepath, src))

        if os.path.exists(img_path):
            cid = email.utils.make_msgid(domain="inline.img")[1:-1]

            # --- Logique de redimensionnement ---
            try:
                with Image.open(img_path) as im:
                    # On ne redimensionne que si l'image est plus large que max_width
                    if im.width > max_width:
                        ratio = max_width / float(im.width)
                        new_height = int(float(im.height) * float(ratio))
                        im = im.resize((max_width, new_height), Image.Resampling.LANCZOS)

                    # Sauvegarde dans le dossier temporaire en JPEG compressé
                    opt_img_name = f"{cid}.jpg"
                    opt_img_path = os.path.join(temp_dir, opt_img_name)
                    # On convertit en RGB pour le JPEG (au cas où c'est un PNG avec alpha)
                    im.convert("RGB").save(opt_img_path, "JPEG", quality=75, optimize=True)

                    img.attrs["src"] = f"cid:{cid}"
                    inline_images.append({'path': opt_img_path, 'cid': cid})
            except Exception as e:
                log.error(f"Impossible de traiter l'image {img_path}: {e}")
                # Si erreur, on peut décider de ne pas l'inclure ou de garder l'original
                continue

    return str(soup), inline_images, temp_dir


def format_message(template, row, header):
    """
    Formats a message template by replacing placeholders with corresponding values
    from the `row` list, based on the column names provided in the `header`.

    The placeholders within the template follow the syntax `${column_name}`,
    where `column_name` corresponds to an entry in the `header` list. If any
    error occurs during formatting, the original template is returned unchanged.

    :param template: The template string containing placeholders to be replaced.
    :type template: str
    :param row: A list of values where indexes correspond to the column names in the
        `header`.
    :type row: list
    :param header: A list of column names, where the index of each column
        corresponds to positional values in `row`.
    :type header: list
    :return: A formatted string with placeholders substituted with values from the
        `row` list, or the original template in case of an error.
    :rtype: str
    """
    try:
        msg_txt = re.sub(r"\${(.*?)}", r"{row[header.index('\1')]}", template)
        return eval('f"""' + msg_txt + '"""')
    except (NameError, KeyError, IndexError, SyntaxError, ValueError) as e:
        # log.error(f"Erreur d'évaluation du message : {e}")
        return template


def process_attachments(args, config, folder="input"):
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
    service, google_drive_files = None, []
    if args.file:
        for f in args.file:
            if not os.path.isfile(f):
                log.critical(f"File not found: {f}")
                sys.exit(-1)
        files = args.file
    else:
        # Nettoyage et téléchargement depuis Google Drive
        for f in glob(f"{folder}/*.*"):
            os.remove(f)
        service = gd.connect_google_driver(config['SA'])
        if 'mailing_folder' not in config:
            return [], service, []
        result = gd.get_files(service, folder_id=config["mailing_folder"])
        if result and "files" in result:
            google_drive_files = result["files"]
            gd.download_file(service, google_drive_files, folder)
        files = [f for f in glob(f"{folder}/*.*") if "published" not in f]

    return files, service, google_drive_files

def md2html(file_path, styles=None, embed_styles=False):
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
        table {width: 100%;}
    """

    if not os.path.exists(file_path):
        log.error(f"Le fichier Markdown {file_path} n'existe pas.")
        return None
    else:
        with open(file_path, "r") as f:
            data = f.read()

    # if not styles is None and not os.path.exists(styles):
    #     log.warning(f"Le fichier CSS {styles} n'existe pas. Default styles used instead.")
    #     styles = None

    converter = md.Markdown(extras=["tables", "header-ids", "cuddled-lists"])

    if styles is None:
        head = f"""
    <!-- Add locale and title header -->
    <head>
        <meta charset="UTF-8">
        <style>{default_styles}</style>
    </head>
    
"""
    elif embed_styles and os.path.exists(styles):
        with open(styles, "r") as f:
            default_styles = f.read()
            head = f"""
                <!-- Add locale and title header -->
                <head>
                    <meta charset="UTF-8">
                    <style>{default_styles}</style>
                </head>

            """
    else:
        head = f"""
   <!-- Add locale and title header -->
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="{styles}">
    </head>
"""

    html = "<html>\n" + head + converter.convert(data) + "\n</html>"
    file_path = file_path.split(".")[0] + ".html"
    with open(file_path, "w") as f:
        f.write(html)
    return file_path

def build_email(param, subject="", to="", cc="", bcc="", message="", images=None, attachments=None):
    """
    Constructs an email message with specified subject, recipients, message body,
    attachments, or inline images. The email includes advanced configurations such as
    List-Unsubscribe headers and inline attachment handling. Designed to
    support both simple and complex email requirements with flexibility.

    :param param: A configuration object containing sender details, profiles, and rules.
    :param subject: The subject of the email. Defaults to an empty string.
    :type subject: str, optional
    :param to: Comma-separated email addresses for primary recipients. Defaults to an empty string.
    :type to: str, optional
    :param cc: Comma-separated email addresses for carbon copy recipients. Defaults to an empty string.
    :type cc: str, optional
    :param bcc: Comma-separated email addresses for blind carbon copy recipients. Defaults to an empty string.
    :type bcc: str, optional
    :param message: The plain text or HTML content of the email body. Defaults to an empty string.
    :type message: str, optional
    :param images: File paths of inline images to include in the email body. Can be a string or a list of strings. Defaults to None.
    :type images: Union[str, list[str]], optional
    :param attachments: File paths of attachments to include in the email. Can be a string or a list of strings. Defaults to None.
    :type attachments: Union[str, list[str]], optional
    :return: A tuple containing the constructed email message (MIMEMultipart object) and list of recipient email addresses.
    :rtype: Tuple[MIMEMultipart, list[str]]
    """
    # 1. Build Message
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = formataddr((param.sendername, param.sender))
    
    # Ajout de l'en-tête List-Unsubscribe
    # Il est recommandé de fournir à la fois une URL (http) et une adresse mail (mailto)
    # unsubscribe_url = "https://www.votre-site.be/unsubscribe" # À adapter selon vos paramètres
    unsubscribe_mail = f"mailto:{param.sender}?subject=unsubscribe"
    
    msg["List-Unsubscribe"] = f"<{unsubscribe_mail}>"  # , <{unsubscribe_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click" # Recommandé par les nouveaux standards Gmail/Yahoo 2024

    if param.max_addr_per_mail == 1:
        to = bcc
        bcc = None
        msg["To"] = to
    else:
        msg["To"] = f"{to},{formataddr((param.sendername, param.sender))}"
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Date"] = email.utils.formatdate(localtime=True)

    if param.domain:
        msg["Message-ID"] = email.utils.make_msgid(idstring=str(uuid4()), domain=param.domain)
    # elif param.profile == 'cambristi':
    #    msg["Message-ID"] = email.utils.make_msgid(idstring=str(uuid4()), domain="gmail.com")

    # Conteneur pour le corps du mail et ses images liées
    msg_related = MIMEMultipart("related")
    all_inline_images = []
    temp_dirs = [] # Liste pour suivre les dossiers à nettoyer


    # 2. Add Content & Attachments
    # Gestion des images passées explicitement en argument (si elles ne sont pas dans le HTML)
    for img_path in [images] if isinstance(images, str) else (images or []):
        if os.path.exists(img_path):
            cid = email.utils.make_msgid(domain="inline.img")[1:-1]
            all_inline_images.append({'path': img_path, 'cid': cid})

    for att in [attachments] if isinstance(attachments, str) else (attachments or []):
        if att.endswith(("htm", "html", "md")):
            is_md = att.endswith("md")
            if is_md:
                att = md2html(att, styles=param.styles if hasattr(param, "styles") else None, embed_styles=True)
            # C'est ici que la magie opère pour le HTML
            html_content, found_images, t_dir = prepare_html_and_get_images(att)
            message = html_content
            all_inline_images.extend(found_images)
            temp_dirs.append(t_dir)
            if is_md and not hasattr(param, "keep-html"):
                os.remove(att)
        else:
            with open(att, "rb") as f:
                content = f.read()
                # ... existing code for other attachment types (pdf, txt, mhtml) ...
                if att.endswith("pdf"):
                    part = MIMEApplication(content, _subtype="pdf")
                    part.add_header("Content-Disposition", "attachment", filename=os.path.basename(att))
                    msg.attach(part)
                elif att.endswith("txt"):
                    msg.attach(MIMEText(content.decode()))

    # Construction de la partie HTML avec images intégrées
    if message and "<html" in message:
        part_html = MIMEText(message, "html")
        msg_related.attach(part_html)

        for img_info in all_inline_images:
            try:
                with open(img_info['path'], "rb") as f:
                    img_part = MIMEImage(f.read())
                    img_part.add_header("Content-ID", f"<{img_info['cid']}>")
                    img_part.add_header("Content-Disposition", "inline",
                                        filename=os.path.basename(img_info['path']))
                    msg_related.attach(img_part)
            except Exception as e:
                log.error(f"Error attaching inline image {img_info['path']}: {e}")

        msg.attach(msg_related)
    elif message:
        msg.attach(MIMEText(message, "plain"))

    # 3. Recipients
    recipients = [r.strip() for r in f"{to},{cc},{bcc}".split(",") if r.strip()]

    # On attache la liste des dossiers temporaires à l'objet msg pour le nettoyage futur
    msg._temp_dirs = temp_dirs

    return msg, recipients


def generate_mailing(param):
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
        pause =  param.pause
        max_mail_per_hour = param.max_mails_per_hour
    except AttributeError as e:
        log.critical(f"Clé de configuration manquante : {e}")
        return "Error"

    reader, file_object = get_subscriber_reader(param)
    if not reader:
        return "Error"

    try:
        header = next(reader, None)
        if not header: return "Error"
        indices = get_indices(header)

        # Skip initial records if requested
        current_row_idx = 1
        if param.from_index:
            log.info(f"Reprise à l'index {param.from_index}")
            for _ in range(2, int(param.from_index)):
                next(reader, None)
                current_row_idx += 1

        addressees, recipient_count, mail_batch_count = [], 0, 0
        start_time = time()

        for row in reader:
            current_row_idx += 1

            # stop is requested last record is reached
            if param.to_index and current_row_idx > int(param.to_index):
                break

            if filter(param.filter, row, indices):
                    continue

            if param.verbose:
                print(row[indices["email"]])

            addressees.append(row[indices["email"]])
            recipient_count += 1

            if len(addressees) >= max_add:
                log.info(f"Envoi à {len(addressees)} destinataires (Index: {current_row_idx})")
                msg_body = format_message(param.message, row, header)
                if not param.donotsend:
                    msg, recipients = build_email(param=param, subject=param.subject, message=msg_body,
                              bcc=",".join(addressees), attachments=param.file)
                    try:
                        if hasattr(param, 'smtp_host'):
                            send_mail(param=param, message=msg, recipients=recipients)
                        else:
                            send_gmail(get_gmail_service(param), message=msg)

                    finally:
                        # Nettoyage des dossiers temporaires créés pour ce mail
                        if hasattr(msg, '_temp_dirs'):
                            for d in msg._temp_dirs:
                                try:
                                    shutil.rmtree(d)
                                    if param.verbose:
                                        log.info(f"Dossier temporaire supprimé : {d}")
                                except Exception as e:
                                    log.error(f"Erreur lors du nettoyage de {d}: {e}")

                addressees, mail_batch_count = [], mail_batch_count + 1
                sleep(pause)
                if recipient_count % max_mail_per_hour == 0:
                    log.info("Limite horaire atteinte. Pause d'une heure...")
                    sleep(3600)

        if addressees:
            log.info(f"Envoi final à {len(addressees)} destinataires.")
            msg_body = format_message(param.message, row, header)
            if not param.donotsend:
                msg, recipients = build_email(param=param, subject=param.subject, message=msg_body,
                                  bcc=",".join(addressees), attachments=param.file)
                if hasattr(param, 'smtp_host'):    # param.profile == 'artscroises':
                    send_mail(param=param, message=msg, recipients=recipients)
                else:
                    send_gmail(get_gmail_service(param), message=msg)
            mail_batch_count += 1

        log.info(
            f"Terminé. {recipient_count} adresses traitées en {mail_batch_count} envois ({int(time() - start_time)}s)")
        return "OK"
    finally:
        if file_object: file_object.close()


def filter(filter, row, indices):
    """
    Evaluates a set of filtering conditions on a given row of data using field indices.

    This function checks each field-value pair in a filter dictionary against a row of
    data by performing the specified operations. Only rows that do not match the filter
    criteria will pass (return `False`). The function supports a variety of comparison
    operations, such as equality, inequality, greater-than, less-than, and membership.

    Supported operations:
    - "is"
    - "is not"
    - "gt" (greater than)
    - "lt" (less than)
    - "ge" (greater than or equal)
    - "le" (less than or equal)
    - "in"
    - "not in"
    - "is empty"
    - "is not empty"
    - "greater than" (alias for "gt")
    - "less than" (alias for "lt")
    - "greater or equal to" (alias for "ge")
    - "less or equal to" (alias for "le")
    - "one of" (alias for "in")
    - "none of" (alias for "not in")
    - "is equal to" (alias for "is")
    - "is not equal to" (alias for "is not")
    - "eq" (alias for "is equal to")
    - "ne" (alias for "is not equal to")

    Filter values can specify further conditions through implicit parsing. For example:
    - Comma-separated values for membership tests (e.g., "in").
    - Empty string values to test for emptiness.

    The function logs warnings for invalid operations or values encountered in the filter.

    :param filter: Dictionary containing filter conditions, where each key represents
                   a field name, and the value is a string describing the operation
                   and target value (e.g., "gt 10").
    :type filter: dict
    :param row: A list of field values representing a single data row that will be
                checked against the filtering criteria.
    :type row: list
    :param indices: Dictionary mapping filter field names to their respective column
                    index positions in the `row` list. Used to retrieve field values
                    for comparison.
    :type indices: dict
    :return: `True` if the given row does not satisfy the filter criteria, `False`
             otherwise.
    :rtype: bool
    """
    if filter == {}:
        return False

    result = True

    # Allowed operations
    ops = [
        "is", "is not", "gt", "lt", "ge", "le", "in", "not in",
        "is empty", "is not empty", "greater than", "less than",
        "greater or equal to", "less or equal to", "one of", "none of",
        "is equal to", "is not equal to", "eq", "ne"
    ]

    for k, v in filter.items():
        res = True
        field_value = row[indices[k]] if k in indices and indices[k] < len(row) else None
        if field_value is None:
            log.warning(f"Invalid field '{k}'")
            return True
        # get the operator
        try:
            op = ops[[v.find(x + ' ') for x in ops].index(0)]
        except ValueError:
            log.warning(f"Invalid filter operation for field '{k}: {v}'")
            return True
        # get the value to compare with
        test_value = v.split(op)[1].strip()
        # correct the operator if needed
        if 'not ' in test_value:
            op += ' not'
            test_value = test_value.split('not')[1].strip()
        if 'empty' in test_value:
            op += ' empty'
            test_value = None
        # find if test_value should be a list
        if test_value and ',' in test_value:
            test_value = test_value.replace(' ', '').split(',')

        try:
            field_value = float(field_value)
            try:
                test_value = float(test_value)
            except ValueError:
                log.warning(f"Invalid filter value for field '{k}: {test_value}'")
                return True
            # numeric comparison
            if op == "ge" or op == "greater than or equal to":
                res = (field_value >= test_value)
            elif op == "gt" or op == "greater than":
                res = (field_value > test_value)
            elif op == "le" or op == "less than or equal to":
                res = (field_value <= test_value)
            elif op == "lt" or op == "less than":
                res = (field_value < test_value)
            elif op == "eq" or op == "is equal to":
                res = (field_value == test_value)
            elif op == "ne" or op == "is not equal to":
                res = (field_value != test_value)

        except ValueError:
            # string comparison
            if op == "in" or op == 'one of':
                res = (field_value in test_value)
            elif op == "not in" or op == 'none of':
                res = (field_value not in test_value)
            elif op == "is" or op == 'is equal to':
                res = (field_value == test_value)
            elif op == "is not" or op == 'is not equal to':
                res = (field_value != test_value)
            elif op == "is not empty":
                res = (field_value != "" and field_value is not None)
            elif op == "is empty":
                res = (field_value == "" or field_value is None)

        if not res:
            return True
        result = result and res

    return not result


def send_gmail(service, message=None):
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
        return service.users().messages().send(userId='me', body=body).execute()
    except errors.HttpError as error:
        log.error(f'Error sending message: {error} to {message["To"]}')
        return None


def send_mail(param=None,message=None, recipients=None):
    """
    Send an email message to specified recipients using SMTP.

    This function attempts to send an email message to the specified list of
    recipients using an SMTP connection. It retries sending the email up to two
    times in case of a failure. Logging and other functionalities depend on the
    settings provided in the `param` object. The email is saved to the sent records
    if it is successfully sent.

    :param param: A configuration object that determines the behavior of the
        email-sending process, such as verbosity for logging.
    :type param: Any
    :param message: The email message to be sent, where the "From" field is
        mandatory and expected to be correctly populated.
    :type message: email.message.EmailMessage
    :param recipients: A list of recipient email addresses to whom the message
        should be sent.
    :type recipients: list[str]
    :return: A boolean indicating whether the email was successfully sent.
    :rtype: bool
    """
    if param.verbose:
        log.info(f"Sending email to {recipients}")
    success = False
    for attempt in range(2):
        conn = get_smtp_connection(param)
        if conn:
            try:
                conn.sendmail(message["From"], recipients, message.as_string())
                conn.quit()
                success = True
                if param.verbose:
                    log.info("sent")
                break
            except SMTPException as e:
                log.error(f"SMTP error on attempt {attempt + 1}: {e}")
                if attempt == 0:
                    sleep(10)

    if success:
        save_to_sent(param, message)
    return success


def get_newsletter_name(files, args):
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


def process_profile(args):
    """
    Processes the user profile to configure and send a mailing task with attachments. The function
    integrates configurations, manages secrets, processes attachments, and dynamically generates
    and sends the mailing.

    :param args: The argparse.Namespace object containing the configurations and command-line
        arguments required for the mailing process.
    :return: A string indicating the success or failure of the process. Returns "OK" if the
        mailing was successfully sent; otherwise, returns "Error".
    """
    config = args.conf[args.profile]
    # Secret retrieval is optional (but more secure)
    # if secret vault or file is not accessible, just ignore and assume everything is in the config file
    # config data overrides secret data
    try:
        secret = get_secret(config["MAILCONFIG"])
        if secret is None:
            log.warning("No secret configuration found")
            secret = {}
    except Exception as e:
        log.warning(f"Error retrieving secret configuration: {e}")
        secret = {}
    config = {**secret, **config}

    files, service, google_drive_files = process_attachments(args, config)

    body_txt = args.body if args.body else ""
    args.newsletter_name = ""

    args = get_newsletter_name(files, args)
    if not args.message:
        args.message = config["default_message"]
        args.message = args.message.replace("${newsletter_name}", args.newsletter_name)
        args.message = args.message.replace("${body}", body_txt)

    config.update(vars(args))
    if "password" not in config:
        config["password"] = getpass("Enter mail user's password")

    param = Dict2Class(config)
    param.file = files  # Mise à jour explicite des fichiers filtrés

    if param.test:
        param.filter = param.filter_test

    if not check_mandatory_param(param):
        return "Error"
    if generate_mailing(param) == "OK" and not args.test:
        for f in google_drive_files:
            gd.rename_file(service, f["id"], f"published_{f['name']}")
        for f in glob("input/*.*"):
            os.remove(f)
        return "OK"
    else:
        return "Error"


def check_mandatory_param(param):
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
    ret = True

    # Parameters mandatory for ALL modes
    common_params = ['subject', 'sender', 'sendername', 'message']
    for p in common_params:
        if not hasattr(param, p) or getattr(param, p) is None:
            log.error(f"{p.replace('_', ' ').capitalize()} is mandatory")
            ret = False

    # Data source check
    if not hasattr(param, 'database') and not (hasattr(param, 'sa') and hasattr(param, 'sheetid')):
        log.error("Database path or (Service Account (SA) and SheetID) is mandatory")
        ret = False

    # Mailing method specific checks
    if hasattr(param, 'smtp_host'):
        # SMTP/IMAP mode
        smtp_imap_params = ['smtp_port', 'smtp_port', 'imap_host', 'imap_port', 'username', 'password', 'sent_folder']
        for p in smtp_imap_params:
            if not hasattr(param, p) or getattr(param, p) is None:
                log.error(f"{p.replace('_', ' ').upper()} is mandatory for SMTP/IMAP mode")
                ret = False
    else:
        # Gmail mode
        gmail_params = ['token_file', 'scopes', 'credentials_id']
        for p in gmail_params:
            if not hasattr(param, p) or getattr(param, p) is None:
                log.error(f"{p.replace('_', ' ').capitalize()} is mandatory for Gmail mode")
                ret = False

    if not ret:
        log.critical("Please check and update your configuration file")

    return ret

def setup_argparse():
    """
    Sets up and parses command-line arguments for a mailing utility.

    This function configures an argument parser with various command-line options
    to customize email sending behavior. The options include mail subject, body,
    attachments, database indices, test mode, verbosity, and other configurations
    for controlling email sending and processing.

    :return: Parsed arguments from the command line
    :rtype: argparse.Namespace

    Options:
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
    parser.add_argument("-s", "--subject", help="Subject of the mail")
    parser.add_argument("-m", "--message", help="Text message of the mail", default="")
    parser.add_argument("file", nargs="*", help="files to attach to the mail")
    parser.add_argument("-t", "--test", action="store_true", help="test mode - send only to the tester group")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-x", "--doNotSend", action="store_true", help="Do not send any mail")
    parser.add_argument("-db", "--database", help="database path")
    parser.add_argument("-f", "--from_index", help="Starting index in the database", default=None)
    parser.add_argument("-to", "--to_index", help="Stopping index in the database", default=None)
    parser.add_argument("-w", "--wait", help="Wait x minutes before restarting sending mail", type=int)
    parser.add_argument("--selected", action="store_true", help="Only send selected mail", default=False)
    parser.add_argument("--body")
    parser.add_argument("-mh", "--max-mails-per-hour", default=1000, type=int)
    parser.add_argument("-na", "--max_addr_per_mail", default=50, type=int)
    parser.add_argument("-p", "--pause", default=3, type=int)
    parser.add_argument("--profile", help="mail profile")
    parser.add_argument("--md2html", action="store_true", help="convert md file to html & exit")
    parser.add_argument("--keep-html", action="store_true", help="keep the generated html file")
    return parser.parse_args()


def main():
    """
    Changes the current working directory to the directory of the executing file, parses
    command-line arguments, and loads configuration settings from a YAML file. Based on
    the specified profile in the arguments, it processes the respective profile logic.

    :return: None
    """
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    args = setup_argparse()
    args.conf = yaml.safe_load(open("config.yml"))

    if args.md2html and args.file[0].endswith(".md"):
        md2html(args.file[0], "../css/styles.css")
        file = args.file[0].replace(".md", ".html")
        make_html_images_inline(file, file)
        sys.exit(0)

    if not (args.message or args.body or args.file) and not args.subject:
        print("Missing subject and message text or file")
        sys.exit(-1)

    if args.profile:
        sys.exit(0 if process_profile(args) == "OK" else -1)
    else:
        log.critical("No profile specified")
        sys.exit(-1)

if __name__ == "__main__":
    main()
