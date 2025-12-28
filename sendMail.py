#!/usr/bin/env python
# coding: utf-8

import argparse
import datetime as dt
import email.mime.application
import email.utils
import imaplib
import json
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
from sympy.codegen.ast import continue_

import googleDriveLib as gd
import csv
import re
from time import time, sleep


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
        response = self._make_request("GET", f"parties/{client_id}")
        if response.status_code != 200:
            return None
        return response.json()

    def _create_client(self, row, indices):
        data = {
            "PartyID": row[indices["id"]],
            "Name": row[indices["first_name"]] + " " + row[indices["last_name"]],
            "Mobile": row[indices["mobile_phone"]],
            "Phone": row[indices["phone"]],
            "Email": row[indices["email"]],
            "ContactFirstName": row[indices["first_name"]],
            "ContactLastName": row[indices["last_name"]],
            "PartyType": "Customer",
        }
        response = self._make_request("POST", "parties", json=data)
        if response.status_code != 200:
            return -1
        return response.text

    def create_order(self, client=None, product_name="", price=0.0, qty=1):

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
    if param is None:
        log.critical("Missing configuration parameter")
        sys.exit(-1)

    # 1. Build Message
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = formataddr((param.sendername, param.sender))
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


def _get_invoice_body(param, row, indices, order):
    """Génère le corps HTML pour une relance de cotisation."""
    supplier = order["Supplier"]
    bank = supplier["BankAccounts"][0]
    acc_name = bank.get("Name", supplier["Name"])

    return f"""
        <html>
        Cher(e) {row[indices["first_name"]]} {row[indices["last_name"]]},<br/><br/>
        Voici le temps de renouveler votre cotisation {param.cotisation_year} à notre association Arts Croisés<br/><br/>
        Si vous souhaitez rester membre, veuillez payer le montant de {param.cotisation_amount} {bank['Currency']} sur le compte :<br/><br/>
        {acc_name}<br/>
        IBAN : {bank['IBAN']}<br/>
        Communication: {order["PaymentReference"]}<br/><br/>
        L'équipe Arts Croisés<br/>
        {supplier['Email']}
        </html>
    """


def _process_cotisation(param, row, indices):
    """Gère la création de facture et retourne le message mis à jour."""
    client_id = param.invoice._create_client(row, indices)
    if client_id == -1:
        log.error(f"Échec création client pour ID {row[indices['id']]}.")
        return None

    client = param.invoice._get_client(client_id)
    order = param.invoice.create_order(
        client=client,
        product_name=f"Cotisation {param.cotisation_year}",
        price=param.cotisation_amount,
        qty=1,
    )

    if order.get("OrderID") == -1:
        log.error(f"Échec facture pour ID {row[indices['id']]}.")
        return None

    return _get_invoice_body(param, row, indices, order)


def generate_mailing(param):
    """Génère un envoi groupé basé sur une liste d'abonnés."""
    try:
        max_add = 1 if param.cotisation else getattr(param, "max_addr_per_mail", 1)
        pause = 0 if param.cotisation else getattr(param, "pause", 0)
        max_mail = getattr(param, "max_mails_per_hour", 100)
    except AttributeError as e:
        log.critical(f"Configuration manquante : {e}")
        return "Error"

    reader, csvfile = _get_subscriber_reader(param)
    if not reader:
        return "Error"

    try:
        header = next(reader, None)
        if not header:
            return "Error"

        indices = {
            col: header.index(col)
            for col in [
                "email",
                "id",
                "first_name",
                "last_name",
                "status",
                "mailing_list",
                "selected",
                "member",
                "membershippaid",
            ]
        }

        current_row_idx = 1
        # Skip rows
        if param.from_index:
            for _ in range(2, int(param.from_index)):
                next(reader, None)
                current_row_idx += 1

        addressees, recipient_count, batch_count = [], 0, 0
        start_time = time()

        for row in reader:
            current_row_idx += 1
            if param.to_index and current_row_idx > int(param.to_index):
                break

            if param.cotisation:
                is_eligible = (
                    row[indices["member"]] == "yes"
                    and not row[indices["membershippaid"]]
                    and row[indices["email"]]
                )
                if not is_eligible:
                    continue

                msg_content = _process_cotisation(param, row, indices)
                if not msg_content:
                    continue
                param.message = msg_content
            else:
                is_active = row[indices["status"]] == "active"
                is_test = not param.test or "Test" in row[indices["mailing_list"]]
                is_selected = (
                    not param.selected or row[indices["selected"]].lower() == "x"
                )
                if not (
                    is_active and is_test and is_selected and row[indices["email"]]
                ):
                    continue

            addressees.append(row[indices["email"]])
            recipient_count += 1

            if len(addressees) >= max_add:
                log.info(f"Envoi lot (Index: {current_row_idx})")
                msg_body = (
                    _format_message(param.message, row, header)
                    if not param.cotisation
                    else param.message
                )

                if not param.donotsend:
                    send_mail(
                        param=param,
                        subject=param.subject,
                        message=msg_body,
                        bcc=",".join(addressees),
                        attachments=param.file,
                    )

                addressees, batch_count = [], batch_count + 1
                sleep(pause)
                if recipient_count % max_mail == 0:
                    log.info("Pause horaire...")
                    sleep(3600)

        if addressees and not param.donotsend:
            send_mail(
                param=param,
                subject=param.subject,
                message=param.message,
                bcc=",".join(addressees),
                attachments=param.file,
            )
            batch_count += 1

        log.info(f"Terminé: {recipient_count} traités en {batch_count} envois.")
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
    if args.database:
        config["db"] = args.database

    param = Dict2Class(config)
    param.file = files  # Mise à jour explicite des fichiers filtrés

    if args.cotisation:
        param.invoice = Invoice(prod=not args.test)
        param.subject = f"Arts Croisés - Cotisation {param.cotisation_year}"

    if generate_mailing(param) == "OK" and not args.test:
        for f in google_drive_files:
            gd.rename_file(service, f["id"], f"published_{f['name']}")
        for f in glob("input/*.*"):
            os.remove(f)


if __name__ == "__main__":
    main()
