#!/usr/bin/env python
# coding: utf-8

import argparse
import datetime as dt
import email.mime.application
import email.utils
import imaplib
import logging
import os
import ssl
import sys
import urllib.parse
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from getpass import getpass
from glob import glob
from smtplib import SMTP, SMTPAuthenticationError, SMTPException
from uuid import uuid4
import gspread
import requests
import yaml
from bs4 import BeautifulSoup
from certifi import where
from getSecrets import get_secret
from oauth2client.service_account import ServiceAccountCredentials
import googleDriveLib as gd
import csv
import re
from time import time, sleep
import spamcheck
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import errors
from googleapiclient.discovery import build
import base64


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


def fetch_data(url, token):
    """
    Fetch data from WIX API
    :param url: str
    :param token: str
    :return: dict
    """
    n = 3
    while n > 0:
        try:
            headers = {'Accept': 'application/json', 'auth': token}
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                log.error(f'Error fetching data: {resp.status_code}')
                return None

        except Exception as e:
            sleep(60)
            n -= 1
            log.error(f'Retrying fetching data')
            continue

    log.error('Error fetching data')
    return None


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

    if ('http') in filepath:
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

    def _get_client(self, client_id):
        """
        Retrieves details for a client using its ID.
        :param client_id:
        :return:
        """
        response = self._make_request("GET", f"parties/{client_id}")
        if response.status_code != 200:
            return None
        return response.json()

    def _create_client(self, row, indices):
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


def build_email(param, subject="",to="",cc="",bcc="",message="",images=None,attachments=None):
    # 1. Build Message
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = formataddr((param.sendername, param.sender))
    if param.cotisation:
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
    elif param.profile == 'cambristi':
        msg["Message-ID"] = email.utils.make_msgid(idstring=str(uuid4()), domain="gmail.com")

    # 2. Add Content & Attachments
    for img in [images] if isinstance(images, str) else (images or []):
        try:
            with open(img, "rb") as f:
                msg.attach(MIMEImage(f.read(), name=os.path.basename(img)))
        except FileNotFoundError:
            log.error(f"Could not find image '{img}'")

    for att in [attachments] if isinstance(attachments, str) else (attachments or []):
        with open(att, "rb") as f:
            content = f.read()
            if att.endswith(("htm", "html")):
                msg.attach(MIMEText(make_html_images_inline(att), "html"))
                message = ""
            elif att.endswith("txt"):
                msg.attach(MIMEText(content.decode()))
            elif att.endswith("pdf"):
                part = MIMEApplication(content, _subtype="pdf")
                part.add_header(
                    "Content-Disposition", "attachment", filename=os.path.basename(att)
                )
                msg.attach(part)

    if message and "<html" in message:
        msg.attach(MIMEText(message, "html"))
    else:
        msg.attach(MIMEText(message, "plain"))

    # 3. Send and Store
    recipients = [r.strip() for r in f"{to},{cc},{bcc}".split(",") if r.strip()]

    return msg, recipients


def get_gmail_service(param):
    """
    Initializes and returns a Gmail API service instance.

    This function is responsible for establishing a connection to the Gmail API
    using stored credentials or by performing an OAuth2 authentication flow. If
    credentials are not valid or expired, the function refreshes them or initiates
    a new authentication flow. The authenticated credentials are saved to a token
    file for future use. Finally, a Gmail API service instance is returned.

    TOKEN_FILE: A string representing the path to the file storing the
                       OAuth2 token.
    SCOPES: A list of strings specifying the OAuth2 scopes required by the
                   application.
    TOKEN_ID: A string identifying where to retrieve the access token from
                     the secret management service.
    CREDENTIALS_ID: A string identifying where to retrieve the OAuth2 client
                           credentials from the secret management service.
    :return: An instance of the Gmail API service client.
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


def send_gmail(service,message=None):

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    body = {"raw": encoded_message}
    try:
        return service.users().messages().send(userId='me', body=body).execute()
    except errors.HttpError as error:
        log.error(f'Error sending message: {error} to {message["To"]}')
        return None


def send_mail(param=None,message=None, recipients=None):
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


def _format_message(template, row, header):
    """Gère le remplacement des variables dans le corps du message."""
    try:
        msg_txt = re.sub(r"\${(.*)}", r"{row[header.index('\1')]}", template)
        return eval('f"""' + msg_txt + '"""')
    except (NameError, KeyError, IndexError, SyntaxError) as e:
        # log.error(f"Erreur d'évaluation du message : {e}")
        return template


def _sync(param):
    """
    Synchronize Arts Croisés members only database with Billit
    :param param:
    :return:
    """

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
            client_id = param.invoice._create_client(row, indices)
            if client_id == -1:
                log.error(f"Failed to create client for {row[indices['id']]}.")
                continue
            client = param.invoice._get_client(client_id)
            if not client:
                continue
            log.info(
                f"Client for {row[indices['first_name']]} {row[indices['last_name']] } sync'ed."
            )

    return "Done"


def _filter_artscroises(param, row, indices):
    is_active = row[indices["status"]] == "active"
    is_test_match = not param.test or "Test" in row[indices["group"]]
    is_selected = (
            not param.selected or row[indices["selected"]].lower() == "x"
    )
    has_email = bool(row[indices["email"]])
    return not (is_active and is_test_match and is_selected and has_email)


def _get_indices(header):
    return {h: i for i, h in enumerate(header)}


# ... existing code ...
def _process_membership_invoice(param, row, indices):
    """Gère la création de client, facture et le template de message pour les cotisations."""
    if not (row[indices["member"]] == "yes" and
            not row[indices["membershippaid"]] and
            row[indices["email"]]):
        return None

    client_id = param.invoice._create_client(row, indices)
    if client_id == -1:
        log.error(f"Failed to create client for {row[indices['id']]}.")
        return None

    client = param.invoice._get_client(client_id)
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


def generate_mailing(param):
    """Génère un envoi groupé basé sur une liste d'abonnés."""
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
            if param.cotisation:
                if not _process_membership_invoice(param, row, indices):
                    continue
            elif _filter_artscroises(param, row, indices):
                continue

            if param.verbose:
                print(", ".join(row))

            addressees.append(row[indices["email"]])
            recipient_count += 1

            if len(addressees) >= max_add:
                log.info(f"Envoi à {len(addressees)} destinataires (Index: {current_row_idx})")
                msg_body = _format_message(param.message, row, header)
                if not param.donotsend:
                    msg = build_email(param=param,subject=param.subject, message=msg_body,
                              bcc=",".join(addressees), attachments=param.file)
                    if param.profile == 'artscroises':
                        send_mail(param=param, message=msg)
                    elif param.profile == 'cambristi':
                        send_gmail(get_gmail_service(param), message= msg)

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


def setup_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--subject", help="Subject of the mail")
    parser.add_argument("-m", "--message", help="Text message of the mail", default="")
    parser.add_argument("file", nargs="*", help="files to attach to the mail")
    parser.add_argument("-t", "--test", action="store_true", help="test mode - send only to the tester group")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-x", "--doNotSend", action="store_true", help="Do not send any mail")
    parser.add_argument("-db", "--database", help="database path", default=None)
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


def process_attachments(args, config, folder="input"):
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


def process_artscroises(args):
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

    config = args.conf[args.profile]
    # config overrides secret data
    config = {**get_secret(config["MAILCONFIG"]), **config }
    if config is None:
        log.critical("No secret configuration found")
        sys.exit(1)
    files, service, google_drive_files = process_attachments(args, config)

    config.update(vars(args))
    param = Dict2Class(config)
    param.file = files
    if 'html' in files[0]:
        param.message = open(files[0], encoding="utf-8").read()
        param.file=files[1:]
    ret = generate_mailing(param)
    print(ret)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    args = setup_argparse()
    args.conf = yaml.safe_load(open("config.yml"))
    if args.profile == "artscroises":
        process_artscroises(args)
    elif args.profile == "cambristi":
        process_cambristi(args)

if __name__ == "__main__":
    main()
