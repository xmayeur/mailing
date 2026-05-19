# Quickstart: Send Dialog Improvements

**Feature**: 006-send-dialog-improvements  
**Date**: 2026-05-19

## User Journey

### Scenario: Newsletter Campaign with Attachments and Test Send

**Setup**: You have an HTML newsletter file with an `<h1>` title tag and want to attach a PDF before sending.

---

### Step 1: Open the Send Mailing Dialog

In the WYSIWYG editor (`src/editor.py`), click **Menu → Send** (or equivalent).

The editor saves the current HTML file and opens the **Send Mailing** dialog.

**What you see**:
- Form with fields: Config, Profile, Attachment, **Subject**, Message, Body, Database, Filter, Flags
- Subject field is **pre-filled** with "My Newsletter Title" (extracted from the HTML's `<h1>` tag)
- Subject is truncated to 50 characters maximum
- Test checkbox is **checked and locked** (cannot uncheck yet)

---

### Step 2: Review and Modify Subject (Optional)

The subject is pre-filled with `<h1>` text from your HTML file.

**You can**:
- Accept the pre-filled subject as-is
- Click in the field and edit the subject
- Your edits persist throughout the dialog session

**Example**:
- HTML file contains: `<h1>Weekly Community Update - Issue #42</h1>`
- Dialog pre-fills: "Weekly Community Update - Issue #" (truncated to 50 chars)
- You can edit it to: "Weekly Update Issue 42" (shorter, clearer)

---

### Step 3: Add File Attachments

The **Attachment** section now includes an **Add** button and attachment list.

**You can**:
1. Click **Add** button
2. File picker dialog opens
3. Browse to your files (PDFs, Word docs, images, etc.)
4. Select one or multiple files and click **Open**
5. Selected files appear in the list below the Add button

**Example**:
- Select: `report.pdf`, `schedule.xlsx`, `branding-guide.pdf`
- List displays: "report.pdf", "schedule.xlsx", "branding-guide.pdf"
- Each list item has a **Delete** button

**You can also**:
- Click **Delete** next to any file to remove it before sending
- Add more files by clicking **Add** again
- Attachment list persists while dialog remains open

---

### Step 4: Configure Other Fields

As normal, fill in:
- Profile (email account)
- Message template
- Database (subscriber list)
- Filter (optional, to limit recipients)
- Other flags (Verbose, Do Not Send, etc.)

---

### Step 5: Send a Test Email

To protect against sending untested campaigns, the **Test** checkbox is checked by default.

**You must**:
1. Click **Send** button
2. Editor runs sendMail with `--test` flag
3. Test email is sent to a test address (configured in your profile)
4. Dialog shows a log of the send result
5. If test succeeds, message shows: **"Test email sent"**

**What happens**:
- Test email is sent with your subject, message body, and **all attachments**
- You verify the email looks correct
- Test mode remains locked during this send (you cannot uncheck it)

---

### Step 6: Send to Full List (After Test Succeeds)

After the test email is sent successfully, the **Test** checkbox is **unlocked**.

**You can now**:
1. Uncheck the **Test** checkbox to enable bulk send mode
2. Click **Send** again
3. Editor runs sendMail without `--test` flag
4. Mailing is sent to all selected subscribers with **all attachments**

**Flow**:
```
Dialog opens
  ↓
Test checkbox: checked (locked) ← Must send test first
  ↓ (Click Send with test checked)
  ↓
Test email sent successfully
  ↓
Test checkbox: checked (now unlocked) ← Can proceed with bulk
  ↓ (Uncheck Test checkbox)
  ↓
Test checkbox: unchecked
  ↓ (Click Send)
  ↓
Bulk email sent to all subscribers with attachments
  ↓
Dialog closes
```

---

### Step 7: Close Dialog and Send Another Campaign

When you close the dialog and open it for a new HTML file:

**Reset occurs**:
- Subject field is repopulated from **new file's** `<h1>` tag
- Attachment list is **cleared** (no files from previous send)
- Test checkbox is **reset to checked (locked)**

**Why**: Each campaign is independent. You must send a test email before bulk send, even if you sent a test for the last campaign.

---

## Common Cases

### Case 1: No `<h1>` Tag in HTML

If your HTML file has no `<h1>` tag:

**Subject field is pre-filled with**: Filename (without directory or extension)

Example:
- File: `~/Documents/weekly-update.html`
- Subject pre-filled: "weekly-update"

You can still edit it before sending.

---

### Case 2: Very Long `<h1>` Title

If your `<h1>` exceeds 50 characters:

**Subject field shows**: First 50 characters (truncated)

Example:
- HTML: `<h1>Our Organization's Monthly Newsletter - Issue 42 - January 2026</h1>`
- Subject pre-filled: "Our Organization's Monthly Newsletter" (50 chars)

Edit if needed to clarify the truncation.

---

### Case 3: Duplicate Attachments

If you accidentally select the same file twice:

- Both instances are added to the list
- You can delete one instance

(This is allowed; sendMail will attach both copies.)

---

### Case 4: Test Email Fails

If the test email fails to send:

- Error message is shown in the log dialog
- **Test checkbox remains locked**
- Fix the issue and try again
- Test checkbox unlocks only after successful send

---

## Safety Features

1. **Test-First Enforcement**: Cannot send to full list without testing first
   - Prevents accidental mass send of untested campaigns
   - Avoids brand damage or compliance issues

2. **Subject Auto-Population**: Reduces typos and manual entry
   - Subject is already in your HTML, reused automatically
   - Can still be edited if needed

3. **Attachment Visibility**: All files shown in list before send
   - No hidden attachments
   - Can review and remove files as needed

4. **Per-Campaign Reset**: Each dialog session is independent
   - New campaign requires new test send
   - Prevents copy-paste errors from previous send

---

## Keyboard Shortcuts

- **Tab**: Navigate to next field
- **Shift+Tab**: Navigate to previous field
- **Space**: Toggle checkboxes (Test, Verbose, Do Not Send)
- **Enter**: Send (equivalent to clicking OK button)
- **Escape**: Cancel (close dialog without sending)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Subject not pre-filled | HTML file may have no `<h1>` tag; fallback to filename |
| Cannot uncheck Test | Test email not sent yet; send test first |
| Attachments not in email | Verify files exist and have correct permissions |
| Test email goes to wrong address | Check Profile settings in config; ensure test address is configured |

---

## What's Next?

After sending, the editor shows a log dialog with:
- Number of emails sent
- Any errors or warnings
- Total time elapsed

You can close the log and send another campaign or continue editing.
