# Research: Send Dialog Improvements

**Feature**: 006-send-dialog-improvements  
**Date**: 2026-05-19  
**Status**: Complete

## 1. Subject Auto-Population

### Finding: HTML Document Context Available

**Decision**: Extract `<h1>` from the dialog's attachment_path parameter.

**Rationale**: Dialog receives the HTML file path in `__init__` as `attachment_path` parameter (from editor.py line 3434). File is guaranteed to exist (editor saves before opening dialog at line 3422-3426). Reading it with BeautifulSoup (already a project dependency) to extract `<h1>` text is straightforward.

**Alternatives considered**:
- Passing document content via dialog parameter — less reliable (requires editor refactoring, document state management)
- Reading file at send time — too late, subject already in form
- Using regex on file — fragile for malformed HTML

**Implementation location**: `src/editor.py`, in `_SendDialog.__init__()` or new helper method

**Key code reference**:
- Line 373: `attachment_path` parameter passed to dialog
- Line 429-431: Attachment label displays filename (can reuse path for HTML reading)
- Line 433-434: Subject input field ready to be pre-populated

### Implementation Details

- Use `BeautifulSoup` to parse HTML (already in `requirements.txt`)
- Extract first `<h1>` tag's text content (strip HTML tags if present)
- Fallback: Use filename (without extension, without path)
- Truncate to 50 characters max
- Apply in `_SendDialog.__init__()` after subject_input widget created

### Testable Behavior

- Dialog opens with subject pre-filled from `<h1>` text
- Subject respects 50-char limit
- User can edit subject after population
- Changes persist in subject_input field

---

## 2. File Attachment Widget

### Finding: Dialog Layout Has Space for Widget

**Decision**: Add attachment list widget to right side of HTML input, above filter widget.

**Rationale**: Dialog uses `QFormLayout` (line 410) with form fields. Current structure:
- HTML file shown as read-only label (line 429-431)
- Subject input (line 433-434)
- Message, Body, Database inputs
- Filter widget takes significant vertical space
- Buttons at bottom

Spec requests attachment widget positioned "right of HTML file input, above filter widget". In form layout, we can add a horizontal row with HTML label on left and attachment widget on right.

**Alternatives considered**:
- Pop-up separate dialog for attachments — disrupts workflow, more clicks
- Add below HTML input — wastes vertical space, attachment is tied to file
- Replace attachment label with file picker button — loses filename visibility

**Implementation location**: `src/editor.py`, in `_SendDialog.__init__()` after line 431

### Implementation Details

- Create custom attachment list widget (new class or QListWidget subclass)
- Replace static `attachment_label` with two-column layout:
  - Left: HTML filename label (current behavior)
  - Right: "Add" button + list view with delete controls per file
- File picker: `QFileDialog.getOpenFileNames()` to select multiple files
- List display: file names with delete button per row
- State: Store in `self.attachments` list; clear when dialog closes
- Integration: Pass attachment list to `build_args()` for sendMail CLI

### Testable Behavior

- "Add" button opens file picker
- Selected files appear in list below button
- Delete button removes individual file
- Attachment list stays visible, doesn't scroll away (position above filter)
- List persists until dialog closes/reopens

---

## 3. Test Mode Enforcement

### Finding: Test Success Detected via CLI Return Value

**Decision**: Lock test checkbox until `sendMail.process_profile()` returns "OK_TEST".

**Rationale**: Test success is detectable from sendMail return value at editor.py line 3407: `if status.upper() in {"OK", "OK_TEST"}`. "OK_TEST" indicates test-mode send succeeded. We can detect this in `_menu_send()` and unlock test checkbox for subsequent sends.

**Alternatives considered**:
- Poll sendMail.log for test completion — fragile (parsing, timing)
- Add callback to sendMail CLI — requires changes to sendMail.py, out of scope
- Disable send button until test — confusing UX, prevents accidental sends but doesn't prevent them

**Implementation location**: `src/editor.py`, in `_SendDialog` and `_menu_send()`

### Implementation Details

- Add instance variable `self._test_sent = False` to dialog state
- In `__init__()`: Check test_check by default (line 563), connect to toggle handler
- In toggle handler: Prevent unchecking if `_test_sent is False` (block toggle signal, auto-recheck)
- In `_menu_send()`: After send succeeds, check result for "OK_TEST"
  - If true, set `dialog._test_sent = True`, unlock test checkbox
  - If false, keep locked
- On dialog close/reopen: Reset `_test_sent` to False (fresh state per campaign)

**Dialog lifecycle**:
1. Dialog opens → test_check checked, locked
2. User attempts uncheck → signal blocked, checkbox stays checked
3. User sends test → success detected → checkbox unlocked
4. User can uncheck to send to full list
5. Dialog closes, reopens → test_check reset to checked, locked

### Testable Behavior

- Test checkbox starts checked, cannot be unchecked
- After successful test send, can uncheck
- Sending without test (test locked) is prevented by UX (button state or validation)
- Dialog reset forces test-first on next campaign

---

## 4. Integration Points

### sendMail CLI

Current: `sendMail.process_profile(args)` returns "OK", "OK_TEST", "ERROR", or None

**Required**: Pass attachment list via args. Check existing arg handling for attachments.

**Finding**: `sendMail.py` has `--attachment` / `-a` flag (CLI tool, not WYSIWYG editor). Dialog's `build_args()` method constructs args for CLI.

**Decision**: Add `attachments` field to args (already supported by sendMail CLI).

---

## Summary

| Requirement | Implementation | Status |
|------------|-----------------|--------|
| Extract `<h1>` from HTML | Read file with BeautifulSoup in `_SendDialog.__init__()` | Ready |
| Truncate subject to 50 chars | Python string slicing | Ready |
| Fallback to filename | `Path(attachment_path).stem` | Ready |
| File picker button | `QFileDialog.getOpenFileNames()` | Ready |
| Attachment list display | New QListWidget-based widget in form layout | Ready |
| Delete per-file control | List item with delete button | Ready |
| Test mode lock | Dialog state `_test_sent` flag, toggle handler, reset on close | Ready |
| Test success detection | Check sendMail return value for "OK_TEST" | Ready |

No external research needed. All findings confirmed in existing codebase.
