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
from smtplib import SMTP_SSL, SMTPAuthenticationError, SMTP
from time import time, sleep
import yaml
from bs4 import BeautifulSoup
from getSecrets import get_secret, get_user_pwd

import gspread
from oauth2client.service_account import ServiceAccountCredentials


def init_log():
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


log = init_log()


class Dict2Class(object):
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
            img.attrs["src"] = "data:%s;base64,%s" % (mimetype, file_to_base64(img_path))
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
    msg["Message-ID"] = email.utils.make_msgid(domain="artscroises.be")

    if message != "":
        msg.attach(MIMEText(message, "plain"))

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

    # the message is now being sent
    try:
        ret = conn.sendmail(
            msg["From"],
            addr.split(","),
            msg.as_string(),
        )

        # a copy of the message in kept in the sent folder
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
        log.error(f"SMTP error: {e}")
    conn.quit()


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
        sys.exit(-1)

    n_add = 0
    n_mail = 0
    addressees = []
    nrow = 1

    start = time()

    # Read the subscriber's db
    try:
        with open(db, "r", newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",", quotechar='"')

            # Get the header
            header = next(reader, None)
            if header[0][:1] == '\ufeff':
                header[0] = header[0][1:]
            email_idx = header.index('Email')
            group_idx = header.index('Groups')
            selected_idx = header.index('Selected')
            opt_out = header.index('Email status')

            # skip records before starting index if required
            if param.from_index:
                log.info(f"Starting (re-)sending mails from index {param.from_index}")
                for nrow in range(2, int(param.from_index)):
                    next(reader, None)

            # loop all other records
            for row in reader:
                nrow += 1

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
                            message=param.message,
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

    except FileNotFoundError:
        log.critical(f"No such file or directory: '{db}'")
        sys.exit(-1)

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
        f"Done. Processed {n_add} addresses in {n_mail+1} email(s) in {int(elapsed)+1} seconds"
    )


def main():
    # Set the right directory
    abspath = os.path.abspath(__file__)
    os.chdir(os.path.dirname(abspath))

    # Get arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--subject", help="Subject of the mail", required=True)
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
        "-w",
        "--wait",
        help="Wait x minutes before restarting sending mail",
        default=None,
    )
    parser.add_argument(
        "--selected", action="store_true", help="Only send selected mail", default=False
    )
    args = parser.parse_args()

    if args.verbose:
        print(args.file)

    # test if attachment files exist
    if args.file:
        for f in args.file:
            if not os.path.isfile(f):
                log.critical(f"File not found: {f}")
                sys.exit(-1)

    if args.test:
        log.info(f"Testing mode - send only to the Test Group subscribers")

    if args.doNotSend:
        log.info(f"No sending mode")

    try:
        # config = yaml.safe_load(open("config.yml", "r"))
        config = get_secret('artscroisesmailing')
    except FileNotFoundError:
        log.critical(f"Config file 'config.yml' not found vault not available")
        sys.exit(-1)

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

    # delay sending if required
    if args.wait:
        log.info(f"Start sending in {args.wait} minutes")
        for i in range(0, int(args.wait)):
            print(f"Sleeping for {60-i} minutes      \r", end="", flush=True)
            sleep(int(60))

    # merge config and argument list into a single object
    config.update(vars(args))
    # convert dict into class - all keys are converted in lower case
    param = Dict2Class(config)
    generate_mailing(param)


if __name__ == "__main__":
    main()
