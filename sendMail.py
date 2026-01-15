#!/usr/bin/env python
# coding: utf-8
"""

TODO: understand why image src from web are showed as attachment, not embedded in html


"""


import argparse
import base64
import csv
import datetime as dt
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
import requests
import yaml
from PIL import Image
from bs4 import BeautifulSoup
from certifi import where
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
    Initialise le module de journalisation vers la sortie standard et un fichier optionnel.
    :param log_file: Le chemin du fichier de log.
    :return: Un objet logger configuré.
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


def prepare_html_for_cid(in_filepath):
    """
    Scanne le HTML, remplace les chemins locaux par des CID et retourne
    le HTML modifié ainsi que la liste des chemins d'images à attacher.
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


class Invoice:
    """
    Handles invoicing and order management operations using an external API.

    The Invoice class provides functionality to interact with the Billit.be third-party
    API to manage orders and clients. It allows creating clients, managing
    invoices, and interacting with API endpoints for various operations.

    Class Attributes:
    :ivar EXPIRY_DAYS: Number of days after which an invoice expires.
    :type EXPIRY_DAYS: int

    Instance Attributes:
    :ivar token: API token for authentication.
    :type token: str
    :ivar base: Base URL for the API (depends on the environment).
    :type base: str
    :ivar headers: Headers used for API requests, including authentication.
    :type headers: dict
    """

    EXPIRY_DAYS = 30

    def __init__(self, prod=False):
        token_dict = get_secret("ArtsCroisesAPIToken")
        if prod:
            self.token = token_dict["token"]
            self.base = token_dict["baseUrl"]
        else:
            self.token = token_dict["devToken"]
            self.base = token_dict["devBaseUrl"]
        self.headers = {"apiKey": self.token, "accept": "application/json"}

    def _make_request(self, method, endpoint, json=None):
        """
        Makes a request to the Billit.be API using the specified method and endpoint.
        :param method:
        :param endpoint:
        :param json:
        :return:
        """
        url = self.base + endpoint
        headers = (
            {**self.headers, "content-type": "text/json"} if json else self.headers
        )
        response = requests.request(
            method, url, headers=headers, json=json, verify=where()
        )
        if response.status_code != 200:
            log.error(f"{method} {endpoint} failed: {response.text}")
            return None
        return response

    def get_client(self, client_id):
        """
        Retrieves details for a client using its ID.
        :param client_id:
        :return:
        """
        response = self._make_request("GET", f"parties/{client_id}")
        if response.status_code != 200:
            return None
        return response.json()

    def create_client(self, row, indices):
        """
        Creates or update a new client using the provided row data.
        :param row:
        :param indices:
        :return:
        """
        data = {
            "PartyID": row[indices["id"]],
            "Nr": row[indices["id"]],
            "Name": row[indices["first_name"]] + " " + row[indices["last_name"]],
            "Mobile": row[indices["mobile_phone"]],
            "Phone": row[indices["phone"]],
            "Email": row[indices["email"]],
            "ContactFirstName": row[indices["first_name"]],
            "ContactLastName": row[indices["last_name"]],
            "PartyType": "Customer",
        }
        response = self._make_request("POST", "parties", json=data)
        if not response or response.status_code != 200:
            return -1
        return response.text

    def create_order(self, client=None, product_name="", price=0.0, qty=1):
        """
        Creates a new order for the specified client.
        :param client:          "client" object returned by _get_client()
        :param product_name:    product_name
        :param price:           product unit price
        :param qty:             product qua,tity
        :return:                an "order" object
        """

        if not client:
            return -1

        today = dt.date.today()
        order_data = {
            "OrderType": "Invoice",
            "OrderDirection": "Income",
            "OrderDate": today.isoformat(),
            "ExpiryDate": (today + dt.timedelta(days=self.EXPIRY_DAYS)).isoformat(),
            "OrderTitle": product_name,
            "OrderLines": [
                {
                    "Quantity": qty,
                    "UnitPriceExcl": price,
                    "Description": product_name,
                    "VATPercentage": 0.0,
                    "Reference": "C2026",
                }
            ],
            "Customer": client,
        }

        response = self._make_request("POST", "orders", json=order_data)
        if not response:
            return -1

        order_id = response.text
        log.debug(f"OrderID: {order_id}")

        # Refresh order details
        response = self._make_request("GET", f"orders/{order_id}")
        if not response:
            return -1
        return response.json()



def _process_membership_invoice(param, row, indices):
    """
    Processes a membership invoice for the Arts Croisés association. The function validates the provided
    information, creates a client if necessary, generates a membership invoice, and composes a message
    for the member conveying payment details.

    It ensures the client meets the criteria for membership renewal, attempts to handle the creation of
    a client and order, and formats the final message detailing how to proceed with the payment.

    :param param: An object that contains properties and behaviors necessary for invoice processing.
    :param row: A dictionary-like object containing the details of a single member or transaction.
    :param indices: A dictionary mapping field names to their corresponding indices within the row object.
    :return: A boolean indicating whether the membership invoice was successfully processed. Returns
        None if any mandatory step in processing fails.
    """
    if param.profile != 'artscroises':
        return None
    if not (row[indices["member"]] == "yes" and
            not row[indices["membershippaid"]] and
            row[indices["email"]]):
        return None

    client_id = param.invoice.create_client(row, indices)
    if client_id == -1:
        log.error(f"Failed to create client for {row[indices['id']]}.")
        return None

    client = param.invoice.get_client(client_id)
    if not client:
        return None

    order = param.invoice.create_order(
        client=client,
        product_name=f"Cotisation Arts Croisés {param.cotisation_year}",
        price=param.cotisation_amount,
        qty=1,
    )
    if order["OrderID"] == -1:
        log.error(f"Failed to create invoice for {row[indices['id']]}.")
        return None

    bank = order["Supplier"]["BankAccounts"][0]
    acc_name = bank.get("Name", order["Supplier"]["Name"])

    param.message = f"""
        <html>
        Chère/cher {row[indices["first_name"]]} {row[indices["last_name"]]},<br/><br/>
        Nous vous souhaitons tous nos meilleurs voeux pour {param.cotisation_year}.<br/><br/>
        Voici le temps de renouveler votre cotisation en tant que membre de notre association Arts Croisés.<br/><br/>
        Si vous souhaitez rester membre, veuillez payer le montant de {param.cotisation_amount} {bank['Currency']} 
        par personne sur le compte suivant :<br/><br/>
        {acc_name}<br/>
        IBAN : {bank['IBAN']}<br/>
        Communication: {order["PaymentReference"]}<br/><br/>
        Cordialement,<br/>
        L'équipe Arts Croisés<br/>
        {order["Supplier"]["Email"]}
        </html>
    """
    return True

def _get_subscriber_reader(param):
    """Extrait la logique de lecture de la source de données."""
    if param.database is None:
        wb = openGoogleDBMembersSheet(sa=param.sa, id=param.sheetid)
        return iter(readAllSheet(wb)), None

    try:
        csvfile = open(param.database, "r", newline="", encoding="utf-8-sig")
        return csv.reader(csvfile, delimiter=",", quotechar='"'), csvfile
    except FileNotFoundError:
        log.critical(f"Fichier introuvable : '{param.database}'")
        return None, None


def _get_indices(header):
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


def _get_smtp_connection(param):
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
        token = get_secret(param.token_id)
        creds = Credentials.from_authorized_user_info(token, param.scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials = get_secret(param.credentials_id)
            # flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_ID, SCOPES)
            flow = InstalledAppFlow.from_client_config(credentials, param.SCOPES)
            creds = flow.run_local_server(port=0)
        with open(param.token_file, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def _save_to_sent(param, msg):
    """
    Store the message in the Sent folder using IMAP.
    :param param:
    :param msg:
    :return:
    """
    for attempt in range(2):
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
            if attempt == 0:
                log.warning(f"Retrying IMAP storage: {e}")
                sleep(10)
            else:
                log.error(f"Error copying to sent folder: {e}")


def prepare_html_and_get_images(in_filepath, max_width=800):
    """
    Lit un fichier HTML, remplace les images locales par des CIDs,
    et redimensionne les images trop grandes pour réduire le poids du mail.
    """

    basepath = os.path.split(in_filepath.rstrip(os.path.sep))[0]
    with open(in_filepath, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    inline_images = []
    # Créer un dossier temporaire pour les images optimisées
    temp_dir = tempfile.mkdtemp()

    for img in soup.find_all("img"):
        src = img.attrs.get("src", "")
        if not src or src.startswith(('http', 'data:')):
            continue

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


def _format_message(template, row, header):
    """Gère le remplacement des variables dans le corps du message."""
    try:
        msg_txt = re.sub(r"\${(.*)}", r"{row[header.index('\1')]}", template)
        return eval('f"""' + msg_txt + '"""')
    except (NameError, KeyError, IndexError, SyntaxError) as e:
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


def build_email(param, subject="", to="", cc="", bcc="", message="", images=None, attachments=None):
    # ... existing code ...
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

    if param.cotisation or param.max_addr_per_mail == 1:
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
    if param.profile == 'artscroises':
        msg["Message-ID"] = email.utils.make_msgid(idstring=str(uuid4()), domain="artscroises.be")
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
            # Note: Si vous utilisez cette option, vous devrez manuellement
            # mettre cid:id dans votre message texte.

    for att in [attachments] if isinstance(attachments, str) else (attachments or []):
        if att.endswith(("htm", "html")):
            # C'est ici que la magie opère pour le HTML
            html_content, found_images, t_dir = prepare_html_and_get_images(att)
            message = html_content
            all_inline_images.extend(found_images)
            temp_dirs.append(t_dir)
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
    Generates and sends email batches based on the specified parameters and subscription data.

    The function processes subscriber data, filters the recipients based on given conditions,
    formats the message body, and sends emails in batches while adhering to specified constraints
    such as maximum recipients per mail and maximum emails per hour. Handles special cases like
    membership-specific invoicing, restricts email sending to specific recipient indices,
    and optionally resumes at a specified index.

    :param param: Object containing configurations and parameters for the email generation
                  and sending process (e.g., max address per mail, pause duration, verbose
                  mode, subscription filters, etc.).
    :type param: object

    :return: A string indicating the result of the operation. Returns "OK" if successful, or
             "Error" in case of a failure.
    :rtype: str

    :raises AttributeError: Raised if a required configuration key is missing in the
                            `param` object.
    """
    try:
        max_add = 1 if param.cotisation else param.max_addr_per_mail
        pause = 0 if param.cotisation else param.pause
        max_mail_per_hour = param.max_mails_per_hour
    except AttributeError as e:
        log.critical(f"Clé de configuration manquante : {e}")
        return "Error"

    reader, csvfile = _get_subscriber_reader(param)
    if not reader:
        return "Error"

    try:
        header = next(reader, None)
        if not header: return "Error"
        indices = _get_indices(header)

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

            # filtering
            if param.profile == 'artscroises':
                if param.cotisation:
                    if not _process_membership_invoice(param, row, indices):
                        continue
                elif _filter_artscroises(param, row, indices):
                    continue
            elif param.profile == 'cambristi':
                if _filter_cambristi(param, row, indices, param.test):
                    continue

            if param.verbose:
                print(row[indices["email"]])

            addressees.append(row[indices["email"]])
            recipient_count += 1

            if len(addressees) >= max_add:
                log.info(f"Envoi à {len(addressees)} destinataires (Index: {current_row_idx})")
                msg_body = _format_message(param.message, row, header)
                if not param.donotsend:
                    msg, recipents = build_email(param=param,subject=param.subject, message=msg_body,
                              bcc=",".join(addressees), attachments=param.file)
                    try:
                        if param.profile == 'artscroises':
                            send_mail(param=param, message=msg, recipients=recipents)
                        elif param.profile == 'cambristi':
                            send_gmail(get_gmail_service(param), message= msg)
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
            msg_body = _format_message(param.message, row, header)
            if not param.donotsend:
                msg, recipients = build_email(param=param, subject=param.subject, message=msg_body,
                                  bcc=",".join(addressees), attachments=param.file)
                if param.profile == 'artscroises':
                    send_mail(param=param, message=msg, recipients=recipients)
                elif param.profile == 'cambristi':
                    send_gmail(get_gmail_service(param), message=msg)
            mail_batch_count += 1

        log.info(
            f"Terminé. {recipient_count} adresses traitées en {mail_batch_count} envois ({int(time() - start_time)}s)")
        return "OK"
    finally:
        if csvfile: csvfile.close()


def _filter_artscroises(param, row, indices):
    """
    Filters rows based on specific conditions such as status, group, selection,
    and email presence. The function evaluates multiple constraints using the
    provided parameters, data row, and column indices to determine the
    exclusion or inclusion of the row.

    :param param: An object containing filtering options such as test mode
        and selection criteria.
    :type param: Any
    :param row: A list or array representing a single row of data to be
        evaluated by the filter.
    :type row: list
    :param indices: A dictionary mapping column names to their respective
        indices in the row for easy access to specific data points.
    :type indices: dict
    :return: A boolean value. True if the row should NOT pass the filter
        (i.e., be excluded), False if it should pass.
    :rtype: bool
    """
    is_active = row[indices["status"]] == "active"
    is_test_match = not param.test or "Test" in row[indices["group"]]
    is_selected = (
            not param.selected or row[indices["selected"]].lower() == "x"
    )
    has_email = bool(row[indices["email"]])
    return not (is_active and is_test_match and is_selected and has_email)


def _filter_cambristi(param, row, indices, test):
    if test:
        try:
            return not ('test' in row[indices["title"]] )
        except IndexError:
            log.warning(f"No title in row {row[indices['nom']]}, {row[indices['prenom']]}")
            return True
    else:
        try:
            is_active = row[indices["title"]] == "member"
            has_mail = bool(row[indices["email"]])
            return not (is_active and has_mail)
        except IndexError:
            return True


def send_gmail(service,message=None):
    """
    This function is used to send an email using the Gmail API. The provided `service`
    object facilitates interaction with the Gmail API. An input `message` object must
    also be provided, containing the email to be sent. The function encodes the email
    in a URL-safe format and sends it using the API. In the case of an error during
    transmission, the error is logged, and `None` is returned.

    :param service: A resource object with methods for interacting with the Gmail API.
    :param message: An email message object containing the data to send. Should
       implement the `as_bytes` method for conversion to raw bytes format.
    :return: The API response on successful email sending, or `None` if an error
       occurs.
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
        conn = _get_smtp_connection(param)
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
        _save_to_sent(param, message)


def _sync(param):
    """
    Synchronize Arts Croisés members only database with Billit
    :param param:
    :return:
    """
    if param.profile != 'artscroises':
        return "N/A"
    reader, csvfile = _get_subscriber_reader(param)
    header = next(reader, None)
    if not header:
        return "Error"

    # mapping des headers
    indices = {
        "email": header.index("email"),
        "id": header.index("id"),
        "first_name": header.index("first_name"),
        "last_name": header.index("last_name"),
        "phone": header.index("phone"),
        "mobile_phone": header.index("mobile_phone"),
        "address": header.index("address"),
        "city": header.index("city"),
        "zip": header.index("zip"),
        "member": header.index("member"),
        "membershippaid": header.index(f"Cotisation {param.cotisation_year}"),
        "group": header.index("mailing_list"),
        "selected": header.index("selected"),
        "status": header.index("status"),
    }
    # Sauter les enregistrements initiaux
    current_row_idx = 1
    if param.from_index:
        log.info(f"Reprise à l'index {param.from_index}")
        for _ in range(2, int(param.from_index)):
            next(reader, None)
            current_row_idx += 1

    for row in reader:
        current_row_idx += 1
        if param.to_index and current_row_idx > int(param.to_index):
            break

        # Filtres de sélection
        has_email = bool(row[indices["email"]])
        is_member = row[indices["member"]] == "yes"

        if is_member:  # and has_email:
            # Create or update member as client
            client_id = param.invoice.create_client(row, indices)
            if client_id == -1:
                log.error(f"Failed to create client for {row[indices['id']]}.")
                continue
            client = param.invoice.get_client(client_id)
            if not client:
                continue
            log.info(
                f"Client for {row[indices['first_name']]} {row[indices['last_name']] } sync'ed."
            )

    return "Done"


def process_artscroises(args):
    """
    Processes and configures the Arts Croisés mailing workflow including handling of
    attachments, configuration settings, and messaging details derived from the provided
    arguments and configurations.

    :param args: Parsed arguments containing configuration details for mailing options.
    :type args: argparse.Namespace
    :return: None
    """
    config = args.conf[args.profile]
    # config overrides secret data
    config = {**get_secret(config["MAILCONFIG"]), **config }
    if config is None:
        log.critical("No secret configuration found")
        sys.exit(1)

    # and args overrides config data
    if config["max_mails_per_hour"]:
        args.max_addr_per_mail = int(config["max_mails_per_hour"])
    if config["max_addr_per_mail"]:
        args.max_mails_per_hour = int(config["max_mails_per_hour"])
    if config["pause"]:
        args.pause = int(config["pause"])

    files, service, google_drive_files = process_attachments(args, config)

    body_txt = args.body if args.body else ""
    args.newsletter_name = ""

    # Analyse des fichiers pour le sujet et le corps
    for f in files:
        basename = os.path.basename(f)
        ext = basename.split(".")[-1].lower()
        name_part = basename.split(".")[0]

        if ext in ["pdf", "html"]:
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

    if not args.message:
        args.message = f"\nChers amies et amis des Arts Croisés,\n{body_txt}\nVeuillez trouver en pièce jointe notre newsletter {args.newsletter_name}.\nBonne lecture!\n\nL'équipe Arts Croisés, asbl\n..."

    if args.wait:
        log.info(f"Start sending in {args.wait} minutes")
        for i in range(args.wait):
            print(f"Sleeping for {args.wait - i} minutes      \r", end="", flush=True)
            sleep(60)

    config.update(vars(args))
    if "password" not in config:
        config["password"] = getpass("Enter mail user's password")

    param = Dict2Class(config)
    param.file = files  # Mise à jour explicite des fichiers filtrés

    if args.cotisation:
        param.invoice = Invoice(prod=not args.test)
        param.subject = f"Arts Croisés - Cotisation {param.cotisation_year}"

    if args.sync:
        param.invoice = Invoice(prod=not args.test)
        _sync(param)

    elif generate_mailing(param) == "OK" and not args.test:
        for f in google_drive_files:
            gd.rename_file(service, f["id"], f"published_{f['name']}")
        for f in glob("input/*.*"):
            os.remove(f)


def process_cambristi(args):
    """
    Processes and sends emails with optional attachment handling and message body
    generation based on the provided profile configuration.

    This function initializes the configuration based on the provided arguments,
    combines it with secret configuration data, and processes any attachments.
    It then uses the updated configuration to create and send mailing content
    through a specified email service.

    :param args: The argparse.Namespace object containing the command-line
        arguments, including profile and other configurations.
    :returns: None
    """
    config = args.conf[args.profile]
    # config overrides secret data
    if "MAILCONFIG" in config:
        config = {**get_secret(config["MAILCONFIG"]), **config }
    if config is None:
        log.critical("No secret configuration found")
        sys.exit(1)
    files, service, google_drive_files = process_attachments(args, config)

    config.update(vars(args))
    param = Dict2Class(config)
    param.file = files
    # if 'html' in files[0]:
    #     param.message = open(files[0], encoding="utf-8").read()
    #     param.file=files[1:]
    generate_mailing(param)


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
        - --cotisation: Generates a cotisation reminder mail (default: False).
        - -y, --cotisation_year: Year for cotisation reminders (default: '2026').
        - -amt, --cotisation_amount: Amount for cotisation reminders (default:
          '15.00').
        - -mh, --max-mails-per-hour: Maximum emails to send per hour (default:
          1000).
        - -na, --max_addr_per_mail: Maximum number of addresses per mail (default:
          50).
        - -p, --pause: Pause duration in seconds between operations (default: 3).
        - --sync: Flag to enable synchronization mode (default: False).
        - --check_spam: Flag to perform spam detection checks (default: False).
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
    parser.add_argument("--cotisation", help="Generate cotisation reminder mail", action="store_true", default=False)
    parser.add_argument("-y", "--cotisation_year", help="Cotisation year", default="2026")
    parser.add_argument("-amt", "--cotisation_amount", help="Cotisation amount", default="15.00")
    parser.add_argument("-mh", "--max-mails-per-hour", default=1000, type=int)
    parser.add_argument("-na", "--max_addr_per_mail", default=50, type=int)
    parser.add_argument("-p", "--pause", default=3, type=int)
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--check_spam", action="store_true")
    parser.add_argument("--profile", help="mail profile")
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
    if args.profile == "artscroises":
        process_artscroises(args)
    elif args.profile == "cambristi":
        process_cambristi(args)

if __name__ == "__main__":
    main()
