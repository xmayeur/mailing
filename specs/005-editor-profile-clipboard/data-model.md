# Phase 1: Data Model & Entities

**Feature**: Editor Profile & Clipboard Enhancements  
**Branch**: `005-editor-profile-clipboard`

## Entity Model

### 1. Profile

**Purpose**: Represents an email configuration profile loaded from config.yml

**Fields**:
- `name` (str): Profile identifier (e.g., "cambristi", "internal", "newsletter")
- `default_document_path` (str | None): Directory path where documents for this profile are stored
- `smtp_config` (dict): SMTP settings (from config.yml, not modified by editor)
- `imap_config` (dict | None): IMAP settings if configured

**Validation Rules**:
- `name` must not be empty
- `default_document_path` must be absolute or expandable path (e.g., `~/Documents/profiles`)
- If `default_document_path` contains invalid/inaccessible path, log warning and use fallback

**Source of Truth**: config.yml profiles section

**Lifecycle**:
- Loaded once at editor startup via ConfigLoader.load_profiles()
- Read-only during editor session (profile config is static)
- User selects active profile via UI dropdown

---

### 2. EditorSession

**Purpose**: Tracks editor runtime state (active profile, file path, unsaved changes)

**Fields**:
- `active_profile_name` (str | None): Currently selected profile name
- `active_document_path` (str | None): Full path to document being edited
- `active_profile_default_path` (str | None): Cached default_document_path of active profile
- `unsaved_changes` (bool): Document has unpersisted changes
- `window_geometry` (dict): Editor window position/size for restoration

**Validation Rules**:
- `active_profile_name` must match a profile from loaded config
- `active_document_path` must be valid file or None
- Window geometry must have valid x, y, width, height integers

**Persistence**: `.claude/editor-session.json`

**Lifecycle**:
- Created on editor startup, loaded from session file if exists
- Updated when user:
  - Selects profile (active_profile_name, active_profile_default_path)
  - Opens file (active_document_path)
  - Closes editor (saved for next session)

---

### 3. ClipboardOperation

**Purpose**: Represents a single paste event with detected content type and metadata

**Fields**:
- `content_type` (str): One of "html_rich", "plain_text", "markdown"
- `raw_text` (str): Clipboard text content
- `raw_html` (str | None): HTML clipboard format (if available)
- `detected_urls` (list[str]): Plain-text URLs found in content (http://, https://, ftp://)
- `has_existing_links` (bool): Content already contains HTML link markup
- `timestamp` (float): Paste event timestamp (for diagnostics)

**Validation Rules**:
- `content_type` must be one of the defined types
- `detected_urls` list must contain only valid URL strings
- If `content_type` == "html_rich", `raw_html` must not be None

**Lifecycle**:
- Created when Quill paste event fires (via QWebChannel)
- Processed by ClipboardProcessor to extract URLs, determine content type
- Passed to editor paste handler to insert with appropriate formatting
- Discarded after paste completes

---

### 4. Document

**Purpose**: Editor document representation (implicit, managed by Quill.js)

**Fields** (from Quill Delta format):
- `ops` (list): Array of insert/format operations
- `metadata` (dict): Optional custom fields (saved to markdown frontmatter)
  - `profile_used` (str): Profile name used when document created
  - `created_at` (str): ISO timestamp
  - `modified_at` (str): ISO timestamp

**File Formats**:
- `.md`: Markdown with YAML frontmatter + content
- `.html`: HTML export from Quill Delta

**Validation Rules**:
- Document size must be <50MB (practical limit for editor)
- YAML frontmatter must be valid (if present)
- HTML must be well-formed (Quill-generated)

---

## Relationships

```
EditorSession
├─ has active_profile_name → Profile
├─ references active_document_path → Document
└─ tracks unsaved_changes flag

Profile
└─ provides default_document_path → file system directory

ClipboardOperation
└─ processes input → Document (paste insertion)
```

---

## State Transitions

### Profile Selection Flow

```
User clicks Profile Dropdown
  ↓
ProfileSelector emits selectionChanged(profile_name)
  ↓
EditorSession.set_active_profile(profile_name)
  ├─ Updates active_profile_name
  ├─ Caches default_document_path
  └─ Updates file browser root directory
  ↓
File browser navigates to default_document_path
  ↓
EditorSession saved to disk
```

### Paste Operation Flow

```
User Ctrl+V in editor
  ↓
Quill paste event → QWebChannel bridge
  ↓
ClipboardProcessor.analyze_paste()
  ├─ Extract raw_text, raw_html
  ├─ Detect content_type (html_rich, plain_text, markdown)
  ├─ Find plain-text URLs (if plain_text)
  └─ Returns ClipboardOperation
  ↓
EditorPasteHandler.handle_paste(clipboard_op)
  ├─ If html_rich: Insert via Quill HTML paste
  ├─ If plain_text with URLs: Linkify URLs then insert
  └─ If plain_text no URLs: Insert as-is
  ↓
Quill updates document Delta
  ↓
Document marked with unsaved_changes = True
```

---

## Implementation Notes

- **Profile loading**: Use existing yaml module; parse config.yml profiles section
- **Session persistence**: Use Python's configparser or json module; store in `.claude/editor-session.json`
- **Clipboard access**: PyQt6.QtGui.QClipboard, QMimeData
- **URL detection**: Regex pattern for http://, https://, ftp:// schemes
- **Document format**: Existing markdown/HTML export logic in editor.py; extend metadata handling
