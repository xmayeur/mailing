# Feature Specification: Send Dialog Improvements

**Feature Branch**: `006-send-dialog-improvements`  
**Created**: 2026-05-19  
**Status**: Draft  
**Input**: User description: "Subject preset from h1 or filename, file attachments widget, test mode enforcement"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-populate Subject Line from Document (Priority: P1)

As a newsletter author, I want the Subject field in the Send Mailing dialog to automatically populate with the top `<h1>` heading from my HTML document, so I don't have to manually retype the title and can quickly review/modify it if needed.

**Why this priority**: Core workflow efficiency — subject line is essential for every send, and auto-population eliminates repetitive manual entry for every campaign.

**Independent Test**: Can be fully tested by opening an HTML document with an `<h1>` tag in the editor, opening the Send Mailing dialog, and verifying the subject field is populated. Delivers immediate value for users creating newsletters from templates.

**Acceptance Scenarios**:

1. **Given** an HTML file with `<h1>My Newsletter Title</h1>` is open in the editor, **When** I open the Send Mailing dialog, **Then** the Subject field is populated with "My Newsletter Title" (truncated to 50 characters if longer)
2. **Given** an HTML file with no `<h1>` tag, **When** I open the Send Mailing dialog, **Then** the Subject field is populated with the filename (without extension), truncated to 50 characters
3. **Given** an `<h1>` title that exceeds 50 characters, **When** the dialog opens, **Then** the Subject field shows the title truncated to 50 characters with no ellipsis indicator
4. **Given** the Subject field is pre-populated, **When** I modify it, **Then** my changes are preserved and not overwritten on dialog re-open

---

### User Story 2 - Attach Multiple Files to Mailing (Priority: P1)

As a campaign manager, I want to add one or more file attachments directly in the Send Mailing dialog, view them in a list, and remove any attachment before sending, so I can keep all mailing assets (PDFs, images, documents) together without managing them separately.

**Why this priority**: Attachments are a core feature of the send workflow; managing them in the dialog prevents users from forgetting attachments and reduces send errors.

**Independent Test**: Can be fully tested by opening the Send Mailing dialog, adding/removing files from the attachment list, and verifying the list state updates correctly. Works independently of subject or test mode features.

**Acceptance Scenarios**:

1. **Given** the Send Mailing dialog is open, **When** I click "Add File" or similar control, **Then** a file picker opens allowing me to select one or more files
2. **Given** files are selected in the file picker, **When** I confirm the selection, **Then** the files appear in an attachment list widget below the HTML file input
3. **Given** files are shown in the attachment list, **When** I click remove/delete next to a file, **Then** that file is removed from the list immediately
4. **Given** the attachment list has files, **When** I proceed to send the mailing, **Then** all listed files are attached to the email
5. **Given** files are attached, **When** I cancel or close the dialog without sending, **Then** the attachment list is reset on next dialog open

---

### User Story 3 - Enforce Test Mode Before Bulk Send (Priority: P1)

As a campaign manager, I want the Test checkbox to remain checked (enforced/locked) in the Send Mailing dialog until I have successfully sent at least one test email, so I cannot accidentally send an untested campaign to the entire subscriber list.

**Why this priority**: Critical safety feature — prevents user error of sending untested campaigns to thousands of people, which could cause brand damage or compliance issues.

**Independent Test**: Can be fully tested by opening the dialog, verifying Test is checked by default, attempting to uncheck it (should fail or re-check automatically), sending a test email, and then verifying Test can be unchecked afterward.

**Acceptance Scenarios**:

1. **Given** the Send Mailing dialog opens for a new campaign, **When** I examine the Test checkbox, **Then** it is checked by default
2. **Given** the Test checkbox is checked, **When** I attempt to uncheck it, **Then** the checkbox remains checked (cannot be unchecked until test email is sent)
3. **Given** I attempt to proceed to send a bulk mailing with Test checked, **When** the send completes successfully as a test, **Then** a confirmation message indicates "Test email sent"
4. **Given** a test email has been successfully sent, **When** I open the Send Mailing dialog again, **Then** the Test checkbox can now be unchecked
5. **Given** Test checkbox is now unlocked (unchecked), **When** I proceed to send, **Then** the mailing is sent to all selected subscribers without test mode
6. **Given** I close and re-open the Send Mailing dialog for a different campaign, **When** the dialog opens, **Then** the Test checkbox is reset to checked (enforced) for the new campaign

---

### Edge Cases

- What happens if the HTML file has multiple `<h1>` tags? (Use the first one)
- What if the `<h1>` tag contains HTML formatting (bold, italics)? (Strip HTML tags, use plain text)
- What if the filename contains special characters? (Use it as-is, truncate to 50 chars)
- What if a user selects the same file twice in the attachment picker? (Allow duplicates or warn?)
- What happens if test email fails to send? (Test mode remains locked, show error, allow retry)
- What if user adds 10+ attachments? (List should scroll, total size warning?)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extract the first `<h1>` heading from the open HTML document and populate the Subject field with its text content
- **FR-002**: System MUST fallback to the filename (without extension) as Subject if no `<h1>` heading exists
- **FR-003**: System MUST truncate Subject text to a maximum of 50 characters
- **FR-004**: System MUST provide a file picker UI control in the Send Mailing dialog to add one or more attachments
- **FR-005**: System MUST display attached files in a list widget in the Send Mailing dialog (positioned right of HTML input, above filter widget)
- **FR-006**: System MUST allow removal of individual files from the attachment list via a per-row delete control
- **FR-007**: System MUST clear the attachment list when the Send Mailing dialog is closed and re-opened for a new campaign
- **FR-008**: System MUST check the Test checkbox by default when the Send Mailing dialog opens
- **FR-009**: System MUST prevent unchecking the Test checkbox until a test email has been successfully sent
- **FR-010**: System MUST unlock the Test checkbox (allow unchecking) after a test email is successfully sent
- **FR-011**: System MUST reset the Test checkbox to checked (locked) when the Send Mailing dialog is closed and re-opened for a new campaign
- **FR-012**: System MUST pass all attached files to the email backend for attachment to the outgoing message

### Key Entities *(include if feature involves data)*

- **Send Mailing Dialog**: UI form managing email campaign dispatch — contains HTML file input, Subject field, recipient filter, attachment list, Test checkbox, and send controls
- **Attachment**: A file selected by the user to be included with the mailing — stored as file path, displayed in list with delete control
- **Campaign Session**: Represents one open Send Mailing dialog instance — tracks test mode state, attachment list, and subject preset

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Subject field is auto-populated on dialog open in under 200ms
- **SC-002**: Users can add/remove attachments with UI response <100ms (added file visible in list, delete removes item instantly)
- **SC-003**: Users cannot send a bulk mailing without first sending a test email (100% enforcement)
- **SC-004**: Test mode checkbox correctly resets to checked when dialog is closed and re-opened
- **SC-005**: 95% of users successfully send at least one test email before sending to full list (measured via test mail logs)
- **SC-006**: Attachment list updates visually within 50ms when files are added or removed (QListWidget renders change immediately per Qt widget performance)

## Assumptions

- The Send Mailing dialog is implemented in PyQt6 (existing editor infrastructure)
- HTML documents open in the editor are always valid HTML with potential `<h1>` tags
- File attachments are stored as full file paths and passed to the existing email backend without modification
- Test email functionality already exists in the sendMail CLI and can be detected/confirmed via return code or log entry
- The "currently open document" is always available to the dialog via existing editor state/session mechanism
- Dialog session state (test mode lock, attachments) is reset when dialog closes, not persisted across editor restarts
- Maximum attachment list size is not specified; assume practical limits (no artificial cap needed for v1)
- Attachment file types are not restricted (user responsibility)
