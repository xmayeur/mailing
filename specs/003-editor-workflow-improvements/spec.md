# Feature Specification: Editor Workflow Improvements

**Feature Branch**: `003-editor-workflow-improvements`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: Editor UX fixes and path persistence improvements

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Persistent Document Folder (Priority: P1)

Newsletter creators frequently work with documents organized in project folders. Currently, they must navigate to the correct folder each time they save a document. The editor should remember the default folder location and restore it when reopened, reducing friction in the save workflow.

**Why this priority**: This is a core usability improvement that affects every save operation. Users lose time navigating folders repeatedly.

**Independent Test**: Can be tested by opening the editor, saving a file to a specific folder, closing the editor, and verifying that reopening presents the same folder as the default location.

**Acceptance Scenarios**:

1. **Given** editor is launched with no file open, **When** user accesses File → Save As, **Then** the file browser defaults to the last used folder path
2. **Given** config file has no default_documents_path set, **When** editor launches, **Then** it uses OS-appropriate default (Documents folder on Windows/macOS, home directory on Linux)
3. **Given** user saves a file to `/home/user/projects/newsletters`, **When** they close and reopen the editor, **Then** Save As defaults to `/home/user/projects/newsletters`
4. **Given** last saved folder no longer exists, **When** editor launches, **Then** it falls back to OS default without errors

---

### User Story 2 - Responsive Filter Editing (Priority: P1)

When composing subscriber filters in the Send Mailing dialog, users experience lag and visual stuttering due to debounce timeout. They type a filter field name, then wait for validation feedback. This breaks the typing flow.

**Why this priority**: Direct impact on task completion time. Users compose filters frequently when sending targeted campaigns.

**Independent Test**: Can be tested by opening Send Mailing dialog, typing in the filter field quickly, and observing that text appears immediately without lag or validation delays interrupting typing.

**Acceptance Scenarios**:

1. **Given** user types text into the filter field, **When** characters are entered at normal typing speed, **Then** all characters appear immediately without lag
2. **Given** user is typing a filter expression, **When** they pause typing, **Then** validation runs and feedback appears without interrupting the user's next keystroke
3. **Given** user types rapidly into filter field, **When** they complete their filter, **Then** there is no perception of UI unresponsiveness during typing

---

### User Story 3 - Send Mailing Window Clarity (Priority: P2)

The dialog title "Send Newsletter" is ambiguous. Users need clearer labeling to understand this is for bulk mailing operations with filtering and profile selection.

**Why this priority**: Improves user orientation and reduces confusion, though not blocking core functionality.

**Independent Test**: Can be tested by opening the send dialog and verifying the window title matches expected naming convention.

**Acceptance Scenarios**:

1. **Given** user clicks File → Send, **When** the dialog opens, **Then** the window title reads "Send Mailing" (not "Send Newsletter")
2. **Given** user has the send dialog open, **When** they look at the window title, **Then** it clearly indicates this is for mailing operations

---

### User Story 4 - Simplified Send Mailing Dialog (Priority: P2)

The "Selected only" checkbox is rarely used and adds cognitive load. Removing it simplifies the interface without loss of core functionality, as selection filtering can be handled at the CLI level or through other means.

**Why this priority**: UI simplification improves user focus on core tasks (profile, subject, filter). Not removing this breaks flow but removing it does not.

**Independent Test**: Can be tested by opening Send Mailing dialog and confirming "Selected" checkbox is not present in the Flags section.

**Acceptance Scenarios**:

1. **Given** user opens the Send Mailing dialog, **When** they look at the Flags section, **Then** only Test, Verbose, and Do not send checkboxes are visible
2. **Given** the "Selected only" option is removed, **When** bulk mailing is performed, **Then** all matching rows are processed (standard behavior without selection filtering)

---

### User Story 5 - Template Safety Enforcement (Priority: P3)

When users open template files in the editor, they should work with copies, not modify templates directly. Opening a template in read-only mode and forcing Save As enforces this workflow automatically.

**Why this priority**: Prevents accidental template modification. Valuable but not critical—users can manage this manually if needed.

**Independent Test**: Can be tested by opening a template file and verifying it opens in read-only mode and Save is disabled until Save As is used.

**Acceptance Scenarios**:

1. **Given** user opens a file named `template.html`, **When** the file opens, **Then** the editor loads it in read-only mode
2. **Given** a template file is open in read-only mode, **When** user tries to save with Ctrl+S, **Then** Save As dialog opens instead of direct save
3. **Given** user makes edits to a template in read-only mode, **When** they invoke Save As, **Then** a new file is created and the original template is unchanged

---

### Edge Cases

- What happens if user config file is corrupted or contains invalid path?
- How does the editor behave if the last saved folder is on a disconnected drive or network path?
- What if a user manually deletes or moves a template file while the editor has it open?
- How does the system handle special characters or long paths in folder locations?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store the last successfully used document folder path in the config file under a key named `default_documents_path`, **per profile** (each profile has its own remembered path)
- **FR-002**: On Windows, MUST default to the user's Documents folder (`%USERPROFILE%\Documents`); on macOS/Linux, MUST default to the user's home directory (`~`)
- **FR-003**: System MUST validate that the stored path exists before using it; if not, MUST fall back to OS default without error
- **FR-004**: System MUST update `default_documents_path` in config **only after a user successfully saves or opens a file**; on save/open failure, do NOT update the path (user retains previous folder default)
- **FR-005**: System MUST apply responsiveness improvements to filter text field debouncing to eliminate typing lag and stuttering
- **FR-006**: System MUST rename the Send Newsletter dialog window to "Send Mailing"
- **FR-007**: System MUST remove the "Selected only" checkbox from the Flags section of the Send Mailing dialog
- **FR-008**: System MUST detect files with `.template` in the filename or named `template.*` and open them in read-only mode
- **FR-009**: System MUST disable the Save action (Ctrl+S, File → Save) when a template file is open; Save As must remain enabled
- **FR-010**: System MUST preserve all edits made to a read-only template in memory and allow Save As without data loss
- **FR-011**: System MUST write config changes atomically; if a write error occurs, the system MUST roll back to the previous config state without data loss

### Key Entities

- **Configuration File**: YAML config file containing profile settings, now extended with `default_documents_path` key **per profile** (each profile has its own remembered folder path)
- **Last Opened Folder**: File system path string stored in profile config, validated at startup
- **Template File**: HTML or Markdown file with `template` in filename, marked as read-only on load

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can save files to a remembered folder location without manual navigation, reducing File → Save As workflow time by 50%; baseline: ~10 seconds (current manual folder browsing + save); target: <5 seconds (immediate default folder + single save click)
- **SC-002**: Filter text field accepts input with <50ms perceived latency during normal typing (at least 60 words per minute)
- **SC-003**: Window title "Send Mailing" is immediately visible and eliminates naming ambiguity; ≥80% of test users correctly identify the dialog's purpose as mailing/newsletter sending (measured via user comprehension testing: ask users "What is this dialog for?" without additional context; success if ≥8 of 10 users or ≥4 of 5 users recognize it as a mailing tool)
- **SC-004**: The Send Mailing dialog displays 3 checkboxes in Flags section (Test, Verbose, Do not send) instead of 4
- **SC-005**: Template files open in read-only mode and cannot be saved directly; 100% of template modifications require explicit Save As
- **SC-006**: No errors occur when stored folder path is invalid; editor recovers gracefully to OS default within 1 second

## Assumptions

- Users have stable write access to the config file location
- Templates are named with `.template` in filename (e.g., `template.html`, `newsletter-template.md`) or exactly named `template.*`
- "Selected only" functionality is not critical for core workflows; users can filter at the CLI if needed
- OS-specific defaults (Documents/home) are appropriate for the target user base
- Debounce timeout issue is resolvable through parameter adjustment without architectural changes to filter validation
- Config file uses YAML format and is writable by the editor process
- Users understand the purpose of read-only mode and will use Save As for template-based workflows

## Clarifications

### Session 2026-05-18

- Q1: Config path storage scope (per-profile or global?) → A: **Per-profile** — Each profile stores its own `default_documents_path` in its profile config block, allowing different workflows to use different save locations.
- Q2: Atomic config writes requirement? → A: **FR-011 Added** — Atomic writes are now a formal requirement to prevent data corruption on concurrent saves or errors.
- Q3: SC-003 measurement method? → A: **≥80% user comprehension** — Test with 5-10 users; success if ≥80% correctly identify the dialog as a mailing tool when shown the "Send Mailing" title.
- Q4: SC-001 baseline time? → A: **~10s current / <5s target** — Current baseline: ~10 seconds for manual folder navigation + save. Target: <5 seconds with path persistence (50% improvement).
- Q5: FR-004 update on error? → A: **Only on success** — Update `default_documents_path` only after confirmed successful save/open. On failure, retain previous folder (safer UX).

