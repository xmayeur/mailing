.. sendMail documentation master file, created by
   sphinx-quickstart on Sat Jan 31 22:04:39 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to sendMail's documentation!
====================================

sendMail is a comprehensive Python utility for handling logging, Google Sheets integration,
file manipulation, and email operations. It includes utilities for processing HTML content,
and sending bulk emails with advanced
features like inline images, attachments, and rate limiting.

Features
--------

* **Email Operations**: Send emails via SMTP or Gmail API with support for HTML content, inline images, and attachments
* **Google Sheets Integration**: Read and write data from Google Sheets for subscriber management
* **HTML Processing**: Process HTML files with automatic image optimization and CID embedding
* **Bulk Mailing**: Send mass emails with rate limiting, batching, and filtering capabilities
* **Google Drive Integration**: Download and manage files from Google Drive
* **Filter Validation**: Real-time YAML filter syntax checking and field name validation
* **Filter Matching**: Apply filters to subscriber rows for preview and testing

Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   modules


Installation
============

To install the required dependencies::

    pip install -r requirements.txt

The main dependencies include:

* gspread - Google Sheets API
* google-auth, google-auth-oauthlib, google-api-python-client - Google authentication
* requests - HTTP library
* Pillow - Image processing
* BeautifulSoup4 - HTML parsing
* PyYAML - Configuration files
* sphinx-rtd-theme - Documentation theme

Quick Start
===========

Basic usage example::

    from sendMail import build_email, send_mail, Dict2Class

    # Configure parameters
    config = {
        'sender': 'your-email@example.com',
        'sendername': 'Your Name',
        'smtp_host': 'smtp.example.com',
        'smtp_port': 587,
        'username': 'your-email@example.com',
        'password': 'your-password'
    }
    param = Dict2Class(config)

    # Build and send email
    msg, recipients = build_email(
        param=param,
        subject='Test Email',
        to='recipient@example.com',
        message='Hello, World!'
    )
    send_mail(param=param, message=msg, recipients=recipients)

Configuration
=============

The application uses a ``config.yml`` file for profile-based configuration and
a secrets manager (via ``getSecrets``) for sensitive credentials. See the module
documentation for detailed configuration options.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
