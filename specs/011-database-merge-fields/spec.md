# Feature Specification: Database Merge Fields in Mailing Content

**Feature Branch**: `011-database-merge-fields`
**Created**: 2026-11-26
**Status**: Draft
**Input**: User description: "Insert special fields named after database fields into the mailing; each is replaced by the recipient's value when the mailing is sent to one recipient at a time. For instance, inserting `${ID}` inserts the recipient's ID value. If the mailing (message) goes to more than one recipient, a blank value is inserted instead."

## Clarifications

### Session 2026-11-26

- Q: Which parts of the outgoing message get merge-field replacement? → A: All parts that exist (rich text, plain text, subject) — no part may leak a literal marker to a recipient.
- Q: What if the batch size allows several recipients per message while markers are present? → A: For safety, the batch size is forced to 1 (one message per recipient) whenever a well-formed marker is present in the body, subject, or HTML/Markdown attachment — markers always resolve to per-recipient values.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Insert a Database Field into the Mailing (Priority: P1)

While composing a mailing in the editor, the user wants to personalize the content with data from the subscriber database (e.g., the recipient's ID, first name, city). The user picks a database field and the editor inserts a special field marker such as `${ID}` at the current cursor position in the mailing content. The inserted marker remains visible and editable in the editor until the mailing is sent.

**Why this priority**: Without the ability to insert the field, no personalization is possible. This is the core user-facing capability.

**Independent Test**: Can be fully tested by opening the editor with a profile whose subscriber database is known, inserting a field from the database, and verifying the marker text (e.g., `${ID}`) appears at the cursor position.

**Acceptance Scenarios**:

1. **Given** the editor is open with a profile whose subscriber database has known fields, **When** the user chooses to insert a field and selects the field `ID`, **Then** the marker `${ID}` is inserted at the cursor position in the mailing content
2. **Given** the mailing content already contains text, **When** the user positions the cursor mid-text and inserts a field, **Then** the marker is inserted at the cursor without disturbing surrounding text
3. **Given** the user does not select any database field (dismisses the field picker), **When** the insertion is cancelled, **Then** the mailing content is unchanged
4. **Given** the profile's subscriber database changes (different file or columns), **When** the user opens the field picker again, **Then** it lists the fields of the current subscriber database

---

### User Story 2 - Replace Fields with the Recipient's Value at Send Time (Priority: P1)

When the mailing is sent to one recipient at a time (the normal mailing flow), each special field in the message is replaced by the value that field holds for that specific recipient. For example, the text `Dear ${FIRSTNAME},` becomes `Dear Alice,` in the email received by Alice and `Dear Bob,` in the email received by Bob. The stored mailing content keeps its markers unchanged; replacement happens only in the outgoing message.

**Why this priority**: This is the payoff of the feature — personalized emails. It is the value the whole feature exists to deliver.

**Independent Test**: Can be fully tested by sending (or simulating) a mailing containing `${ID}` and other fields to a subscriber list, then verifying each outgoing email contains the matching subscriber's values.

**Acceptance Scenarios**:

1. **Given** the mailing content contains `${ID}` and the current subscriber's ID is `42`, **When** the email is prepared for that recipient (sent one at a time), **Then** the outgoing email contains `42` instead of `${ID}`
2. **Given** the mailing contains several different field markers, **When** the email is prepared for a recipient, **Then** every marker is replaced by that recipient's value for the corresponding field
3. **Given** a subscriber whose value for a field is empty, **When** the email is prepared, **Then** that marker is replaced by an empty string (the surrounding text remains)
4. **Given** the stored mailing (draft/template), **When** the user reopens it after a send, **Then** the markers are still present (the stored content is never modified by a send)
5. **Given** the mailing has a subject line such as `Your order ${ORDERID}` and a subject field value, **When** the email is prepared for a single recipient, **Then** the subject is personalized with that recipient's value
6. **Given** the outgoing email carries both a rich-text part and a plain-text part, **When** a marker is replaced for a single recipient, **Then** the marker is replaced in both parts

---

### User Story 3 - Blank Replacement When One Message Reaches Several Recipients (Priority: P2)

When the mailing is sent as a single message addressed to more than one recipient (e.g., several addresses in the To/CC of the same message), no single recipient's value can be chosen, so each special field is replaced by a blank value. The rest of the message is unaffected.

**Why this priority**: Needed for correctness and to prevent leaking one recipient's data to another; strictly less common than the one-recipient flow but essential once multiple recipients share a message.

**Independent Test**: Can be fully tested by preparing a message whose To line contains two addresses and verifying the outgoing message has blank values where the markers were.

**Acceptance Scenarios**:

1. **Given** a mailing containing `${ID}`, **When** a message is prepared for two recipients at once, **Then** the outgoing message contains an empty string instead of the marker (no recipient's value is substituted)
2. **Given** a mailing containing a marker plus surrounding text such as `Hello ${FIRSTNAME},`, **When** a multi-recipient message is prepared, **Then** the outgoing message reads `Hello ,` and no other content changes

---

### User Story 4 - Field Picker Lists the Actual Database Fields (Priority: P2)

The user needs to know which field names are valid. The insertion UI lists the field names of the current profile's subscriber database (headers of the CSV/Excel file or of the Google Sheet), so the user picks a real field rather than typing a guess.

**Why this priority**: Prevents typos and improves discoverability, but the feature already works if the user types a marker manually.

**Independent Test**: Can be fully tested by opening the field picker with a subscriber database whose headers are known and verifying the list matches exactly.

**Acceptance Scenarios**:

1. **Given** the profile's subscriber database has headers `ID`, `FIRSTNAME`, `LASTNAME`, **When** the field picker opens, **Then** it lists exactly those field names
2. **Given** the subscriber database cannot be read (missing file, unreadable), **When** the field picker opens, **Then** the user is informed that fields are unavailable and the mailing content is unchanged
3. **Given** a Google Sheets or Excel subscriber database, **When** the field picker opens, **Then** field names from that source's first row are listed

---

### Edge Cases

- What happens when the marker references a field that does not exist in the subscriber database? → The marker is replaced by a blank value like an empty field.
- What happens when the marker appears in the message subject line? → The marker is replaced there too (same rules as the body).
- What happens when a marker is only partially typed or malformed (e.g., `${` alone, `${ID` without closing brace)? → It is left as literal text; only well-formed markers are processed.
- What happens when the same marker appears multiple times? → Each occurrence is replaced.
- What happens when a marker is inside text the user intended literally? → In this version every well-formed marker is processed (documented limitation); the user avoids the syntax for literal text.
- What happens when a marker appears inside an HTML attribute (e.g. `<a href="${email}">`)? → It is replaced like any other occurrence (the raw content is processed as text); this is intended and enables personalized links.
- What happens when a subscriber's field value contains characters with special meaning in email content (e.g., HTML markup in a CSV cell)? → The value is inserted exactly as stored in the database, without transformation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The editor MUST let the user insert a special field (merge field) whose name is a field of the current profile's subscriber database, at the current cursor position in the mailing content.
- **FR-002**: The merge-field syntax MUST be `${FIELDNAME}` where `FIELDNAME` is the exact name of a subscriber database field (between `${` and `}`).
- **FR-003**: The editor MUST provide a field picker that lists the field names of the current subscriber database (from the same source used for filter validation and suggestions).
- **FR-004**: The picker MUST refresh when the selected profile or its subscriber database changes.
- **FR-005**: At send time, when the message is prepared for a single recipient, the system MUST replace every well-formed merge-field marker in the message with that recipient's value for the named field.
- **FR-006**: At send time, when the message is addressed to more than one recipient, the system MUST replace every well-formed marker with an empty string.
- **FR-007**: Marker replacement MUST NOT modify the mailing content as stored/edited; only the outgoing message is affected.
- **FR-008**: The system MUST process every occurrence of a marker in the message. Replacement MUST be neutral to surrounding text (the rest of the content is unchanged).
- **FR-009**: The system MUST leave malformed or unknown constructs (anything not matching `${FIELDNAME}`) as literal text.
- **FR-010**: If a subscriber's value for a field is missing or empty, the system MUST replace the marker with an empty string.
- **FR-011**: The system MUST replace with an empty string any marker whose field name does not exist in the subscriber database, so that a mistake never leaks a literal marker into a sent email.
- **FR-012**: The system MUST apply the same replacement rules to the message subject line when one is defined (including the blank rule for multi-recipient messages).
- **FR-013**: The system MUST apply the same replacement rules to every part of the outgoing message that exists (rich text, plain text, subject), so that no part of the sent email displays a literal marker.
- **FR-014**: The system MUST force one recipient per message (batch size 1) whenever the message content (body, subject, or HTML/Markdown attachment) contains at least one well-formed merge-field marker, so that every marker resolves to per-recipient values.

### Key Entities *(include if feature involves data)*

- **Merge field**: A marker of the form `${FIELDNAME}` inserted in the mailing content. Attributes: field name (text), position in content. Behaves as plain text during editing.
- **Subscriber database**: The current profile's data source (CSV, Excel, or Google Sheet). Attributes: field names (first-row headers), one record per recipient with a value per field.
- **Recipient**: One address receiving a message. Attributes: the subscriber record's values, used for replacement when the message is dedicated to that single recipient.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can insert a database merge field in the editor in under 5 seconds using the field picker, without typing syntax manually.
- **SC-002**: When a mailing containing merge fields is sent one recipient at a time, 100% of markers in each outgoing email resolve to that recipient's values (empty string when the value is empty).
- **SC-003**: When a mailing containing merge fields is sent to multiple recipients in one message, the fields appear blank in the outgoing message for 100% of occurrences.
- **SC-004**: After any send, the stored mailing still contains 100% of its original markers (no content mutation).
- **SC-005**: The field picker lists exactly the field names of the current subscriber database with no missing or extra entries.

## Assumptions

- Merge-field syntax is `${FIELDNAME}` with the dollar sign and curly braces, matching the field tokens already familiar from the existing feature discussions; field names are matched exactly as they appear in the database header row.
- The insert action behaves like normal text insertion: markers can be freely edited, copied, deleted, or undeleted (undo) in the editor.
- Replacement applies to the whole outgoing message text prepared for the recipient(s), in the normal one-recipient-at-a-time flow; no new send mode is introduced.
- A blank replacement for multi-recipient messages is acceptable because such messages are exceptional in this tool's normal mailing flow (one recipient per message).
- Error handling for picker failures follows existing patterns: the failure is surfaced to the user without blocking editing.

## Out of Scope

- Preview of the personalized email inside the editor (seeing the value substituted before sending).
- Conditional content (showing/hiding blocks depending on a field value).
- Computed or derived fields (formulas combining fields, date formatting).
- Internationalization of the merge-field syntax (a single fixed syntax is used).
