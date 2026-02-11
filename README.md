# sendMail - Email Campaign Management System

[![Tests](https://github.com/xmayeur/mailing/workflows/Tests/badge.svg)](https://github.com/xmayeur/mailing/actions)
[![codecov](https://codecov.io/gh/xmayeur/mailing/branch/master/graph/badge.svg)](https://codecov.io/gh/xmayeur/mailing)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive email campaign management system for organizations managing mailing lists, newsletters, and membership communications.

## Overview

**sendMail** is a Python-based bulk email management system that provides:

* **Bulk email sending** with rate limiting and batch processing
* **Multiple email profiles** (Arts Croisés, Cambristi)
* **Google Sheets integration** for subscriber management
* **Google Drive integration** for attachment handling
* **HTML email templates** with inline image support
* **SMTP and Gmail API** support for sending emails
* **Flexible filtering** based on subscriber attributes

## Features

- 📧 **Multi-profile email campaigns** with configurable settings
- 📊 **Google Sheets integration** for dynamic subscriber lists
- 📁 **Google Drive integration** for automatic attachment downloads
- 🎨 **HTML email support** with automatic inline image processing
- ⏱️ **Rate limiting** to comply with email provider restrictions
- 🔄 **Batch processing** with pause and resume capabilities
- 🧪 **Test mode** for safe campaign testing
- 📝 **Detailed logging** for monitoring and debugging
- 🔒 **Secure credential management** via secrets vault

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd sendMail

# Install required dependencies
pip install -r requirements.txt
```

### Dependencies

- gspread
- google-auth
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client
- oauth2client
- PyYAML
- beautifulsoup4
- Pillow
- requests
- certifi
- markdown2

## Configuration

### config.yml

Create a `config.yml` file with profile-specific settings:

```yaml
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
```

### Secrets Management

Credentials and API keys should be stored securely using the `getSecrets` module. Required secrets:

- **MAILCONFIG**: SMTP/IMAP credentials
- **Service Account**: Google API credentials
- **Sheet ID**: Google Sheets identifier
- **Billit API Token**: For invoice generation (Arts Croisés profile)

## Command-Line Usage

### Basic Syntax

```bash
python sendMail.py --profile <profile_name> [options] [files...]
```

### Arguments

#### Basic Options

| Argument        | Type   | Description                                                      |
|-----------------|--------|------------------------------------------------------------------|
| `--profile`     | string | **Required**. Mail profile to use (`artscroises` or `cambristi`) |
| `-s, --subject` | string | Subject of the email                                             |
| `-m, --message` | string | Text message body of the email                                   |
| `file`          | list   | Files to attach to the email (positional argument)               |

#### Test & Debug Options

| Argument          | Type | Description                               |
|-------------------|------|-------------------------------------------|
| `-t, --test`      | flag | Test mode - send only to the tester group |
| `-v, --verbose`   | flag | Increase output verbosity                 |
| `-x, --doNotSend` | flag | Do not send any mail (dry run)            |

#### Database Options

| Argument           | Type    | Description                                              |
|--------------------|---------|----------------------------------------------------------|
| `-db, --database`  | string  | Path to CSV database file (alternative to Google Sheets) |
| `-f, --from_index` | integer | Starting index in the database                           |
| `-to, --to_index`  | integer | Stopping index in the database                           |
| `--selected`       | flag    | Only send to selected recipients                         |

#### Rate Limiting & Batch Options

| Argument                    | Type    | Description                                               |
|-----------------------------|---------|-----------------------------------------------------------|
| `-mh, --max-mails-per-hour` | integer | Maximum emails to send per hour (default: 1000)           |
| `-na, --max_addr_per_mail`  | integer | Maximum number of addresses per mail (default: 50)        |
| `-p, --pause`               | integer | Pause duration in seconds between operations (default: 3) |
| `-w, --wait`                | integer | Wait x minutes before starting to send mail               |

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

Send HTML email with controlled rate limiting:

```bash
python sendMail.py --profile cambristi \
    -s "Event Announcement" \
    -mh 500 \
    -na 25 \
    -p 5 \
    email_template.html
```

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

- `id` - Unique subscriber ID
- `first_name` - First name
- `last_name` - Last name
- `email` - Email address
- `status` - Subscription status (active/inactive)
- `group` - Mailing list group
- `selected` - Selection marker (x for selected)
- `member` - Membership status (yes/no)
- `phone` - Phone number
- `mobile_phone` - Mobile phone number
- `address` - Street address
- `city` - City
- `zip` - Postal code
- `Cotisation YYYY` - Cotisation payment status for year YYYY

### CSV Format

When using a local CSV file with `-db`, use the same column structure as above with UTF-8 encoding.

## Email Templates

### HTML Templates

HTML email templates support:
- Inline images (automatically converted to CID references)
- Image optimization and compression
- Responsive design elements
- CSS styling

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

- **INFO**: Normal operations
- **WARNING**: Non-critical issues
- **ERROR**: Failed operations
- **CRITICAL**: Fatal errors

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
- Verify SMTP/IMAP credentials in secrets
- Check Google API credentials are valid
- Ensure service account has proper permissions

### Rate Limiting Issues
- Reduce `max_mails_per_hour` and `max_addr_per_mail`
- Increase `pause` duration between sends
- Use `-w` to schedule sends during off-peak hours

### Template Problems
- Verify HTML syntax is valid
- Check image paths are relative and correct
- Test with simple text email first

### Database Connection Issues
- Verify Google Sheets ID is correct
- Check service account has access to the sheet
- Try using local CSV with `-db` flag

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

- ✅ **Dictionary to Class conversion** utilities
- ✅ **File utilities** (MIME type detection, Base64 encoding)
- ✅ **Message formatting** with variable substitution
- ✅ **Filtering functions** for both profiles
- ✅ **Email building** with various configurations
- ✅ **Google Drive** connection, file listing, download, upload, and rename
- ✅ **Argument parsing** for command-line interface

### Continuous Integration

Tests run automatically on every push and pull request via GitHub Actions:

- ✅ Multiple Python versions (3.10, 3.11)
- ✅ Multiple operating systems (Ubuntu, macOS, Windows)
- ✅ Code coverage reporting via Codecov
- ✅ Linting with flake8 and black

### Test Status

| Component         | Status                                                               | Coverage                                                                 |
|-------------------|----------------------------------------------------------------------|--------------------------------------------------------------------------|
| sendMail.py       | ![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg) | ![Coverage](https://img.shields.io/badge/coverage-87%25-yellow.svg)      |
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

