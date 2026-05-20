# Data Model: Send Dialog Improvements

**Feature**: 006-send-dialog-improvements  
**Date**: 2026-05-19  
**Phase**: 1 (Design)

## Entities

### DialogState

Represents the runtime state of a Send Mailing dialog instance.

**Fields**:
- `subject: str` — Subject line text (auto-populated from `<h1>` or filename, user-editable)
- `attachments: list[str]` — List of absolute file paths selected by user
- `test_sent: bool` — True if test email has been successfully sent in this session
- `attachment_path: str` — Path to current HTML file being sent (immutable, passed at dialog creation)

**Constraints**:
- `subject` must not exceed 50 characters
- `attachments` list is reset to empty when dialog closes and reopens
- `test_sent` is reset to False when dialog reopens for a new campaign
- `attachment_path` is read-only (cannot be changed within dialog)

**Lifecycle**:
1. Dialog created → DialogState initialized with subject auto-populated, attachments empty, test_sent=False
2. User modifies subject → subject field updated
3. User adds files → attachments list grows
4. User deletes file → attachment removed from list
5. User sends test email → sendMail returns "OK_TEST" → test_sent=True
6. User unchecks test mode (now enabled) → test_sent remains True
7. User sends bulk email → test_sent not checked again
8. Dialog closes → DialogState destroyed
9. Dialog reopens for new campaign → new DialogState created with test_sent=False

---

### SubjectField

Represents the Subject input widget behavior.

**Behaviors**:
- **Auto-population**: On dialog open, extract `<h1>` from HTML file (attachment_path) or fallback to filename
- **Truncation**: Limit extracted text to 50 characters (no ellipsis added)
- **User edit**: User can modify pre-populated text after dialog opens
- **Persistence**: Edits persist during dialog lifetime; lost on close
- **Validation**: No validation required; accepts any text up to 50 chars

**Implementation notes**:
- Use BeautifulSoup to extract first `<h1>` tag text content
- Strip HTML tags from `<h1>` text (e.g., `<h1><b>Title</b></h1>` → "Title")
- Filename fallback: `Path(attachment_path).stem` (removes directory and extension)
- Store extraction logic in method: `_extract_subject_from_html(html_path: str) -> str`

---

### AttachmentList

Represents the list of files attached to the mailing.

**Fields**:
- `files: list[str]` — Absolute file paths selected by user
- `display_names: dict[str, str]` — Mapping from path to display name (filename only)

**Behaviors**:
- **Add files**: File picker dialog allows selecting one or more files
  - User selects files → added to list in order selected
  - Duplicate paths: Allowed (user responsibility)
- **Remove file**: Per-row delete button removes file from list
  - File removed immediately on delete click
  - List updates to reflect removal
- **Display**: Show filename (not full path) in list
  - Truncate long filenames if needed (implementation detail)
- **Persistence**: List cleared when dialog closes
- **Reset**: List starts empty for each new campaign

**Implementation notes**:
- Use `QListWidget` or custom `QAbstractListModel` for list display
- File picker: `QFileDialog.getOpenFileNames()` for multi-select
- Delete button: Per-row widget or model-based delete action
- Store paths as absolute paths internally (for sendMail CLI)
- Display names derived from `Path(absolute_path).name`

---

### TestModeCheckbox

Represents the Test checkbox state machine.

**States**:
1. **Locked (initial)**: Checkbox checked, cannot be unchecked by user
   - Condition: `test_sent == False`
   - UI: Checkbox ticked, toggle signal blocked if user tries to uncheck
   - Intent: Force user to send test before bulk send

2. **Unlocked (after test)**: Checkbox can be checked or unchecked by user
   - Condition: `test_sent == True`
   - UI: Checkbox ticked (default), user can uncheck to proceed with bulk send
   - Intent: Allow bulk send after test has been sent

3. **Reset (on close)**: Checkbox returns to locked state
   - Condition: Dialog closes and reopens for new campaign
   - State: test_sent reset to False, checkbox locked again
   - Intent: Enforce test mode for each campaign

**State Machine**:
```
[Locked: test_sent=False]
    ↓ (user clicks uncheck)
    ↓ (signal blocked, checkbox auto-rechecks)
    ↓ (user sends test email)
[Locked: test_sent=False] → [Unlocked: test_sent=True]
    ↓ (user unchecks)
[Unlocked, unchecked: test_sent=True]
    ↓ (user clicks OK to send)
    ↓ (dialog closes)
    ↓ (dialog reopens for new campaign)
[Locked: test_sent=False] ← reset
```

**Implementation notes**:
- Instance variable: `self._test_sent: bool`
- Toggle handler: `_on_test_mode_toggled()` blocks unchecking if `_test_sent == False`
- Success detection: Check `_send_result_is_success(result)` for "OK_TEST" return
- Reset on close: Dialog's DialogState destroyed, recreated on open

---

### SendMailDialogArgs

Represents arguments passed to sendMail CLI.

**Current fields** (from existing code):
- `profile: str` — Profile name from config
- `conf: dict` — Config data
- `attachment: str` — HTML file to send
- `subject: str` — Email subject
- `message: str` — Email body template
- `database: str` — Subscriber database path
- `filter: str` — YAML filter
- `test: bool` — Test mode flag
- `password: str` — Email account password
- Other flags (verbose, do_not_send, etc.)

**New field**:
- `attachments: list[str]` — New field for multi-file attachments
  - Type: list of absolute file paths
  - Source: AttachmentList.files
  - Passed to sendMail CLI via `--attachment` or new arg

**Validation**:
- All attachment file paths must exist (validate before building args)
- Subject must not exceed 50 characters
- No other validation required

---

## Relationships

```
DialogState
├── SubjectField (1:1)
├── AttachmentList (1:1)
├── TestModeCheckbox (1:1)
└── SendMailDialogArgs (1:1, built from DialogState at send time)
```

---

## State Transitions

### Subject Field Lifecycle
```
1. Dialog.__init__()
   → _extract_subject_from_html(attachment_path)
   → subject_input.setText(extracted_subject)

2. User edits subject_input
   → DialogState.subject updated in real-time

3. Dialog closes
   → DialogState destroyed
```

### Attachment List Lifecycle
```
1. Dialog.__init__()
   → attachments = []

2. User clicks "Add"
   → QFileDialog.getOpenFileNames()
   → user selects files
   → files added to list

3. User clicks delete per row
   → file removed from list

4. Dialog closes
   → attachments list discarded
```

### Test Mode Checkbox Lifecycle
```
1. Dialog.__init__()
   → test_sent = False
   → test_check.setChecked(True)
   → test_check.setEnabled(False) OR signal blocked

2. User tries to uncheck
   → _on_test_mode_toggled(False) called
   → if test_sent == False: block toggle, recheck

3. User sends test email
   → _menu_send() calls sendMail
   → result = "OK_TEST"
   → test_sent = True
   → test_check.setEnabled(True)

4. User unchecks test_check
   → signal allowed through
   → test_check.setChecked(False)

5. User sends bulk email
   → sendMail runs with test=False

6. Dialog closes, reopens
   → DialogState recreated
   → test_sent = False
   → test_check locked again
```

---

## Validation Rules

**Subject**:
- No length validation (automatic truncation to 50 chars at extraction)
- Any Unicode characters allowed
- No whitespace stripping (user edits preserved as-is)

**Attachments**:
- File must exist on disk (validate before send)
- File path must be absolute (convert from picker result if needed)
- No file type restrictions (user responsibility)
- No size limits (user responsibility)

**Test Mode**:
- Automatically enforced by UI (checkbox locked)
- No manual validation required
