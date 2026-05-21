# sendMail — Project Guide

## What this project does

Bulk email campaign management tool for organizations (mailing lists, newsletters, membership). Supports SMTP and Gmail API backends, Google Sheets/CSV subscriber databases, Google Drive attachments, HTML/Markdown templating, and rate limiting.

## Entry point

```bash
python src/sendMail.py --profile <profile_name> -s "Subject" [options] [files...]
```

Key flags: `-t` (test mode), `-x` (dry run), `-db` (CSV database), `-f/-to` (index range), `-mh` (rate limit), `-md2html` (markdown→HTML).

## Key files

| File                    | Role                                                                              |
|-------------------------|-----------------------------------------------------------------------------------|
| `src/sendMail.py`       | Main application — email logic, subscriber filtering, templating, HTML processing |
| `src/editor.py`         | WYSIWYG HTML editor GUI (PyQt6 + Quill.js) — compose/edit newsletters             |
| `src/profile_manager.py` | Profile loading and vault integration — SMTP credential management                |
| `src/googleDriveLib.py` | Google Drive integration (download/upload/rename)                                 |
| `config.yml`            | Email profiles — SMTP/IMAP settings, rate limits, filtering rules                 |

## Profile Loading Architecture (008-fix-profile-loading)

### Overview

Profiles decouple email configurations from code. Each profile defines SMTP settings, rate limits, filters, and styling. SMTP credentials load from a secure vault (get-hc-secrets) at runtime.

### Components

**Profile Class** (`src/profile_manager.py`):
- Loads SMTP params from vault: `vault_key` → secret name → fetch from vault
- Caches SMTP params per-session (invalidated on profile switch)
- Validates required fields before returning params

**sendMail Integration** (`src/sendMail.py`):
- Extracts vault_key from config (checks: vault_key, MAILCONFIG, mailconfig)
- Creates Profile instance and fetches vault secrets
- Merges vault params with config (vault values override defaults)
- Passes merged config to SMTP connection

**Editor Integration** (`src/editor.py`):
- Profile dropdown to switch profiles
- Auto-loads profile styling and SMTP settings
- Applies profile-specific CSS from templates
- Caches profile within editor session

### Data Flow

```
config.yml (profile def)
  ↓ vault_key: "mailconfig: artscroises"
Profile.load_smtp_from_vault()
  ↓ extract key: "artscroises"
get_secret("artscroises")  ← vault API
  ↓ returns: {smtp_host, smtp_port, username, password, ...}
merge: {**vault_result, **config}
  ↓
SMTP connection params ready
```

### Key Design Decisions

1. **Vault-first**: Credentials always from vault if configured; no fallback to stale cached values
2. **Per-profile caching**: Each session maintains one Profile instance; cache invalidated on switch
3. **Fail-safe**: Missing vault key raises ProfileLoadError (not silent failure)
4. **Config override**: Profile config values take precedence over vault (for debugging/testing)
5. **TLS compatibility**: TLS 1.2 minimum (1.3 too strict for OVH); certificate verification disabled for compatibility

### Testing

- **Unit tests** (`tests/test_profile_loading.py`): Profile class, vault mocking, cache behavior
- **Integration tests** (`tests/integration/test_profile_flow.py`): Full flow (profile → vault → SMTP)
- **Logging tests**: Verify debug-level diagnostic messages don't leak to INFO level

## WYSIWYG Editor

Launch the editor independently (never imported by `src/sendMail.py` — keeps CLI lightweight):

```bash
python src/editor.py                      # blank document
python src/editor.py data/template.md     # open the newsletter template
python src/editor.py data/20260420.md     # edit an existing newsletter
```

The editor saves **both** `.md` and `.html` simultaneously.  
Then pass the HTML to sendMail:

```bash
python src/sendMail.py --profile cambristi data/20260420.html
```

### Editor assets (`editor_assets/`)

| File | Source |
|---|---|
| `quill.js` | Quill v2 bundled from CDN (MIT) — do not replace without updating `editor.html` |
| `quill.snow.css` | Quill Snow theme CSS |
| `qwebchannel.js` | Copied from Qt install: `find $(brew --prefix) -name qwebchannel.js` |
| `editor.html` | Host page with Quill init and QWebChannel bootstrap |

To refresh `qwebchannel.js` after a Qt upgrade:

```bash
cp "$(find $(brew --prefix) -name qwebchannel.js | head -1)" editor_assets/qwebchannel.js
```

### New dependencies added for the editor

`PyQt6>=6.7.0`, `PyQt6-WebEngine>=6.7.0`, `html2text>=2024.2.26`

### Building the editor binary

```bash
pyinstaller editor.spec   # produces dist/sendMailEditor/ (+ .app on macOS)
```

Note: the editor binary is ~80–150 MB due to Chromium (QWebEngine). It is built separately from `sendMail.spec`.

## Package manager & dependencies

`pyproject.toml` (PEP 621, Python 3.12+) + `requirements.txt`.

Core: `google-api-python-client`, `gspread`, `beautifulsoup4`, `markdown2`, `pillow`, `pyyaml`, `get-hc-secrets`
Dev: `pytest`, `pytest-cov`, `mypy`, `ruff`, `behave`

## Running tests

```bash
pytest tests/ -v --cov=. --cov-report=html
```

Tests live in `tests/` (5 files, 18+ classes covering Dict2Class, file utils, message formatting, filtering, email building, HTML processing, SMTP/Gmail, arg parsing, Google Drive).

## Linting & formatting

CI enforces:
- `flake8` — max-complexity=10, max-line-length=127
- `black` — code format checks
- `mypy` — type checking (ignore-missing-imports=true in pyproject.toml)
- `ruff` — linting

## CI

- `.github/workflows/tests.yml` — multi-platform (Ubuntu/macOS/Windows, Python 3.10–3.11), pytest + Codecov upload
- `.github/workflows/main.yml` — PyInstaller cross-platform builds (triggered manually with version input)

## Conventions

- `Dict2Class` utility for dynamic object creation from dicts
- `${field}` syntax for template variable substitution
- MIME auto-detection for attachments
- Inline images via base64/CID
- Google Sheets/Drive via service accounts
- Logging to `sendMail.log`
- snake_case naming throughout

## Tool Enforcement
- This project uses `mypy --strict` and `ruff check .`.
- Never use `type: ignore` without a human-approved justification.
- All function signatures must be fully typed.

## Active Technologies
- Python 3.12+ + google-api-python-client, gspread, beautifulsoup4, markdown2, pillow, pyyaml, get-hc-secrets, PyQt6, PyQt6-WebEngine (008-fix-profile-loading)
- YAML config files (config.yml), Google Sheets, Google Drive, local filesystem (008-fix-profile-loading)

## Recent Changes
- 008-fix-profile-loading: Added Python 3.12+ + google-api-python-client, gspread, beautifulsoup4, markdown2, pillow, pyyaml, get-hc-secrets, PyQt6, PyQt6-WebEngine
