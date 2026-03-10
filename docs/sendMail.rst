sendMail module
===============

Overview
--------

The **sendMail** module is a comprehensive email campaign management system that supports:

* **Bulk email sending** with rate limiting and batch processing
* **Multiple email profiles** (Arts Croisés, Cambristi)
* **Google Sheets integration** for subscriber management
* **Google Drive integration** for attachment handling
* **HTML email templates** with inline image support
* **Membership management** and cotisation reminders
* **SMTP and Gmail API** support for sending emails
* **Flexible filtering** based on subscriber attributes

The module is designed for organizations managing mailing lists, newsletters, and membership communications.

.. automodule:: sendMail
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Classes
-------

Dict2Class
^^^^^^^^^^

.. autoclass:: sendMail.Dict2Class
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

Functions
---------

Logging & Initialization
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.init_log
   :no-index:

Google Sheets Functions
^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.openGoogleDBMembersSheet
   :no-index:

.. autofunction:: sendMail.readAllSheet
   :no-index:

File Utilities
^^^^^^^^^^^^^^

.. autofunction:: sendMail.guess_type
   :no-index:
.. autofunction:: sendMail.file_to_base64
   :no-index:

HTML Processing
^^^^^^^^^^^^^^^

.. autofunction:: sendMail.prepare_html_for_cid
   :no-index:
.. autofunction:: sendMail.prepare_html_and_get_images
   :no-index:
.. autofunction:: sendMail.md2html
   :no-index:


Email Building & Sending
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.build_email
   :no-index:
.. autofunction:: sendMail.send_mail
   :no-index:
.. autofunction:: sendMail.send_gmail
   :no-index:
.. autofunction:: sendMail.get_gmail_service
   :no-index:

Message Processing
^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.generate_mailing
   :no-index:
.. autofunction:: sendMail.process_attachments
   :no-index:

SMTP & IMAP
^^^^^^^^^^^

.. autofunction:: sendMail.get_smtp_connection
   :no-index:
.. autofunction:: sendMail.save_to_sent
   :no-index:

Configuration & Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.check_mandatory_param
   :no-index:

Filtering & Data Processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.get_subscriber_reader
   :no-index:
.. autofunction:: sendMail.get_indices
   :no-index:
.. autofunction:: sendMail.format_message
   :no-index:
.. autofunction:: sendMail.filter
   :no-index:


Profile Processing
^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.process_profile
   :no-index:


Command-line Interface
^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: sendMail.setup_argparse
   :no-index:
.. autofunction:: sendMail.main
   :no-index:

Command-Line Arguments
----------------------

The sendMail module can be invoked from the command line with the following arguments:

Basic Options
^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Argument
     - Type
     - Description
   * - ``--profile``
     - string
     - **Required**. Mail profile to use (``artscroises`` or ``cambristi``)
   * - ``-s, --subject``
     - string
     - Subject of the email
   * - ``-m, --message``
     - string
     - Text message body of the email
   * - ``file``
     - list
     - Files to attach to the email (positional argument, can specify multiple files)

Test & Debug Options
^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Argument
     - Type
     - Description
   * - ``-t, --test``
     - flag
     - Test mode - send only to the tester group
   * - ``-v, --verbose``
     - flag
     - Increase output verbosity
   * - ``-x, --doNotSend``
     - flag
     - Do not send any mail (dry run)

Database Options
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Argument
     - Type
     - Description
   * - ``-db, --database``
     - string
     - Path to CSV database file (alternative to Google Sheets)
   * - ``-f, --from_index``
     - integer
     - Starting index in the database
   * - ``-to, --to_index``
     - integer
     - Stopping index in the database
   * - ``--selected``
     - flag
     - Only send to selected recipients

Rate Limiting & Batch Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Argument
     - Type
     - Description
   * - ``-mh, --max-mails-per-hour``
     - integer
     - Maximum emails to send per hour (default: 1000)
   * - ``-na, --max_addr_per_mail``
     - integer
     - Maximum number of addresses per mail (default: 50)
   * - ``-p, --pause``
     - integer
     - Pause duration in seconds between operations (default: 3)
   * - ``-w, --wait``
     - integer
     - Wait x minutes before starting to send mail

Other Options
^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Argument
     - Type
     - Description
   * - ``--body``
     - string
     - Specifies the email body content
   * - ``--check_spam``
     - flag
     - Perform spam detection checks

Usage Examples
--------------

Example 1: Basic Newsletter with Attachments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Send a newsletter to all active members with a PDF attachment:

.. code-block:: bash

    python sendMail.py --profile artscroises \
        -s "Newsletter January 2026" \
        newsletter.pdf logo.png

Example 2: Test Mode with Custom Message
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Test email sending with a custom message to the test group only:

.. code-block:: bash

    python sendMail.py --profile artscroises \
        -s "Test Newsletter" \
        -m "This is a test message" \
        -t \
        -v \
        newsletter.pdf

Example 3: HTML Email with Rate Limiting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Send HTML email with controlled rate limiting:

.. code-block:: bash

    python sendMail.py --profile cambristi \
        -s "Event Announcement" \
        -mh 500 \
        -na 25 \
        -p 5 \
        email_template.html


Example 4: Partial Database Processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Process only records 100 to 200 from the database:

.. code-block:: bash

    python sendMail.py --profile artscroises \
        -s "Newsletter" \
        -f 100 \
        -to 200 \
        newsletter.pdf

Example 5: Dry Run (No Sending)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Preview what would be sent without actually sending emails:

.. code-block:: bash

    python sendMail.py --profile artscroises \
        -s "Newsletter Test" \
        -x \
        -v \
        newsletter.pdf

Example 6: Selected Recipients Only
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Send only to recipients marked as "selected" in the database:

.. code-block:: bash

    python sendMail.py --profile artscroises \
        -s "Special Announcement" \
        --selected \
        announcement.pdf

Example 7: Using CSV Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use a local CSV file instead of Google Sheets:

.. code-block:: bash

    python sendMail.py --profile artscroises \
        -s "Newsletter" \
        -db subscribers.csv \
        newsletter.pdf

Example 8: Delayed Send with Wait Time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Wait 30 minutes before starting the mail campaign:

.. code-block:: bash

    python sendMail.py --profile artscroises \
        -s "Scheduled Newsletter" \
        -w 30 \
        newsletter.pdf

Configuration
-------------

The module requires a ``config.yml`` file with profile-specific settings:

.. code-block:: yaml

    artscroises:
      MAILCONFIG: "ArtsCroisesMailConfig"
      SA: "artscroisesServiceAccount"
      sheetid: "artscroisesmembersdb"
      mailing_folder: "folder_id_from_google_drive"
      smtp_host: "smtp.example.com"
      smtp_port: 587
      imap_host: "imap.example.com"
      imap_port: 993
      max_mails_per_hour: 1000
      max_addr_per_mail: 50
      pause: 3

    cambristi:
      MAILCONFIG: "CambristiMailConfig"
      # Similar configuration...

Secrets (credentials, API keys) should be stored securely using the ``getSecrets`` module.
