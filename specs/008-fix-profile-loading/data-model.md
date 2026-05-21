# Data Model: Fix Profile Loading and Configuration

**Date**: 2026-05-21  
**Feature**: Fix Profile Loading and Configuration  
**Scope**: Profile configuration, SMTP parameters, filters, logging

## Entities

### Profile

Represents an email configuration/profile with settings for a specific email account or mailing list.

**Fields**:
- `name` (string): Profile identifier (e.g., "artscroises", "cambristi")
- `vault_key` (string): Secrets manager key for SMTP credentials (e.g., "mailconfig: artscroisesmailing")
- `smtp_host` (string, runtime): SMTP server hostname (loaded from vault)
- `smtp_port` (int, runtime): SMTP port (loaded from vault)
- `smtp_user` (string, runtime): SMTP authentication username (loaded from vault)
- `smtp_password` (string, runtime): SMTP authentication password (loaded from vault)
- `smtp_security` (string): "tls" | "ssl" | "none"
- `template_file` (string, optional): Path to HTML template for styling
- `rate_limit_mh` (int): Messages per hour limit
- `subscriber_source` (string): "sheets" | "csv" | "file"
- `filters` (object, optional): Saved filter criteria [NEW]
  - `name` (string): Filter name
  - `criteria` (object): Filter match rules
  - `active` (bool): Whether filter is enabled

**Relationships**:
- Profile → SMTP (one-to-one via vault_key)
- Profile → Template (zero-to-one via template_file)
- Profile → Filter (zero-to-many via filters array)

**Persistence**:
- Stored in config.yml as YAML
- SMTP parameters loaded from vault at profile selection time
- Filters persisted to config.yml when user saves

**State Transitions**:
1. Unloaded → Selected (read from config.yml)
2. Selected → SMTPLoaded (vault key resolved, credentials fetched)
3. SMTPLoaded → Ready (template loaded if exists, can send emails)

### SMTP Configuration (Runtime)

Credentials loaded from vault by get-hc-secrets.

**Fields**:
- `host` (string): SMTP server
- `port` (int): Connection port
- `username` (string): Auth user
- `password` (string): Auth password
- `encryption` (string): TLS/SSL method
- `timeout` (int, seconds): Connection timeout

**Validation Rules**:
- host: non-empty, valid hostname/IP
- port: 1-65535
- username, password: non-empty if SMTP requires auth
- timeout: 1-300 seconds

**Errors**:
- Missing vault key: raise ValueError with key name
- Vault fetch fails: raise ConnectionError with specific reason
- Invalid SMTP params: raise ValidationError with field details

### Filter

Represents subscriber filtering criteria, optionally persisted per profile.

**Fields**:
- `name` (string): User-friendly filter name
- `criteria` (dict): Match conditions (column → value patterns)
- `active` (bool): Whether to apply this filter
- `created_at` (datetime): When filter was created
- `modified_at` (datetime): Last modification time

**Relationships**:
- Filter → Profile (many-to-one, via profile.filters)

**Persistence**:
- Stored in config.yml under profile.filters
- Loaded on profile initialization
- User can save current filters to profile via explicit request

### Log Entry (Conceptual)

Logging throughout application, with debug-level diagnostic info.

**Levels**:
- **DEBUG**: Diagnostic info (profile loading steps, vault fetches, filter matching details)
- **INFO**: User-relevant events (send started, subscriber count, rate limit applied)
- **WARNING**: Non-critical issues (retry on SMTP fail, incomplete profile)
- **ERROR**: Critical failures (SMTP connection failed, vault unreachable)

**Changes**:
- Replace all debug-diagnostic log.info calls with log.debug
- Keep user-relevant log.info calls
- Structured logging format: `logger.{level}("{context}: {message}", extra={context_dict})`

## Validation Rules

### Profile Validation

- `name`: Required, matches pattern `[a-z0-9_-]+`
- `vault_key`: Required for SMTP profiles
- `smtp_security`: One of "tls", "ssl", "none"
- `rate_limit_mh`: Positive integer, 1-10000
- `subscriber_source`: One of "sheets", "csv", "file"
- Vault key must resolve to valid SMTP params (tested at profile load time)

### Filter Validation

- `criteria`: At least one condition
- Condition keys must match schema columns
- Condition values: type-appropriate (string/int/bool per schema)

### Config File Validation

- config.yml must be valid YAML
- Each profile section must have required fields
- Vault keys must follow pattern "mailconfig: [a-z0-9_-]+"

## Schema Integration

Filters use existing schema system (schema_provider.py, schema_cache.py):
- Subscriber database columns come from CSV header or Sheets
- Filter criteria must match schema columns
- Schema caching applies to filter validation

## Testing Strategy

### Unit Tests

- Profile loading from config.yml
- Vault key lookup and SMTP param extraction
- Filter serialization/deserialization
- Log level categorization (debug vs info)

### Integration Tests

- End-to-end profile selection → SMTP connect
- Editor file open with profile styling
- Filter save/restore across sessions
- Config file updates persist correctly

### Contract Tests

- Vault API contract (get-hc-secrets request/response)
- Profile schema (config.yml YAML structure)
