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
| `src/googleDriveLib.py` | Google Drive integration (download/upload/rename)                                 |
| `config.yml`            | Email profiles — SMTP/IMAP settings, rate limits, filtering rules                 |

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

### Editor Core Classes (005-editor-profile-clipboard feature)

**ConfigLoader**: Loads email profiles from config.yml and provides access to profile metadata
- `load_profiles_from_config()` — parse YAML and create profile objects
- `get_profiles()` — return filtered profile list with metadata
- Expands user paths (~) and validates file existence

**EditorSession**: Tracks active profile selection and document state for session persistence
- `active_profile_name` — currently selected profile
- `active_profile_default_path` — profile's documents directory
- `save_to_file()` / `load_from_file()` — persist session to `~/.claude/editor-session.json`
- Restored on editor startup to preserve user's last profile selection

**ClipboardProcessor** & **ClipboardOperation**: Analyze pasted clipboard content
- `analyze_paste(html_content, plain_text)` — detect content type and extract URLs
- Returns: `content_type` (html|plain), `has_html_links` (bool), `detected_urls` (list[str])
- URL detection via regex: `https?://` and `ftp://` schemes

**EditorPasteHandler**: Process clipboard analysis results and apply URL linkification
- Receives clipboard_analyzed signal from JavaScript (QWebChannel)
- Calls JavaScript to linkify detected plain-text URLs

**EditorBridge** (extended): QWebChannel bridge for JavaScript↔Python communication
- `clipboard_analyzed` signal — emitted when clipboard content analyzed
- `on_clipboard_analyzed(content_type, has_html_links, detected_urls)` — process paste events
- `_apply_url_linkification(urls)` — format plain URLs as links in editor

**Stylesheet Management** (US4: Apply Profile Stylesheet on Selection):
- `_on_profile_selected(profile_name)` — load and apply profile's CSS stylesheet
- `_resolve_stylesheet_path(styles_value)` — expand user paths, validate existence
- `_apply_profile_stylesheet(css_path)` — inject CSS into Quill editor canvas
- `_clear_profile_stylesheet()` — remove previous stylesheet before switching profiles
- Stylesheet path read from profile's `styles:` config key in config.yml

### Send Dialog Enhancements (006-send-dialog-improvements feature)

**_SendDialog Class Extensions**:
- `_extract_subject_from_html(html_path: str)` — extract subject from `<h1>` heading or filename (max 50 chars)
- `_on_add_attachment()` — file picker callback to add files to attachment list
- `_on_remove_attachment(row: int)` — remove individual file from attachment list
- `_on_attachment_context_menu(pos)` — context menu (right-click) to delete attachments
- `_update_test_mode_lock()` — enforce test checkbox locked until test email sent
- `_unlock_test_mode()` — unlock test checkbox after successful test send

**Subject Auto-Population**:
- Extracts first `<h1>` heading text from HTML document on dialog open
- Fallback to filename (without extension) if no `<h1>` found
- Truncates to 50 characters maximum
- User can edit after population

**File Attachments**:
- "Add File(s)" button opens multi-file picker
- Selected files displayed in list widget (right of HTML input, above filter)
- Right-click context menu to delete individual files
- Attachment list cleared when dialog reopens for new campaign
- Files passed to sendMail CLI via `namespace.attachment` in build_args()

**Test Mode Enforcement**:
- Test checkbox checked by default and locked (disabled) on dialog open
- Remains locked until test email successfully sent (returns "OK_TEST")
- EditorWindow._menu_send() detects "OK_TEST" and calls dialog._unlock_test_mode()
- After unlock, user can uncheck to send to full list
- Resets to checked (locked) on dialog reopen for new campaign

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
- Python 3.12+ + PyQt6 (≥6.7.0), pyyaml, gspread, google-api-python-clien (004-visual-filter-builder)
- N/A (filter definitions stored in YAML config) (004-visual-filter-builder)
- Python 3.12+ + PyQt6 (≥6.7.0), PyQt6-WebEngine (≥6.7.0), Quill.js v2 (via HTML5), pyyaml, google-api-python-clien (005-editor-profile-clipboard)
- YAML (config.yml), Markdown/HTML files (documents) (005-editor-profile-clipboard)
- Python 3.12+ + PyQt6 (≥6.7.0), pyyaml, google-api-python-clien (006-send-dialog-improvements)
- N/A (state tracked in dialog instance, not persisted) (006-send-dialog-improvements)

## Recent Changes
- 004-visual-filter-builder: Added Python 3.12+ + PyQt6 (≥6.7.0), pyyaml, gspread, google-api-python-clien
