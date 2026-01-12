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
from bs4 import BeautifulSoup
from certifi import where
from getSecrets import get_secret
from oauth2client.service_account import ServiceAccountCredentials
import googleDriveLib as gd
import csv
import re
from time import time, sleep
import spamcheck


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

SHEETID = "artscroisesDBmembreID"
SA = "artscroisesServiceAccount"


def openGoogleDBMembersSheet(sa=SA, id=SHEETID):
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


def send_mail(
    param=None,
    subject="",
    to="",
    cc="",
    bcc="",
    message="",
    images=None,
    attachments=None,
):
    """
    Send an email message using SMTP.
    :param param:
    :param subject:
    :param to:
    :param cc:
    :param bcc:
    :param message:
    :param images:
    :param attachments:
    :return:
    """
    if param is None:
        log.critical("Missing configuration parameter")
        sys.exit(-1)

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
    msg["Message-ID"] = email.utils.make_msgid(
        idstring=str(uuid4()), domain="artscroises.be"
    )

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

    if message and "<html>" in message:
        msg.attach(MIMEText(message, "html"))
    else:
        msg.attach(MIMEText(message, "plain"))

    # 3. Send and Store
    recipients = [r.strip() for r in f"{to},{cc},{bcc}".split(",") if r.strip()]

    if param.check_spam:
        spam_result = spamcheck.check(msg.as_string(), report=True)
        print(spam_result["score"])
        if spam_result["score"] > 0.5:
            print(spam_result["report"])
            log.critical("Message rejected by spam filter")
            return

    if param.verbose:
        log.info(f"Sending email to {recipients}")
    success = False
    for attempt in range(2):
        conn = _get_smtp_connection(param)
        if conn:
            try:
                conn.sendmail(msg["From"], recipients, msg.as_string())
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
        _save_to_sent(param, msg)


def _get_subscriber_reader(param):
    """Extrait la logique de lecture de la source de données."""
    if param.db is None:
        wb = openGoogleDBMembersSheet()
        return iter(readAllSheet(wb)), None

    try:
        csvfile = open(param.db, "r", newline="", encoding="utf-8-sig")
        return csv.reader(csvfile, delimiter=",", quotechar='"'), csvfile
    except FileNotFoundError:
        log.critical(f"Fichier introuvable : '{param.db}'")
        return None, None


def _format_message(template, row, header):
    """Gère le remplacement des variables dans le corps du message."""
    try:
        msg_txt = re.sub(r"\${(.*)}", r"{row[header.index('\1')]}", template)
        return eval('f"""' + msg_txt + '"""')
    except (NameError, KeyError, IndexError) as e:
        log.error(f"Erreur d'évaluation du message : {e}")
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


def generate_mailing(param):
    """Génère un envoi groupé basé sur une liste d'abonnés."""
    try:
        if param.cotisation:
            max_add = 1
            pause = 0
        else:
            max_add = param.max_addr_per_mail
            pause = param.pause
        max_mail = param.max_mails_per_hour
    except AttributeError as e:
        log.critical(f"Clé de configuration manquante : {e}")
        return "Error"

    reader, csvfile = _get_subscriber_reader(param)
    if reader is None:
        return "Error"

    try:
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
            "membershippaid": header.index("membershippaid"),
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

        addressees = []
        recipient_count = 0
        mail_batch_count = 0
        start_time = time()

        for row in reader:
            current_row_idx += 1
            if param.to_index and current_row_idx > int(param.to_index):
                break

            # Filtres de sélection - skip if false
            if param.cotisation:
                is_member = row[indices["member"]] == "yes"
                not_paid = (
                    row[indices["membershippaid"]] is None
                    or row[indices["membershippaid"]] == ""
                )
                has_email = bool(row[indices["email"]])
                if not (is_member and not_paid and has_email):
                    continue

                # Create or update client
                client_id = param.invoice._create_client(row, indices)
                if client_id == -1:
                    log.error(f"Failed to create client for {row[indices['id']]}.")
                    continue
                client = param.invoice._get_client(client_id)
                if not client:
                    continue
                # create an invoice and get the order id

                order = param.invoice.create_order(
                    client=client,
                    product_name=f"Cotisation Arts Croisés {param.cotisation_year}",
                    price=param.cotisation_amount,
                    qty=1,
                )
                if order["OrderID"] == -1:
                    log.error(f"Failed to create invoice for {row[indices['id']]}.")
                    continue

                # Build body message
                ref = order["PaymentReference"]
                qr_url = order["PaymentLinks"][0]["QRImageUrl"]
                supplier = order["Supplier"]["Name"]
                iban = order["Supplier"]["BankAccounts"][0]["IBAN"]
                cur = order["Supplier"]["BankAccounts"][0]["Currency"]
                acc_name = (
                    order["Supplier"]["BankAccounts"][0]["Name"]
                    if "Name" in order["Supplier"]["BankAccounts"][0]
                    else supplier
                )
                email = order["Supplier"]["Email"]

                param.message = f"""
                    <html>
                    Chère/cher {row[indices["first_name"]]} {row[indices["last_name"]]},<br/><br/>
                    Nous vous souhaitons tous nos meilleurs voeux pour {param.cotisation_year}.<br/><br/>
                    Voici le temps de renouveler votre cotisation en temps que membre de notre association Arts Croisés.<br/><br/>
                    Si vous souhaitez rester membre, par sympathie ou pour pouvoir participer à nos activités, veuillez payer le montant 
                    de {param.cotisation_amount} {cur} par personne sur le compte bancaire suivant :<br/><br/>
                    {acc_name}<br/>
                    IBAN : {iban}<br/>
                    Communication: {ref}<br/><br/>
                    
                    Si vous ne souhaitez plus être membre, nous vous saurons gré de bien vouloir répondre à cet email et nous le faire savoir, de façon à ne plus vous contacter l'année prochaine.
                    <br/><br/>
                    
                    Cordialement,<br/>
                    L'équipe Arts Croisés<br/>
                    {email}
                    
                    </html>

                """
                pass

            else:
                is_active = row[indices["status"]] == "active"
                is_test_match = not param.test or "Test" in row[indices["group"]]
                is_selected = (
                    not param.selected or row[indices["selected"]].lower() == "x"
                )
                has_email = bool(row[indices["email"]])
                if not (is_active and is_test_match and is_selected and has_email):
                    continue

            if param.verbose:
                print(", ".join(row))

            addressees.append(row[indices["email"]])
            recipient_count += 1

            # Envoi par lots
            if len(addressees) >= max_add:
                log.info(
                    f"Envoi à {len(addressees)} destinataires (Index: {current_row_idx})"
                )

                msg_body = _format_message(param.message, row, header)
                if not param.donotsend:
                    send_mail(
                        param=param,
                        subject=param.subject,
                        message=msg_body,
                        bcc=",".join(addressees),
                        attachments=param.file,
                    )

                addressees = []
                mail_batch_count += 1
                sleep(pause)

                if recipient_count % max_mail == 0:
                    log.info("Limite horaire atteinte. Pause d'une heure...")
                    sleep(3600)

        # Envoi du reliquat
        if addressees:
            log.info(f"Envoi final à {len(addressees)} destinataires.")
            if not param.donotsend:
                send_mail(
                    param=param,
                    subject=param.subject,
                    message=param.message,
                    bcc=",".join(addressees),
                    attachments=param.file,
                )
            mail_batch_count += 1

        elapsed = time() - start_time
        log.info(
            f"Terminé. {recipient_count} adresses traitées en {mail_batch_count} envois ({int(elapsed)}s)"
        )
        return "OK"

    finally:
        if csvfile:
            csvfile.close()


def setup_argparse(config):
    parser = argparse.ArgumentParser()
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
    parser.add_argument("-db", "--database", help="database path", default=None)
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
    parser.add_argument(
        "--cotisation", help="Generate cotisation reminder mail", action="store_true"
    )
    parser.add_argument(
        "-y", "--cotisation_year", help="Cotisation year", default="2026"
    )
    parser.add_argument(
        "-amt", "--cotisation_amount", help="Cotisation amount", default="15.00"
    )
    parser.add_argument(
        "-mh",
        "--max-mails-per-hour",
        default=int(config["max_mails_per_hour"]),
        type=int,
    )
    parser.add_argument(
        "-na", "--max_addr_per_mail", default=int(config["max_addr_per_mail"]), type=int
    )
    parser.add_argument("-p", "--pause", default=int(config["pause"]), type=int)
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--check_spam", action="store_true")
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
        service = gd.connect_google_driver()
        result = gd.get_files(service, folder_id=config["mailing_folder"])
        if result and "files" in result:
            google_drive_files = result["files"]
            gd.download_file(service, google_drive_files, folder)
        files = [f for f in glob(f"{folder}/*.*") if "published" not in f]

    return files, service, google_drive_files


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = get_secret("artscroisesmailing")
    if config is None:
        log.critical("No secret configuration found")
        sys.exit(1)

    args = setup_argparse(config)
    files, service, google_drive_files = process_attachments(args, config)

    body_txt = args.body if args.body else ""
    newsletter_name = ""

    # Analyse des fichiers pour le sujet et le corps
    for f in files:
        basename = os.path.basename(f)
        ext = basename.split(".")[-1].lower()
        name_part = basename.split(".")[0]

        if ext in ["pdf", "html"]:
            if not args.subject:
                args.subject = name_part
            if "letter" in name_part.lower() or "lettre" in name_part.lower():
                newsletter_name = basename
            if ext == "html":
                args.message = "html"
        elif "body.txt" in basename:
            body_txt = open(f, encoding="utf-8").read()
            args.message = body_txt
            files.remove(f)

    if not args.message:
        args.message = f"\nChers amies et amis des Arts Croisés,\n{body_txt}\nVeuillez trouver en pièce jointe notre newsletter {newsletter_name}.\nBonne lecture!\n\nL'équipe Arts Croisés, asbl\n..."

    if args.wait:
        log.info(f"Start sending in {args.wait} minutes")
        for i in range(args.wait):
            print(f"Sleeping for {args.wait - i} minutes      \r", end="", flush=True)
            sleep(60)

    config.update(vars(args))
    if "password" not in config:
        config["password"] = getpass("Enter mail user's password")

    config["db"] = args.database if args.database else None

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


if __name__ == "__main__":
    main()
