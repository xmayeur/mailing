================
Editor Tutorial
================

Welcome to the sendMail Editor tutorial. This guide covers how to use the standalone WYSIWYG newsletter editor to create, edit, and manage HTML newsletters.

Getting Started
===============

Prerequisites
-------------

- Python 3.10 or later
- PySide6 and QtWebEngine installed
- sendMail package installed

Installation
------------

If you haven't installed sendMail yet::

    pip install sendMail

Or from source::

    git clone https://github.com/xmayeur/mailing.git
    cd mailing
    pip install -e .

Launching the Editor
====================

From Command Line
-----------------

Launch a blank editor::

    python src/editor.py

Open an existing file::

    python src/editor.py path/to/your/newsletter.md
    python src/editor.py path/to/your/newsletter.html

Using the Standalone Binary (macOS/Windows)
--------------------------------------------

If you've built the Nuitka standalone executable::

    ./dist_nuitka/editor.app/Contents/MacOS/sendMailEditor
    ./dist_nuitka/editor.build/sendMailEditor.exe

Creating a New Newsletter
=========================

1. Launch the editor with no arguments
2. You'll see a blank document with the rich text editor in the center
3. Start typing or paste content into the editor
4. Use the formatting toolbar to style your text:

   - **Bold**, *Italic*, ~~Strikethrough~~
   - Heading sizes (H1, H2, H3, etc.)
   - Lists (bullet and numbered)
   - Links and images
   - Blockquotes
   - Code blocks

Opening Existing Documents
===========================

The editor supports both Markdown and HTML::

    # Open a Markdown file
    python src/editor.py newsletters/2026-05-17.md

    # Open an HTML file
    python src/editor.py newsletters/template.html

When you open a file, the editor automatically detects the format and displays it in the rich text editor.

Editing Content
===============

Text Formatting
---------------

Use the Quill editor toolbar to format text:

1. **Emphasis**: Select text and click Bold (B) or Italic (I)
2. **Headings**: Select text and choose heading size from dropdown
3. **Lists**: Click the bullet list or number list button
4. **Links**: Select text, click the link button, enter URL
5. **Images**: Click the image button and choose from your computer

Inserting Images
----------------

1. Click the image button in the toolbar
2. Select an image from your computer
3. The image is automatically embedded as base64 for HTML export

HTML Preview
------------

The editor shows a live preview of the generated HTML. This helps you see how the newsletter will look when sent.

Working with Filters
====================

The editor includes advanced filtering capabilities for conditional content delivery.

Opening the Send Dialog
-----------------------

1. Click **File** → **Send...** or use Ctrl+Enter (Cmd+Enter on macOS)
2. This opens the Send Dialog with filter options
3. The dialog shows your current sendMail profiles

Note: Ctrl+S (Cmd+S) saves the newsletter; it does not open the send dialog.

Setting Up Filters
------------------

The send dialog uses a **visual filter builder**: each filter row is a
combination of a field dropdown, an operator dropdown, and a value input.

1. Click **Add Row** to add a filter row
2. Pick a **field** from the dropdown (populated from your database schema)
3. Pick an **operator** (e.g. *is equal to*, *is not empty*, *one of*)
4. Enter the expected **value** (a larger text box appears for list operators)
5. Click **Apply Filter** to activate the filter
6. Click **Reset Filter** to fall back to the profile's configured filter
7. The editor validates the filter in real-time; a status line under the
   builder shows errors (red) or validity (green)

When the **Test** checkbox is enabled, the dialog edits the profile's
``filter_test`` rules instead of ``filter``.

Database Preview
----------------

1. Enter a subscriber database path (CSV or Excel) via the **Database**
   **Browse** button, or leave it empty to use the profile's Google Sheets
2. Matching records load automatically (a **Retry** button appears if loading fails)
3. The editor shows matching records based on your filter
4. See exactly which subscribers will receive the filtered content

Valid Filter Fields
-------------------

Filter fields depend on your subscriber database schema. Common fields include:

- ``country``
- ``email``
- ``subscription_level``
- ``name``
- Custom fields from your CSV/Google Sheets

Managing Profiles
=================

Adding sendMail Profiles
------------------------

The editor reads profiles from your ``config.yml``. Each top-level key is a
profile name::

    newsletter:
      sender: newsletters@example.com
      sendername: "Example Newsletters"
      max_mails_per_hour: 100
      filter:
        subscription_level: premium

Selecting a Profile
--------------------

1. Open the Send Dialog (File → Send...)
2. The **Profile** dropdown shows all available profiles
3. Select the profile to use for sending
4. The filter fields are validated against that profile's database

Profile Configuration
---------------------

Profiles are managed in your sendMail configuration file::

    # Edit your configuration
    python src/editor.py
    # Then: Settings → Edit Config...

Saving Your Work
================

The editor saves your content as **HTML files**, ready for sending with
sendMail. Opening a Markdown file edits it in the rich text editor; saving
writes the rendered HTML next to it.

HTML Format
-----------

The output format includes:

- Rendered HTML markup
- Embedded images as base64
- Styling and formatting preserved
- Complete ``<!DOCTYPE>`` document with stylesheet

Save Behavior
-------------

**New documents**: Saved with your chosen filename::

    # File → Save As, choose name and location
    # Creates: newsletters/my-newsletter.html

**Existing documents**: Updated in place when you save.

Manual Save
-----------

Use **File** → **Save** (Ctrl+S / Cmd+S) to save current edits, or
**File** → **Save As...** (Ctrl+Shift+S) to save with a new filename.

Sending via sendMail
====================

Once your newsletter is ready:

1. **Save the newsletter** in the editor
2. **Note the HTML file path** (e.g., ``newsletters/2026-05-17.html``)
3. **Send via sendMail**::

    python src/sendMail.py --profile newsletter \
      -s "May Newsletter 2026" \
      newsletters/2026-05-17.html

With Filters
------------

Filters are not passed on the command line. They come either from the
profile's ``filter`` key in ``config.yml``, or from a filter applied in the
editor's Send Dialog::

    python src/sendMail.py --profile newsletter \
      -s "Premium Subscribers Newsletter" \
      newsletters/2026-05-17.html

Use ``-t`` to send in test mode (applies the profile's ``filter_test`` rules)::

    python src/sendMail.py --profile newsletter -t \
      -s "Test Send" \
      newsletters/2026-05-17.html

Using Database Preview Filter
------------------------------

1. Set up the filter in the editor's Send Dialog and click **Apply Filter**
2. The preview shows exactly which records match
3. Send directly from the dialog — the applied filter is used for the send

Tips and Tricks
===============

Templates
---------

Create reusable newsletter templates::

    # Save as a template
    python src/editor.py templates/base-newsletter.md

    # Create new newsletter from template
    cp templates/base-newsletter.md newsletters/2026-05-20.md
    python src/editor.py newsletters/2026-05-20.md

Batch Processing
----------------

For recurring newsletters::

    # Create a weekly newsletter
    python src/editor.py newsletters/weekly-$(date +%Y-%m-%d).md

    # Send when ready
    python src/sendMail.py --profile newsletter \
      -s "Weekly Update" \
      newsletters/weekly-$(date +%Y-%m-%d).html

Filter Testing
--------------

Before sending to your full list:

1. Create a test filter in the editor and use database preview to see matching records
2. Configure the profile's ``filter_test`` rules in ``config.yml``
3. Test with a small group first::

    python src/sendMail.py --profile newsletter \
      -s "Test Newsletter" \
      -t \
      newsletters/test.html

Image Best Practices
--------------------

1. **Size appropriately**: Compress images before inserting
2. **Alt text**: Always provide alt text for accessibility
3. **Responsive**: The editor scales images to fit email widths
4. **Test rendering**: Preview in the HTML pane before sending

Markdown Tips
-------------

The editor supports full GitHub-flavored Markdown:

- Tables
- Code blocks with syntax highlighting
- Links and references
- Inline HTML (for advanced formatting)

Google Sheets Integration
-------------------------

To use Google Sheets for subscriber lists:

1. Set up Google Sheets credentials in sendMail config
2. In the editor, select your Google Sheets database
3. Use database preview to verify filters work correctly

Common Tasks
============

Create and Send a Simple Newsletter
-----------------------------------

::

    # 1. Create new newsletter
    python src/editor.py newsletters/announcement.md

    # 2. Edit in the editor GUI
    # (Add your content and format it)

    # 3. Send to all subscribers
    python src/sendMail.py --profile default \
      -s "Important Announcement" \
      newsletters/announcement.html

Send to Filtered Group
----------------------

::

    # 1. Create newsletter
    python src/editor.py newsletters/premium-offer.md

    # 2. Set up filter in editor's Send Dialog (or in the profile's
    #    "filter" key in config.yml)
    # Filter: subscription_level is equal to premium

    # 3. Test with preview
    # (Verify matching records in database preview)

    # 4. Send to filtered group
    python src/sendMail.py --profile default \
      -s "Exclusive Premium Offer" \
      newsletters/premium-offer.html

Create Newsletter from Template
-------------------------------

::

    # Copy template
    cp templates/newsletter-template.md newsletters/2026-05-18.md

    # Open in editor
    python src/editor.py newsletters/2026-05-18.md

    # Customize content and send
    python src/sendMail.py --profile newsletter \
      -s "Weekly Newsletter" \
      newsletters/2026-05-18.html

Troubleshooting
===============

Editor Won't Launch
-------------------

- Verify PySide6 is installed (it comes with the repository's dependencies)
- Check Python version: ``python --version`` (requires 3.10+)
- On Linux without display: Use xvfb or set ``QT_QPA_PLATFORM=offscreen``

Filter Not Validating
---------------------

- Pick field names from the dropdown so they match your database schema
- Check the error message shown under the filter builder
- Operators requiring a value must have one (e.g. *is equal to*)
- For ``filter``/``filter_test`` keys edited in config.yml, check YAML syntax
  (proper indentation with spaces, not tabs)

Images Not Embedding
---------------------

- Check image file path is correct
- Large images may be scaled down for email compatibility
- Some email clients strip images - always provide alt text

sendMail Command Not Found
---------------------------

- Ensure sendMail is installed: ``pip install sendMail``
- Or use full path: ``python src/sendMail.py``
