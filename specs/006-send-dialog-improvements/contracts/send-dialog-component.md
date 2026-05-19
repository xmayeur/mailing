# UI Component Contract: Send Mailing Dialog

**Feature**: 006-send-dialog-improvements  
**Component**: `_SendDialog` (PyQt6 QDialog)  
**Location**: `src/editor.py`

## Overview

The Send Mailing dialog (`_SendDialog` class) is the primary UI for composing and sending email campaigns. This contract specifies the three new/enhanced features: subject auto-population, file attachments, and test mode enforcement.

---

## Component Interface

### Initialization

```python
class _SendDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        attachment_path: str,          # HTML file being sent
        config_path: str,              # Path to sendMail config
        config_data: dict | None = None,
        initial_profile: str = "default",
    ) -> None: ...
```

**On creation**:
- Extract subject from HTML file's `<h1>` heading
- Populate `subject_input` field with extracted text (truncated to 50 chars)
- Display HTML filename in attachment label
- Initialize attachment list as empty
- Set test checkbox to checked (locked state)

---

## Feature 1: Subject Auto-Population

### Public Interface

**Property/Field**: `subject_input: QLineEdit`

**Behavior**:
1. On dialog creation, extract `<h1>` text from the HTML file at `attachment_path`
2. Populate `subject_input` with extracted text (truncated to 50 characters)
3. If no `<h1>` found, use filename of `attachment_path` (without directory or extension)
4. User can edit the field after population
5. Edits persist in the dialog lifetime

**Constraints**:
- Extraction must complete in <200ms (performance requirement)
- Extract only the first `<h1>` tag
- Strip HTML formatting from `<h1>` text (plain text only)
- Truncate to 50 characters (no ellipsis marker)

### Internal Methods

```python
def _extract_subject_from_html(html_path: str) -> str:
    """
    Extract subject line from HTML <h1> tag or filename.
    
    Returns: Subject text (up to 50 chars)
    """
    # 1. Parse HTML with BeautifulSoup
    # 2. Find first <h1> tag
    # 3. Get plain text (strip HTML)
    # 4. Truncate to 50 chars
    # 5. If no <h1>, return filename (without extension, truncated)
```

---

## Feature 2: File Attachments

### Public Interface

**UI Controls**:
- **Add button**: Opens file picker to select one or more files
- **List widget**: Displays selected files with display names
- **Delete button** (per row): Removes individual file from list

**Property/Field**: `attachments: list[str]`

**Behavior**:
1. User clicks "Add" button
2. File picker dialog opens (`QFileDialog.getOpenFileNames()`)
3. User selects one or more files and confirms
4. Selected files appear in list widget below the HTML file input
5. Each list item shows the filename (not full path)
6. Each list item has a delete button
7. Clicking delete removes the file from the list immediately
8. List persists until dialog closes
9. On dialog close/reopen, attachment list resets to empty

**Position**: Right side of HTML file input, above filter widget (as specified in feature requirements)

### Internal Methods

```python
def _on_add_attachment(self) -> None:
    """Open file picker and add selected files to attachment list."""
    # Call QFileDialog.getOpenFileNames()
    # For each selected file:
    #   - Convert to absolute path
    #   - Add to self.attachments list
    #   - Update list widget display

def _on_remove_attachment(self, file_path: str) -> None:
    """Remove file from attachment list."""
    # Remove from self.attachments
    # Update list widget display
```

---

## Feature 3: Test Mode Enforcement

### Public Interface

**UI Control**: `test_check: QCheckBox`

**Behavior**:
1. On dialog creation, `test_check` is checked by default
2. `test_check` is locked (cannot be unchecked by user initially)
3. User attempts to uncheck → checkbox remains checked (locked)
4. User sends test email → sendMail returns "OK_TEST"
5. On successful test send, `test_check` becomes unlocked
6. User can now check/uncheck `test_check` freely
7. User unchecks to proceed with bulk send
8. Dialog closes and reopens for a new campaign
9. `test_check` resets to checked (locked) for the new campaign

**State Machine**:
```
[Locked, Checked]
  ↓ (user tries to uncheck)
  ↓ (toggle blocked, auto-rechecks)
  ↓ (user sends test email)
[Locked, Checked] → [Unlocked, Checked]
  ↓ (user unchecks if desired)
[Unlocked, Unchecked]
  ↓ (user sends bulk email)
  ↓ (dialog closes)
  ↓ (dialog reopens for new campaign)
[Locked, Checked] ← reset
```

### Internal Methods & Attributes

```python
class _SendDialog(QDialog):
    _test_sent: bool = False  # Track if test email sent in this session
    
    def _on_test_mode_toggled(self, checked: bool) -> None:
        """Handle test checkbox toggle events."""
        # If unchecking and test_sent == False:
        #   - Block the signal
        #   - Recheck the checkbox
        #   - Prevent toggle
        # Otherwise allow toggle normally
    
    def _unlock_test_mode(self) -> None:
        """Unlock test checkbox after successful test send."""
        # Set _test_sent = True
        # Enable test_check for user interaction
```

### Integration with Send Flow

In `EditorWindow._menu_send()`:

```python
def _menu_send(self) -> None:
    # ... existing code ...
    dialog = _SendDialog(...)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    
    # Send email via sendMail CLI
    result = self._send_with_sendmail(dialog)
    
    # Check if test was successful
    if "OK_TEST" in str(result).upper():
        dialog._unlock_test_mode()  # Unlock for bulk send
        # Show test success message
    else:
        # Test failed or not run, keep locked
        pass
```

---

## Component State

**Instance Variables**:
- `subject_input: QLineEdit` — Subject field
- `attachments: list[str]` — List of absolute file paths
- `test_check: QCheckBox` — Test mode checkbox
- `_test_sent: bool` — Flag indicating test email sent successfully
- `attachment_path: str` — HTML file being sent (immutable)

**Reset on Dialog Reopen**:
- `subject_input`: Repopulated with current HTML's `<h1>` (new content each dialog open)
- `attachments`: Cleared (empty list)
- `test_check`: Reset to checked (locked)
- `_test_sent`: Reset to False

---

## Error Handling

**Subject Extraction**:
- If HTML file is invalid or unreadable → fallback to filename
- If filename is also missing or invalid → use generic default (e.g., "Untitled")

**Attachment File Picker**:
- User cancels → attachment list unchanged
- User selects non-existent file → system error handled by QFileDialog
- File deleted after selection but before send → sendMail CLI handles error

**Test Mode**:
- Test send fails → Keep checkbox locked (allow retry)
- Test send returns unexpected result → Log warning, keep locked

---

## Accessibility

- All buttons must have descriptive labels
- Keyboard navigation: Tab through fields, Space to toggle checkbox, Enter to confirm
- List items should be keyboard-navigable
- Error messages shown in modal dialogs or status labels

---

## Testing Contract

**Unit Tests** (mock PyQt6):
```python
def test_subject_extraction_from_h1():
    """Verify <h1> extraction and truncation."""
    # Create HTML file with <h1>
    # Create dialog
    # Assert subject_input contains extracted text (≤50 chars)

def test_subject_fallback_to_filename():
    """Verify filename fallback when no <h1>."""
    # Create HTML file without <h1>
    # Create dialog
    # Assert subject_input contains filename (≤50 chars)

def test_attachment_add_and_remove():
    """Verify file list add/remove behavior."""
    # Create dialog
    # Mock file picker to return files
    # Simulate add action
    # Assert files appear in list
    # Simulate delete action
    # Assert file removed from list

def test_test_mode_locked_then_unlocked():
    """Verify test checkbox state machine."""
    # Create dialog
    # Assert test_check is checked and locked
    # Simulate toggle attempt
    # Assert checkbox remains checked
    # Simulate test send success
    # Assert test_check now unlocked
    # Simulate toggle
    # Assert checkbox can be unchecked
```

**Integration Tests** (with PyQt6):
- Open dialog, verify subject populated
- Open file picker, select files, verify list displayed
- Send test email, verify unlock occurs
- Close and reopen dialog, verify reset occurs

---

## Version Notes

**Version**: 1.0  
**Status**: Design  
**Last Updated**: 2026-05-19
