#!/usr/bin/env python
# coding: utf-8

import argparse
import csv
import email.mime.application
import imaplib
import logging
import os
import ssl
import sys
import urllib.parse
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from getpass import getpass
from glob import glob
from smtplib import SMTPAuthenticationError, SMTP, SMTPException
from time import time, sleep
import gspread
from bs4 import BeautifulSoup
from getSecrets import get_secret, get_user_pwd
from oauth2client.service_account import ServiceAccountCredentials
import googleDriveLib as gd
from uuid import uuid4


def init_log(log_file=None):
    """
    Initialize the logging module to the sdterr output and to the log file
    :param log_file: the log file path
    :return: a logger object
    """
    # if os.path.exists("sendMail.log"):
    #     os.remove("sendMail.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # stdout_handler = logging.StreamHandler(sys.stdout)
    # stdout_handler.setLevel(logging.DEBUG)
    # stdout_handler.setFormatter(formatter)
    # logger.addHandler(stdout_handler)

    if log_file is not None:
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
    if sheet_name == "":
        ws = wb.sheet1
    else:
        ws = wb.get_sheet_by_name(sheet_name)
    return ws.get_all_values()


class Dict2Class(object):
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
    soup = BeautifulSoup(open(in_filepath, "r"), "html.parser")
    for img in soup.find_all("img"):
        img_path = urllib.parse.unquote(os.path.join(basepath, img.attrs["src"]))
        mimetype = guess_type(img_path)
        if ";base64," not in img_path:
            img.attrs["src"] = "data:%s;base64,%s" % (
                mimetype,
                file_to_base64(img_path),
            )
        else:
            # TODO Change by a regex to ensure the string start with data:.*?;base64...
            img.attrs["src"] = img_path[6:]

    if out_filepath is not None:
        with open(out_filepath, "w") as of:
            of.write(str(soup))
    return str(soup)


def send_mail(
    param=None,
    subject: str = "",
    to: str = "",
    cc: str = "",
    bcc: str = "",
    message: str = "",
    images=None,
    attachments=None,
):
    """

    :param param: configuration dictionary with email settings
    :param subject: mail subject
    :param to: comma-separated to recipient list
    :param cc: comma-separated hidden recipient
    :param bcc: comma-separated hidden recipient
    :param message: text body message
    :param images: list of images to attach
    :param attachments: attachment list. .txt and .html will be managed as message parts, not attachment
    :return:
    """

    if param is None:
        log.critical("Missing configuration parameter")
        sys.exit(-1)

    try:
        # get configuration parameters
        host = param.smtp_host  # config["HOST"]
        port = param.smtp_port  # config["PORT"]
        username = param.username  # config["USERNAME"]
        sender = param.sender  # config["SENDER"]
        sender_name = param.sendername  # config["SENDERNAME"]
        password = param.password  # config["PASSWORD"]
        imap_host = param.imap_host  # config["IMAP_HOST"]
        imap_port = param.imap_port  # config["IMAP_PORT"]
        sent_folder = param.sent_folder  # config["SENT_FOLDER"]

    except AttributeError as e:
        log.critical(f"Missing or invalid key '{e}' in config file")
        sys.exit(-1)

    # Initiate secured SMTP protocol
    context = ssl.create_default_context()
    conn = SMTP(host, port)
    conn.starttls(context=context)
    conn.ehlo()
    try:
        conn.login(username, password)
    except SMTPAuthenticationError:
        log.critical("Invalid SMTP credentials")
        sys.exit(-1)

    # create message structure
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, sender))
    addr = ""
    msg["To"] = to + "," + formataddr((sender_name, sender))
    addr += to
    if cc != "":
        msg["Cc"] = cc
        addr += cc
    if bcc != "":
        msg["Bcc"] = bcc
        addr += bcc
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(
        idstring=str(uuid4()), domain="artscroises.be"
    )

    # Attach inline images if any
    if images is not None:
        if type(images) is not list:
            images = [images]
        for img in images:
            try:
                img_data = open(img, "rb").read()  # read the image binary data
                # attach the image data to MIMEMultipart using MIMEImage, we add
                # the given filename use os.basename
                msg.attach(MIMEImage(img_data, name=os.path.basename(img)))
            except FileNotFoundError:
                log.error(f"Could not find file '{img}' - skipping attachment")

    # Manage attachments
    if attachments is not None:
        if type(attachments) is not list:
            attachments = [attachments]

        for att in attachments:
            with open(att, "rb") as fd:
                # HTML and text attachments are embedded in the message body, not attached
                if att[-3:] == "htm" or att[-4:] == "html":
                    # images referred in the html code are embedded into the html code, no more as separate files
                    html = make_html_images_inline(att, "out.html")
                    part = MIMEText(html, "html")
                    message = ""
                elif att[-3:] == "txt":
                    part = MIMEText(fd.read().decode())
                # PDF files are managed as attached documents
                elif att[-3:] == "pdf":
                    part = email.mime.application.MIMEApplication(
                        fd.read(), _subtype="pdf"
                    )
                    part.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=os.path.basename(att),
                    )
            # All parts are added to the message structure
            msg.attach(part)
    # if param.verbose:
    #     print(msg.as_string())

    # the message is now being sent
    if message != "":
        msg.attach(MIMEText(message, "plain"))

    success = True
    ret = {}
    try:
        ret = conn.sendmail(
            msg["From"],
            addr.split(","),
            msg.as_string(),
        )
    except SMTPException as e:
        # retry
        sleep(10)
        conn = SMTP(host, port)
        conn.starttls(context=context)
        conn.ehlo()
        try:
            conn.login(username, password)
        except SMTPAuthenticationError:
            log.critical("Invalid SMTP credentials")
            sys.exit(-1)
        try:
            ret = conn.sendmail(
                msg["From"],
                addr.split(","),
                msg.as_string(),
            )
        except SMTPException as e:
            log.critical(f"SMTP error after two tries: {e}")
            log.info(ret)
            success = False

    if param.verbose:
        log.info("sent")

    conn.quit()
    if success:
        # a copy of the message in kept in the sent folder
        try:
            imap = imaplib.IMAP4_SSL(imap_host, imap_port)
            imap.login(username, password)
            imap.append(
                sent_folder,
                "\\Seen",
                imaplib.Time2Internaldate(time()),
                msg.as_string().encode("utf8"),
            )
            imap.logout()
        except Exception as e:
            log.warning(f"Retrying copying sent message in sent folder{e}")
            try:
                imap = imaplib.IMAP4_SSL(imap_host, imap_port)
                imap.login(username, password)
                imap.append(
                    sent_folder,
                    "\\Seen",
                    imaplib.Time2Internaldate(time()),
                    msg.as_string().encode("utf8"),
                )
                imap.logout()
            except Exception as e:
                log.error(f"Error copying sent message in sent folder{e}")

        if param.verbose:
            log.info("stored in sent folder")


def generate_mailing(param):
    """
    Generate a mass mailing based on a CVS file of subscribers
    :param param: configuration parameters
    :return:
    """

    try:
        db = param.db  # config["DB"]
        max_add = param.max_addr_per_mail  # config["MAX_ADDR_PER_MAIL"]
        max_mail = param.max_mails_per_hour  # config["MAX_MAILS_PER_HOUR"]
        pause = param.pause  # config["PAUSE"]
    except AttributeError as e:
        log.critical(f"Missing or invalid configuration key {e}")
        return "Error"

    n_add = 0
    n_mail = 0
    addressees = []
    nrow = 1

    start = time()
    reader = iter([])
    if db is None:
        wb = openGoogleDBMembersSheet()
        reader = iter(readAllSheet(wb))
    else:
        # Read the subscriber's db
        try:
            csvfile = open(db, "r", newline="")
            reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        except FileNotFoundError:
            log.critical(f"No such file or directory: '{db}'")
            return "Error"

    # Get the header
    header = next(reader, None)
    if header[0][:1] == "\ufeff":
        header[0] = header[0][1:]
    email_idx = header.index("email")
    group_idx = header.index("mailing_list")
    selected_idx = header.index("selected")
    opt_out = header.index("status")
    user_idx = header.index("id")

    # skip records before starting index if required
    if param.from_index:
        log.info(f"Starting (re-)sending mails from index {param.from_index}")
        for nrow in range(2, int(param.from_index)):
            next(reader, None)

    # loop all other records
    for row in reader:
        nrow += 1
        if param.to_index is not None and nrow > int(param.to_index):
            break
        # skip inactive records and opt-out ones

        if row[opt_out] != "active":
            continue

        # skip records not belonging to the test group if requested
        if param.test and "Test" not in row[group_idx]:
            continue

        if param.selected and row[selected_idx].lower() != "x":
            continue

        if param.verbose:
            print("', ".join(row))

        if row[email_idx] == "" or row[email_idx] is None:
            continue

        user_id = row[user_idx]
        # create a group of 'max_add' addresses and send to all of them in BCC
        addressees.append(row[email_idx])
        n_add += 1
        if n_add % max_add == 0:
            if param.verbose:
                print("_" * 80)
                print(", ".join(addressees))
                print("_" * 80)
            log.info(
                f'Sending {n_add} addressees, up to index {nrow}: {", ".join(addressees)}'
            )
            if not param.donotsend:
                send_mail(
                    param=param,
                    subject=param.subject,
                    message=eval('f"""' + param.message + '"""'),
                    bcc=",".join(addressees),
                    attachments=param.file,
                )

            addressees = []
            n_mail += 1
            sleep(pause)

        # Control the limit of allowed mails to send as per email provider rules
        if n_add % max_mail == 0:
            log.info("Sleeping for 1 hour...")
            if param.verbose:
                print("+" * 80)
            sleep(3600)

    # Send the remaining mails
    if len(addressees) != 0:
        log.info(
            f'Sending {n_add} addressees, up to index {nrow}: {", ".join(addressees)}'
        )
        if not param.donotsend:
            send_mail(
                param=param,
                subject=param.subject,
                message=param.message,
                bcc=",".join(addressees),
                attachments=param.file,
            )
    elapsed = time() - start
    log.info(
        f"Done. Processed {n_add} addresses in {n_mail + 1} email(s) in {int(elapsed) + 1} seconds"
    )
    return "OK"


def main():
    # Set the right directory
    abspath = os.path.abspath(__file__)
    os.chdir(os.path.dirname(abspath))

    # open secret config object
    config = get_secret("artscroisesmailing")
    if config is None:
        log.critical(f"No secret configuration found")
        sys.exit(1)

    # Get arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--subject", help="Subject of the mail", required=False)
    parser.add_argument("-m", "--message", help="Text message of the mail", default="")
    parser.add_argument(
        "file",
        nargs="*",
        # type=argparse.FileType("r"),
        help="files to attach to the mail",
    )
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="test mode - send only to the tester group",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true",
    )
    parser.add_argument(
        "-x",
        "--doNotSend",
        action="store_true",
        help="Do not send any mail",
    )
    # parser.add_argument("-p", "--password", help="password for the mail", default=None)
    parser.add_argument("-db", "--database", help="database path", default=None)
    parser.add_argument(
        "-f", "--from_index", help="Starting index in the database", default=None
    )
    parser.add_argument(
        "-to", "--to_index", help="Stopping index in the database", default=None
    )
    parser.add_argument(
        "-w",
        "--wait",
        help="Wait x minutes before restarting sending mail",
        default=None,
    )
    parser.add_argument(
        "--selected", action="store_true", help="Only send selected mail", default=False
    )

    parser.add_argument("--body")

    parser.add_argument(
        "-mh",
        "--max-mails-per-hour",
        default=int(config["max_mails_per_hour"]),
        type=int,
    )
    parser.add_argument(
        "-na", "--max-addr-per-mail", default=int(config["max_addr_per_mail"]), type=int
    )
    parser.add_argument("-p", "--pause", default=int(config["pause"]), type=int)

    args = parser.parse_args()

    if args.verbose:
        print(args.file)

    body_txt = ""
    if args.body:
        body_txt = args.body

    # test if attachment files exist
    gd_files = []
    service = None
    folder = "input"
    # if file paths are passes as argument, get them & test existence
    files = args.file
    if args.file:
        for f in args.file:
            if not os.path.isfile(f):
                log.critical(f"File not found: {f}")
                sys.exit(-1)
    else:
        # alternatively, download files from google drive mailing folder
        files = glob(f"{folder}/*.*")
        for f in files:
            os.remove(f)
        service = gd.connect_google_driver()
        gd_files = gd.get_files(service, folder_id=config["mailing_folder"])
        if len(gd_files) > 0:
            gd_files = gd_files["files"]
            gd.download_file(service, gd_files, "input")

        # Attach files to the mail
        newsletter_name = ""
        files = glob(f"{folder}/*.*")
        files = [f for f in files if not "published" in f]
        # if len(files) == 0:
        #    log.critical(f"No files found to attach to the mail - non content!")
        #    sys.exit(-1)

    # Derive the message subject
    for f in files:
        fb = os.path.basename(f)
        if (
            fb.split(".")[-1] == "pdf" or fb.split(".")[-1] == "html"
        ) and not args.subject:
            fn = fb.split(".")[0]
            if "letter" in fn.lower() or "lettre" in fn.lower():
                args.subject = fn
                newsletter_name = fb
        elif "body.txt" in fb:
            body_txt = open(f, encoding="utf-8").read()
            files.remove(f)

    args.file = files

    # define a default message body
    if not args.message:
        args.message = f"""
Chers amies et amis des Arts Croisés,

{body_txt}
Veuillez trouvez en pièce jointe notre newsletter {newsletter_name}.
Bonne lecture!




L'équipe Arts Croisés, asbl

PS: Veuillez utiliser notre adresse info@artscroises.be pour toute correspondance et ne pas répondre à ce mail
Pour vous désinscrire, envoyer un mail avec comme sujet "Se désinscrire"
        """

    if args.test:
        log.info(f"Testing mode - send only to the Test Group subscribers")

    if args.doNotSend:
        log.info(f"No sending mode")

    # # Get configuration yaml - here an example
    #
    # HOST: smtp.mail.ovh.net
    # PORT: 465
    # IMAP_HOST: imap.mail.ovh.net
    # IMAP_PORT: 993
    # USERNAME: info@artscroises.be
    # PASSWORD
    # SENDER: info@artscroises.be
    # SENDERNAME: Arts Croisés asbl
    # DB: data/Subscribers.csv
    # MAX_ADDR_PER_MAIL: 50
    # MAX_MAILS_PER_HOUR: 200
    # PAUSE: 10
    # SENT_FOLDER: INBOX.Mailing
    #
    # The following parameters may be overwritten by passed arguments
    # SUBJECT: ""
    # MESSAGE: ""
    # TEST: False
    # VERBOSE: False
    # DONOTSEND: False
    # FROM_INDEX: 0
    # WAIT: 0
    # SELECTED: False

    if "password" not in config:
        if args.password:
            pwd = args.password
        else:
            pwd = getpass("Enter mail user's password")
        config["password"] = pwd

    # Override default database path
    if args.database:
        config["db"] = args.database
    else:
        config["db"] = None

    # delay sending if required
    if args.wait:
        log.info(f"Start sending in {args.wait} minutes")
        for i in range(0, int(args.wait)):
            print(f"Sleeping for {60 - i} minutes      \r", end="", flush=True)
            sleep(int(60))

    # merge config and argument list into a single object
    config.update(vars(args))

    # convert dict into class - all keys are converted in lower case
    param = Dict2Class(config)
    # Generate the mailing mail and send it to all 'active' recipients from the database
    ret = generate_mailing(param)
    if ret == "OK" and not args.test:
        for f in gd_files:
            gd.rename_file(service, f["id"], f"published_{f['name']}")
        files = glob(f"{folder}/*.*")
        for f in files:
            os.remove(f)


if __name__ == "__main__":
    main()
