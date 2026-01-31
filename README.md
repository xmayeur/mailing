# sendMail - Email Campaign Management System

A comprehensive email campaign management system for organizations managing mailing lists, newsletters, and membership communications.

## Overview

**sendMail** is a Python-based bulk email management system that provides:

* **Bulk email sending** with rate limiting and batch processing
* **Multiple email profiles** (Arts Croisés, Cambristi)
* **Google Sheets integration** for subscriber management
* **Google Drive integration** for attachment handling
* **HTML email templates** with inline image support
* **Invoice generation** via Billit.be API
* **Membership management** and cotisation reminders
* **SMTP and Gmail API** support for sending emails
* **Flexible filtering** based on subscriber attributes

## Features

- 📧 **Multi-profile email campaigns** with configurable settings
- 📊 **Google Sheets integration** for dynamic subscriber lists
- 📁 **Google Drive integration** for automatic attachment downloads
- 🎨 **HTML email support** with automatic inline image processing
- 🧾 **Invoice generation** using Billit.be API
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

| Argument | Type | Description |
|----------|------|-------------|
| `--profile` | string | **Required**. Mail profile to use (`artscroises` or `cambristi`) |
| `-s, --subject` | string | Subject of the email |
| `-m, --message` | string | Text message body of the email |
| `file` | list | Files to attach to the email (positional argument) |

#### Test & Debug Options

| Argument | Type | Description |
|----------|------|-------------|
| `-t, --test` | flag | Test mode - send only to the tester group |
| `-v, --verbose` | flag | Increase output verbosity |
| `-x, --doNotSend` | flag | Do not send any mail (dry run) |

#### Database Options

| Argument | Type | Description |
|----------|------|-------------|
| `-db, --database` | string | Path to CSV database file (alternative to Google Sheets) |
| `-f, --from_index` | integer | Starting index in the database |
| `-to, --to_index` | integer | Stopping index in the database |
| `--selected` | flag | Only send to selected recipients |

#### Rate Limiting & Batch Options

| Argument | Type | Description |
|----------|------|-------------|
| `-mh, --max-mails-per-hour` | integer | Maximum emails to send per hour (default: 1000) |
| `-na, --max_addr_per_mail` | integer | Maximum number of addresses per mail (default: 50) |
| `-p, --pause` | integer | Pause duration in seconds between operations (default: 3) |
| `-w, --wait` | integer | Wait x minutes before starting to send mail |

#### Membership & Invoice Options

| Argument | Type | Description |
|----------|------|-------------|
| `--cotisation` | flag | Generate cotisation reminder mail |
| `-y, --cotisation_year` | string | Cotisation year (default: "2026") |
| `-amt, --cotisation_amount` | string | Cotisation amount (default: "15.00") |
| `--sync` | flag | Synchronize members database with Billit |

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

### Example 4: Membership Cotisation Reminder

Generate and send cotisation invoices for 2026:

```bash
python sendMail.py --profile artscroises \
    --cotisation \
    -y 2026 \
    -amt 15.00
```

### Example 5: Partial Database Processing

Process only records 100 to 200 from the database:

```bash
python sendMail.py --profile artscroises \
    -s "Newsletter" \
    -f 100 \
    -to 200 \
    newsletter.pdf
```

### Example 6: Dry Run (No Sending)

Preview what would be sent without actually sending emails:

```bash
python sendMail.py --profile artscroises \
    -s "Newsletter Test" \
    -x \
    -v \
    newsletter.pdf
```

### Example 7: Selected Recipients Only

Send only to recipients marked as "selected" in the database:

```bash
python sendMail.py --profile artscroises \
    -s "Special Announcement" \
    --selected \
    announcement.pdf
```

### Example 8: Using CSV Database

Use a local CSV file instead of Google Sheets:

```bash
python sendMail.py --profile artscroises \
    -s "Newsletter" \
    -db subscribers.csv \
    newsletter.pdf
```

### Example 9: Delayed Send with Wait Time

Wait 30 minutes before starting the mail campaign:

```bash
python sendMail.py --profile artscroises \
    -s "Scheduled Newsletter" \
    -w 30 \
    newsletter.pdf
```

### Example 10: Sync Members with Billit

Synchronize member database with Billit invoicing system:

```bash
python sendMail.py --profile artscroises \
    --sync
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

## Invoice Generation (Arts Croisés Profile)

The Billit.be integration allows:

- Creating/updating client records
- Generating invoices for membership fees
- Automatic payment reference generation
- Email templates with payment instructions

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

## Documentation

Full API documentation is available in the `docs/` directory. Build with:

```bash
sphinx-build -b html docs docs/_build/html
```

View at `docs/_build/html/index.html`

## License

[Your License Here]

## Support

For issues and questions, please contact the maintainer or file an issue in the repository.

## Contributing

Contributions are welcome! Please follow the existing code style and include tests for new features.

