# Email Profiles Configuration Guide

## Overview

Email profiles manage SMTP configuration, styling, and filtering for email campaigns.

## Profile Structure

```yaml
profiles:
  artscroises:
    vault_key: "mailconfig: artscroises"    # Secrets Manager key for SMTP credentials
    sender: "newsletter@artscroises.com"    # Default sender email
    template_file: "templates/artscroises.html"  # Profile styling template (optional)
    default_message: "Default newsletter content"
    rate_limit_mh: 100                      # Max emails per hour
    filters:                                 # Saved subscriber filters (optional)
      criteria:
        status: "active"
      active: true
```

## Vault Configuration

### Setup

1. Store SMTP credentials in Secrets Manager (vault):
   ```bash
   vault write secret/mailconfig/artscroises \
     host=smtp.artscroises.com \
     port=587 \
     username=artscroises_user \
     password=artscroises_password \
     security=tls
   ```

2. Reference vault key in profile config:
   ```yaml
   artscroises:
     vault_key: "mailconfig: artscroises"
   ```

### Required SMTP Fields

The vault key must contain:
- `host`: SMTP server hostname
- `port`: SMTP server port (typically 587 for TLS, 465 for SSL)
- `username`: SMTP authentication username
- `password`: SMTP authentication password
- `security`: TLS/SSL method ("tls", "ssl", or "none")

### Error Handling

If vault key is missing or invalid:
- **Specific error**: Message includes profile name and vault key
- **No fallback**: System fails immediately (security-critical)
- **User action**: Check vault configuration or choose different profile

## Templates (Optional)

Profile styling template HTML file:

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    .profile-artscroises {
      font-family: Arial, sans-serif;
      color: #333;
      background: #f5f5f5;
    }
  </style>
</head>
<body class="profile-artscroises">
  <!-- Your template content -->
</body>
</html>
```

Editor loads template file to apply profile styling when opening newsletters.

## Filters (Optional)

### Save Filter to Profile

```python
from src.filter_persistence import FilterPersistence

config = profile_config
persistence = FilterPersistence(config)

# Save filter criteria
criteria = {"status": "active", "domain": "example.com"}
persistence.save_filter(criteria)

# Filter persists in config.yml and restores on next session
```

### Load Saved Filter

```python
filters = persistence.load_filters()
if filters:
    schema_columns = ["name", "email", "status", "domain"]
    applied = persistence.apply_filter(filters["criteria"], schema_columns)
```

### Clear Filters

```python
persistence.clear_filters()
```

## Usage Examples

### Send Email via Artscroises Profile

```bash
python src/sendMail.py --profile artscroises -s "Newsletter" newsletter.html
```

### Edit Newsletter with Profile Styling

```bash
python src/editor.py newsletter.md
# Editor loads artscroises profile styling automatically
```

### Profile Selection Behavior

- **CLI**: `--profile <name>` flag
- **Editor**: Profile dropdown remembers last used (per-session)
- **First run**: Defaults to first available profile

## Logging

Profile loading logged at `DEBUG` level (enable with verbose flag):
- Vault fetch attempts
- SMTP parameter validation
- Cache invalidation on profile switch
- Filter loading and validation

To see debug logs:
```bash
python src/sendMail.py --profile artscroises --verbose -s "Test" file.html
```

## Troubleshooting

### SMTP Connection Failed

1. Verify vault key in profile config matches stored secrets
2. Check SMTP host/port/credentials in vault
3. Verify network connectivity to SMTP server
4. Check debug logs for specific error: `--verbose`

### Profile Not Found

- Verify profile name in `--profile` flag matches config.yml
- Check config.yml YAML syntax
- Run with `--verbose` to see error details

### Filter Not Applied

1. Check filter criteria references valid schema columns
2. Look for warning messages: "Filter criteria references non-existent column"
3. Re-save filter with valid column names

## Security Considerations

- SMTP credentials stored in Secrets Manager, not config.yml
- Vault access requires authentication (per get-hc-secrets setup)
- Profile switching invalidates cached credentials
- No fallback to stale credentials if vault unreachable
