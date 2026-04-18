# sendMail - Email Campaign Management System

[![Tests](https://github.com/xmayeur/mailing/workflows/Tests/badge.svg)](https://github.com/xmayeur/mailing/actions)
[![codecov](https://codecov.io/gh/xmayeur/mailing/branch/master/graph/badge.svg)](https://codecov.io/gh/xmayeur/mailing)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Build and Release Executables](https://github.com/xmayeur/mailing/actions/workflows/main.yml/badge.svg)](https://github.com/xmayeur/mailing/actions/workflows/main.yml)

A comprehensive email campaign management system for organizations managing mailing lists, newsletters, and membership communications.

## Overview

**sendMail** is a Python-based bulk email management system that provides:

* **Bulk email sending** with rate limiting and batch processing
* **Multiple email profiles**
* **Google Sheets integration** for subscriber management
* **CSV/Excel database support** for dynamic subscriber lists
* **Google Drive integration** for attachment handling
* **Markdown support** for email content
* **HTML email templates** with inline image support
* **SMTP and Gmail API** support for sending emails
* **Flexible filtering** based on subscriber attributes

## Features

* 📧 **Multi-profile email campaigns** with configurable settings
* 📊 **Google Sheets integration** for dynamic subscriber lists
* 📁 **Google Drive integration** for automatic attachment downloads
* 🎨 **HTML email support** with automatic inline image processing
* ⏱️ **Rate limiting** to comply with email provider restrictions
* 🔄 **Batch processing** with pause and resume capabilities
* 🧪 **Test mode** for safe campaign testing
* 📝 **Detailed logging** for monitoring and debugging
* 🔒 **Secure credential management** via secrets vault

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd sendMail

# Install required dependencies
pip install -r requirements.txt
```

### Dependencies

* gspread
* google-auth
* google-auth-oauthlib
* google-auth-httplib2
* google-api-python-client
* oauth2client
* PyYAML
* beautifulsoup4
* Pillow
* requests
* certifi
* markdown2
* python-calamine

## Configuration

### sendMail.yml

Create a `sendMail.yml` config file with profile-specific settings (IMAP/SMTP)
Store this file in the following directory: `$HOME/.config` (MAC or Unix) or `%USERPROFILE%/.config` (Windows)
or specify your own config file path with the `sendMail -cfg myConfigFile.yml` argument

```yaml
myProfile:
  sender: "sender@example.com"                      # Email address to send from
  sendername: "John Doe"                            # Displayed name in the message header
  username: "jdoe"                                  # Username for SMTP/IMAP authentication
  password: "password"                              # Password for SMTP/IMAP authentication
  smtp_host: "smtp.example.com"                     # SMTP server address
  smtp_port: 587                                    # SMTP server port
  smtp_tls:                                         # Enable TLS encryption (optional)
  imap_host: "imap.example.com"                     # IMAP server address
  imap_port: 993                                    # IMAP server port
  domain: "example.com"                             # Domain for email address validation 
  sent_folder: "Sent"                               # folder to store sent messages
  max_mails_per_hour: 1000                          # maximum emails to send per hour
  max_addr_per_mail: 50                             # maximum number of addresses per mail
  pause: 3                                          # pause duration in seconds between operations
  filter: # Filtering options - see below for details
    email: is not empty
    status: is active
  filter_test: # filter active in test mode
    email: is "tester@example.com"
    group: in "test, Test"
  MAILCONFIG: "myProfile"                           # (optional) key name to retrieve some of the below parameters that are in a secure vault
  SA: "myServiceAccount"                            # (optional) if attachment are on a Google Driven key name of Service Account credentials in the secure vault
  sheetid: "myMembersDB"                            # (optional) key name of the member database as Google Sheets identifier in vault 
  mailing_folder: "folder_id_from_google_drive"     # (optional) Google driver folder ID where message attachments are stored

myOtherProfile:
  MAILCONFIG: "myOtherMailConfig"
  # Similar configuration... excepted for gmail_api_key and gmail_api_secret if used
  gmailCredentials:
    installed:
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
      "auth_uri": "https://accounts.google.com/o/oauth2/auth"
      "client_id": "*****"
      "client_secret": "****"
      "project_id": "****"
      "redirect_uris":
        - "http://localhost"
      "refresh_token": ""
      "token_uri": "https://oauth2.googleapis.com/token"
  TOKEN_FILE: 'token.json'
  SCOPES:
    - 'https://www.googleapis.com/auth/gmail.readonly'
    - 'https://www.googleapis.com/auth/gmail.modify'
    - 'https://www.googleapis.com/auth/gmail.send'
```

The filter section is optional and can be used to filter subscribers based on specific attributes.

if all the conditions are met, the subscriber is added to the mailing list

The syntax is:

```
filter:
    <field_name>: <operation> <value>
    <field_name>: <operation> <value>

where:
<field_name>: is a field from the subscriber database (email, first_name...)
<operation>: is one of  "is", "is not", "gt", "lt", "ge", "le", "in", "not in"
                        "is empty", "is not empty", "greater than", "less than",
                        "greater or equal to", "less or equal to", "one of", "none of",
                        "is equal to", "is not equal to"
<value>: is the value to compare with
```

### Secrets Management

Optionally, Credentials and API keys can be stored securely using the `getSecrets` module. Typical secrets:

* **MAILCONFIG**: SMTP/IMAP credentials
* **Service Account**: Google API credentials
* **Sheet ID**: Google Sheets identifier

## Command-Line Usage

### Basic Syntax

```bash
python sendMail.py --profile <profile_name> [options] [files...]
```

### Arguments

#### Basic Options

| Argument         | Type   | Description                                                                              |
|------------------|--------|------------------------------------------------------------------------------------------|
| `--profile`      | string | **Required**. Mail profile to use (`artscroises` or `cambristi`)                         |
| `-cfg, --config` | string | Path to config file (default: `$HOME/.config/sendMail.yml`)                              |
| `-s, --subject`  | string | Subject of the email                                                                     |
| `-m, --message`  | string | Text message body of the email - optional if files argument given                        |
| `file`           | list   | Files `(.html, .txt, .pdf, .md, .png, .jpg)`to attach to the email (positional argument) |
| `--keep-html`    | flag   | Keep HTML files after conversion of `.md` Markdown files                                 |

#### Test & Debug Options

| Argument          | Type | Description                                                                 |
|-------------------|------|-----------------------------------------------------------------------------|
| `-t, --test`      | flag | Test mode - send only to the tester group according to filter_test settings |
| `-v, --verbose`   | flag | Increase output verbosity                                                   |
| `-x, --doNotSend` | flag | Do not send any mail (dry run)                                              |

#### Database Options

| Argument           | Type    | Description                                                       |
|--------------------|---------|-------------------------------------------------------------------|
| `-db, --database`  | string  | Path to CSV or Excel database file (alternative to Google Sheets) |
| `-f, --from_index` | integer | Starting index in the database                                    |
| `-to, --to_index`  | integer | Stopping index in the database                                    |
| `--selected`       | flag    | Only send to selected recipients                                  |

#### Rate Limiting & Batch Options

| Argument                    | Type    | Description                                               |
|-----------------------------|---------|-----------------------------------------------------------|
| `-mh, --max-mails-per-hour` | integer | Maximum emails to send per hour (default: 1000)           |
| `-na, --max_addr_per_mail`  | integer | Maximum number of addresses per mail (default: 50)        |
| `-p, --pause`               | integer | Pause duration in seconds between operations (default: 3) |
| `-w, --wait`                | integer | Wait x minutes before starting to send mail               |

#### Other Options

| Argument    | Type | Description                              |
|-------------|------|------------------------------------------|
| `--md2html` | flag | Convert a Markdown file to HTML and exit |

## Usage Examples

### Example 1: Basic Newsletter with Attachments

Send a newsletter to all active members with a PDF attachment:

```bash
python sendMail.py --profile artscroises \
    -s "Newsletter January 2026" \
    newsletter.pdf logo.png
```

### Example 2: Test Mode with Custom Message

Test email sending with a custom message to the test group only:

```bash
python sendMail.py --profile artscroises \
    -s "Test Newsletter" \
    -m "This is a test message" \
    -t \
    -v \
    newsletter.pdf
```

### Example 3: HTML Email with Rate Limiting

Send HTML email from converted mardonx file with controlled rate limiting:

```bash
python sendMail.py --profile cambristi \
    -s "Event Announcement" \
    -mh 500 \
    -na 25 \
    -p 5 \
    -keephtml \
    email_template.md
```

email_template.html will be created in the same directory and can be published to a web site

### Example 4: Partial Database Processing

Process only records 100 to 200 from the database:

```bash
python sendMail.py --profile artscroises \
    -s "Newsletter" \
    -f 100 \
    -to 200 \
    newsletter.pdf
```

### Example 5: Dry Run (No Sending)

Preview what would be sent without actually sending emails:

```bash
python sendMail.py --profile artscroises \
    -s "Newsletter Test" \
    -x \
    -v \
    newsletter.pdf
```

### Example 6: Selected Recipients Only

Send only to recipients marked as "selected" in the database:

```bash
python sendMail.py --profile artscroises \
    -s "Special Announcement" \
    --selected \
    announcement.pdf
```

### Example 7: Using CSV Database

Use a local CSV file instead of Google Sheets:

```bash
python sendMail.py --profile artscroises \
    -s "Newsletter" \
    -db subscribers.csv \
    newsletter.pdf
```

### Example 8: Delayed Send with Wait Time

Wait 30 minutes before starting the mail campaign:

```bash
python sendMail.py --profile artscroises \
    -s "Scheduled Newsletter" \
    -w 30 \
    newsletter.pdf
```

## Database Structure

### Google Sheets Format

The subscriber database should include the following columns:

* `id` - Unique subscriber ID
* `first_name` - First name
* `last_name` - Last name
* `email` - Email address
* `status` - Subscription status (active/inactive)
* `group` - Mailing list group
* `selected` - Selection marker (x for selected)
* `member` - Membership status (yes/no)
* `phone` - Phone number
* `mobile_phone` - Mobile phone number
* `address` - Street address
* `city` - City
* `zip` - Postal code
* `Cotisation YYYY` - Cotisation payment status for year YYYY

### CSV Format

When using a local CSV file with `-db`, use the same column structure as above with UTF-8 encoding.

## Email Templates

### HTML Templates

HTML email templates support:

* Inline images (automatically converted to CID references)
* Image optimization and compression
* Responsive design elements
* CSS styling

Place images in the same directory as the HTML file and reference them with relative paths:

```html
<img src="logo.png" alt="Logo">
```

### Message Variables

Use template variables in your message text:

```
Dear ${first_name} ${last_name},
...
```

Available variables match the column names in your database.

## Logging

All operations are logged to `sendMail.log` with timestamps and severity levels:

* **INFO**: Normal operations
* **WARNING**: Non-critical issues
* **ERROR**: Failed operations
* **CRITICAL**: Fatal errors

## Google Drive Integration

The system can automatically download attachments from Google Drive:

1. Configure `mailing_folder` in `config.yml` with your Drive folder ID
2. Upload files to the specified folder
3. Run without specifying files - they'll be downloaded automatically
4. After successful sending, files are renamed with `published_` prefix

## Best Practices

1. **Always test first**: Use `-t` flag to send to test group before production
2. **Use rate limiting**: Configure appropriate limits to avoid provider restrictions
3. **Monitor logs**: Check `sendMail.log` for issues
4. **Dry run**: Use `-x` flag to preview without sending
5. **Batch processing**: Use `-f` and `-to` for large lists to process in chunks
6. **Backup data**: Keep backups of your subscriber database
7. **Test HTML**: Preview HTML templates in email clients before sending

## Troubleshooting

### Authentication Errors

* Verify SMTP/IMAP credentials in secrets
* Check Google API credentials are valid
* Ensure service account has proper permissions

### Rate Limiting Issues

* Reduce `max_mails_per_hour` and `max_addr_per_mail`
* Increase `pause` duration between sends
* Use `-w` to schedule sends during off-peak hours

### Template Problems

* Verify HTML syntax is valid
* Check image paths are relative and correct
* Test with simple text email first

### Database Connection Issues

* Verify Google Sheets ID is correct
* Check service account has access to the sheet
* Try using local CSV with `-db` flag

## Testing

The project includes a comprehensive test suite using pytest.

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_sendMail.py -v

# Run specific test class
pytest tests/test_sendMail.py::TestDict2Class -v

# Run specific test function
pytest tests/test_sendMail.py::TestDict2Class::test_dict_to_class_conversion -v
```

### Test Structure

```
tests/
├── __init__.py
├── test_sendMail.py       # Tests for sendMail.py
└── test_googleDriveLib.py # Tests for googleDriveLib.py
```

### Test Coverage

The test suite covers:

* ✅ **Dictionary to Class conversion** utilities
* ✅ **File utilities** (MIME type detection, Base64 encoding)
* ✅ **Message formatting** with variable substitution
* ✅ **Filtering functions** for both profiles
* ✅ **Email building** with various configurations
* ✅ **Google Drive** connection, file listing, download, upload, and rename
* ✅ **Argument parsing** for command-line interface

### Continuous Integration

Tests run automatically on every push and pull request via GitHub Actions:

* ✅ Multiple Python versions (3.10, 3.11)
* ✅ Multiple operating systems (Ubuntu, macOS, Windows)
* ✅ Code coverage reporting via Codecov
* ✅ Linting with flake8 and black

### Test Status

| Component         | Status                                                               | Coverage                                                                 |
|-------------------|----------------------------------------------------------------------|--------------------------------------------------------------------------|
| sendMail.py       | ![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg) | ![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg) |
| googleDriveLib.py | ![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg) | ![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen.svg) |

### Writing New Tests

When adding new features, follow these guidelines:

1. **Create test file** in `tests/` directory matching module name
2. **Use mocks** for external dependencies (Google APIs, SMTP, etc.)
3. **Test edge cases** including error conditions
4. **Follow naming convention**: `test_<function_name>_<scenario>`
5. **Add docstrings** to explain what each test validates

Example test structure:

```python
class TestYourFeature:
    """Tests for your feature"""

    def test_feature_success(self):
        """Test successful operation"""
        # Arrange
        mock_data = {"key": "value"}

        # Act
        result = your_function(mock_data)

        # Assert
        assert result is not None

    def test_feature_failure(self):
        """Test error handling"""
        # Arrange & Act & Assert
        with pytest.raises(ValueError):
            your_function(invalid_data)
```

## Documentation

Online documentation is available at https://mailing.readthedocs.io/.

Full API documentation is available in the `docs/` directory. Build with:

```bash
sphinx-build -b html docs docs/_build/html
```

View at `docs/_build/html/index.html`

## Copyright

© Copyright 2025-2026 Xavier Mayeur

## License

This program is free software: you can redistribute it and/or modify it under the terms of the [GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.txt) as published by the Free Software Foundation, version 3 of the License

## Support

For issues and questions, please contact the maintainer or file an issue in the repository.

## Contributing

Contributions are welcome! Please follow the existing code style and include tests for new features.

## Changelog

All notable changes to this project will be documented here.

### 2026-02-11

* Added initial changelog section to README.
