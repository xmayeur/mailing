# Feature Specification: Editor UI Fixes & Send Workflow

**Feature Branch**: `009-editor-ui-fixes-send-flow`  
**Created**: 2026-06-04  
**Status**: Draft  
**Input**: User description: "Fix Insert Hyperlink menu, anchor tag attribute, add HTML source view, and implement send workflow with session log dialog"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Insert Hyperlink via Menu (Priority: P1)

User selects text in the editor, opens the Format menu, and clicks "Insert Hyperlink". A dialog appears. User enters URL and optional display text, confirms. A clickable hyperlink is inserted at the selection, identical to the result of pressing Ctrl+K.

**Why this priority**: Core editing function is broken — menu item does nothing or produces incorrect output.

**Independent Test**: Select text → Format → Insert Hyperlink → enter URL → OK → verify `<a href="...">text</a>` inserted in document.

**Acceptance Scenarios**:

1. **Given** text is selected, **When** user clicks "Insert Hyperlink" from the menu, **Then** the link dialog opens with the selected text pre-filled in the display text field
2. **Given** the link dialog is open, **When** user enters a URL and clicks OK, **Then** a hyperlink is inserted exactly as if the user had used Ctrl+K
3. **Given** no text is selected, **When** user clicks "Insert Hyperlink", **Then** the link dialog opens with empty display text and the URL becomes the display text on confirm

---

### User Story 2 - Insert Anchor with Correct ID Attribute (Priority: P1)

User places cursor in document and inserts an anchor. The anchor HTML uses `id="anchor-name"` not `data-anchor-id="anchor-name"`. Links in the document using `#anchor-name` resolve correctly in browsers.

**Why this priority**: Wrong HTML attribute means anchors are broken in all rendered emails/pages.

**Independent Test**: Insert anchor named "section1" → view HTML source → confirm `<a id="section1"></a>` present, no `data-anchor-id` attribute.

**Acceptance Scenarios**:

1. **Given** user inserts an anchor named "top", **When** HTML is saved or previewed, **Then** the anchor tag is `<a id="top"></a>` (not `data-anchor-id`)
2. **Given** a hyperlink with `href="#top"` exists, **When** the document is rendered in a browser, **Then** clicking the link scrolls to the anchor

---

### User Story 3 - View HTML Source Code (Priority: P2)

User can open a read-only HTML source view of the current document to inspect or copy the raw HTML. The view reflects the current editor content.

**Why this priority**: Enables power users to verify output and debug formatting without leaving the editor.

**Independent Test**: Click "View Source" (menu or button) → a dialog shows the current HTML → content matches what would be saved to file.

**Acceptance Scenarios**:

1. **Given** document has content, **When** user opens HTML source view, **Then** a dialog shows the full current HTML
2. **Given** the source dialog is open, **When** user closes it, **Then** the editor returns to normal without any change to the document
3. **Given** the source dialog is open, **When** user clicks Copy, **Then** the full HTML is copied to the clipboard

---

### User Story 4 - Send Workflow with Session Log (Priority: P1)

User completes the full send workflow: editor → save → Send dialog (forced test mode) → send test → log dialog shows progress → user confirms receipt → test mode unlocked → user sends for real → log dialog → user confirms → back to Send dialog.

**Why this priority**: The send workflow lacks feedback during sending and the test-mode gate is unclear.

**Independent Test**: Click Send in editor → Send dialog opens in test mode (locked) → click Send → log dialog shows live progress → on completion confirmation prompt appears → after confirm log closes → Send dialog stays open with test unlocked.

**Acceptance Scenarios**:

1. **Given** user clicks Send in the editor, **When** Send dialog opens, **Then** Test checkbox is checked and disabled (locked)
2. **Given** Send dialog is in test mode, **When** user clicks the Send button, **Then** the Session Log dialog opens and shows live progress lines as the send runs
3. **Given** send operation completes, **When** progress is done, **Then** a confirmation prompt appears asking user to confirm they received the test email
4. **Given** user confirms test receipt, **When** log dialog closes, **Then** Send dialog resumes with Test checkbox enabled (unlocked)
5. **Given** user clicks Send in non-test mode, **When** send completes, **Then** log dialog shows completion and a confirmation prompt; after confirm, Send dialog remains open
6. **Given** send operation fails, **When** error occurs, **Then** log dialog displays the error message and the confirmation prompt still appears

---

### Edge Cases

- What happens if the send operation is interrupted (network loss) mid-send? Log must show error; dialog must not hang.
- What if the user closes the log dialog before the send finishes? Send should continue; warn user.
- What if no database records match the filter? Send dialog must show 0 matching records and warn before sending.
- What if the anchor name contains spaces or special characters? Normalize to valid HTML id (replace spaces with hyphens, strip invalid chars).

## Requirements *(mandatory)*

### Functional Requirements

**Fix: Insert Hyperlink menu**
- **FR-001**: The "Insert Hyperlink" menu action MUST call the same internal function as the Ctrl+K toolbar button, opening the link dialog with identical behaviour
- **FR-002**: When text is selected before opening the dialog, the selected text MUST pre-populate the display text field

**Fix: Anchor tag attribute**
- **FR-003**: The anchor insertion function MUST produce `id="<name>"` on the anchor element, not `data-anchor-id="<name>"`
- **FR-004**: Anchor names MUST be sanitized to valid HTML id values (no spaces, lowercase recommended)

**New: HTML source view**
- **FR-005**: A "View HTML Source" action MUST be accessible from the View menu (or equivalent toolbar)
- **FR-006**: The source dialog MUST display the current document's full HTML content
- **FR-007**: The source dialog MUST provide a copy-to-clipboard button
- **FR-008**: The source view MUST be read-only

**Send workflow**
- **FR-009**: Clicking Send in the editor MUST open the Send dialog with the Test checkbox checked and the checkbox disabled (locked)
- **FR-010**: Clicking the Send button inside the Send dialog MUST open the Session Log dialog, which displays progress lines in real time as the send operation runs
- **FR-011**: After a send completes (success or failure), the Session Log dialog MUST display a confirmation prompt before allowing the user to close it
- **FR-012**: After a successful test send and user confirmation, the Send dialog MUST unlock the Test checkbox
- **FR-013**: After a real (non-test) send completes, the Send dialog MUST remain open so the user can review state or close manually
- **FR-014**: The Session Log dialog MUST show errors clearly if the send operation fails

### Key Entities

- **SessionLogDialog**: Displays streaming log lines; has confirmation prompt before close; stays open until user confirms
- **SendDialog**: Orchestrates send options; manages test-mode lock/unlock; opens SessionLogDialog
- **EditorWindow**: Hosts the document; triggers Save before Send; opens SendDialog in forced test mode

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: "Insert Hyperlink" menu item produces a valid `<a href="...">` tag 100% of the time when a URL is entered
- **SC-002**: Anchor tags in saved HTML contain `id="..."` and zero instances of `data-anchor-id` remain
- **SC-003**: HTML source dialog opens in under 500 ms for documents up to 500 KB
- **SC-004**: Send workflow completes the full test → confirm → real-send → confirm cycle without requiring a dialog restart
- **SC-005**: Session log displays first progress line within 2 seconds of clicking Send

## Interaction Diagram (./docs/diagrams/interactions.puml as reference)

```
User                EditorWindow         SendDialog            SessionLogDialog
 |                       |                    |                       |
 |-- clicks Send ------->|                    |                       |
 |                       |-- save if dirty    |                       |
 |                       |-- open SendDialog (test=True, locked) --->|
 |                       |                    |                       |
 |-- sets options ------>|                    |                       |
 |-- clicks Send ------->|                    |                       |
 |                       |                    |-- open SessionLog --->|
 |                       |                    |                  streams log lines
 |                       |                    |                  send completes
 |                       |                    |                  show confirm prompt
 |<--"Test received?"----|--------------------|----------------------|
 |-- Yes/No ------------>|                    |                       |
 |                       |                    |                  close log dialog
 |                       |                    |<-- control returns ---|
 |                       |                    |-- unlock test mode    |
 |                       |                    |                       |
 |-- unchecks Test ------>                    |                       |
 |-- sets options ------->                    |                       |
 |-- clicks Send -------->                    |                       |
 |                       |                    |-- open SessionLog --->|
 |                       |                    |                  streams log lines
 |                       |                    |                  send completes
 |                       |                    |                  show confirm prompt
 |<-- "Send complete" ---|--------------------|-----------------------|
 |-- OK ---------------->|                    |                       |
 |                       |                    |                  close log dialog
 |                       |                    |<-- control returns ---|
 |                       |                    |-- waits for user      |
 |-- Cancel/Close ------->                    |                       |
 |                       |<-- SendDialog closed                       |
```

## Assumptions

- The editor already has a working Ctrl+K / toolbar Insert Link path; the menu item fix reuses that exact code path
- "View HTML Source" is read-only for this iteration; direct HTML editing via source is deferred
- The Session Log dialog's send operation runs in a background thread so the UI remains responsive
- "Confirm" after send is a simple QMessageBox asking the user to acknowledge
- The forced-test-mode lock applies only when the Send dialog is opened from the editor's Send action
- Anchor sanitization: spaces → hyphens, other special characters stripped, result lowercased
