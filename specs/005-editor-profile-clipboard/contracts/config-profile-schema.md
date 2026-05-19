# Contract: Config Profile Schema

**Purpose**: Define the structure of email profiles in config.yml

**Format**: YAML (existing config.yml format)

## Profile Structure

```yaml
profiles:
  profile_name:
    default_document_path: "/path/to/documents"  # OPTIONAL
    smtp_host: "smtp.example.com"                # REQUIRED
    smtp_port: 587                               # REQUIRED
    smtp_user: "user@example.com"                # REQUIRED
    smtp_password: "password"                    # REQUIRED (or env var)
    imap_host: "imap.example.com"                # OPTIONAL
    imap_port: 993                               # OPTIONAL
    # ... other existing fields remain unchanged
```

## Field Specifications

### `profile_name`
- **Type**: String (key in profiles dict)
- **Constraints**: Non-empty, alphanumeric + underscores/hyphens
- **Example**: `cambristi`, `internal-team`, `newsletter_subscribers`

### `default_document_path`
- **Type**: String (file system path) | Null
- **Constraints**: 
  - Optional field (may be absent or null)
  - If present: Must be absolute path or expandable (e.g., ~/Documents)
  - Directory must exist or be creatable (soft requirement - UI handles gracefully)
- **Example**: `/Users/xavier/Documents/campaigns`, `~/Dropbox/sendMail/templates`
- **Fallback**: If missing or invalid, editor uses last accessed directory or home dir

### Existing Fields
- `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`: No changes (backward compatible)
- `imap_host`, `imap_port`: No changes (backward compatible)
- Any future profile fields: Editor ignores unknown fields gracefully

## Backward Compatibility

✓ Profiles without `default_document_path` are valid and supported  
✓ Existing config.yml files remain unchanged  
✓ No schema migration required  
✓ No breaking changes to profile structure  

## Contract Enforcement

**Editor behavior**:
- If profile missing `default_document_path`: File browser uses fallback (home dir)
- If `default_document_path` invalid: Log warning, use fallback
- Unknown profile fields: Silently ignored (forward compatible)

**sendMail.py behavior**:
- Continues to work as before; `default_document_path` is editor-only concern
- No dependency on new field

## Example Valid Configurations

```yaml
# Minimal profile (backward compatible)
profiles:
  basic:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_user: user@gmail.com
    smtp_password: password123

# Profile with editor path
profiles:
  cambristi:
    default_document_path: /Users/xavier/Documents/cambristi_campaigns
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_user: cambristi@example.com
    smtp_password: pass456

# Profile with expandable path
profiles:
  newsletters:
    default_document_path: ~/Dropbox/sendMail/newsletters
    smtp_host: smtp.sendgrid.net
    smtp_port: 587
    smtp_user: sendgrid_user
    smtp_password: sg_key_xyz
```

## Testing Strategy

- Valid profile without `default_document_path`: Editor starts, file browser uses fallback
- Valid profile with absolute path that exists: File browser navigates to path
- Valid profile with path that doesn't exist: Warning logged, fallback used
- Invalid path characters: Gracefully handled (not path traversal vulnerability)
