# Feature Specification: Editor Profile & Clipboard Enhancements

**Feature Branch**: `005-editor-profile-clipboard`  
**Created**: 2026-05-19  
**Status**: Draft  
**Input**: User description: "Move config profile selection to main window + apply default_document_path immediately; Enable cut/paste with hyperlinks; Auto-linkify URLs on paste"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Profile Selection in Editor (Priority: P1)

Editor users can select an email profile directly from the main window and immediately open documents associated with that profile's default path, eliminating the need to navigate config files or manually browse directories.

**Why this priority**: Core usability improvement. Users currently must work outside the editor to switch profiles, breaking workflow continuity. This is the primary entry point for the feature.

**Independent Test**: Can be fully tested by (1) launching editor, (2) selecting a profile from main window, (3) verifying default_document_path loads automatically and (4) confirming ability to open documents from that path. Delivers standalone value without clipboard features.

**Acceptance Scenarios**:

1. **Given** editor is open with config profiles available, **When** user selects a profile from dropdown in main window, **Then** the default_document_path for that profile is loaded and file browser opens to that directory
2. **Given** a profile with default_document_path set, **When** user selects the profile, **Then** recently opened files from that path appear in file history or quick-access UI
3. **Given** multiple profiles with different default paths, **When** user switches between profiles, **Then** the active directory context updates immediately

---

### User Story 2 - Preserve Hyperlinks in Copy/Paste (Priority: P1)

Editor users can copy text containing hyperlinks from external sources (web pages, emails, documents) and paste them into the editor while preserving the link markup, avoiding manual link recreation.

**Why this priority**: Core editor feature. Users frequently work with hyperlinked content and loss of hyperlink data is frustrating and time-consuming to fix manually.

**Independent Test**: Can be fully tested by (1) copying text with hyperlink from external source, (2) pasting into editor, (3) verifying hyperlink is preserved in document. Works independently of profile feature.

**Acceptance Scenarios**:

1. **Given** text with HTML link copied from external source, **When** user pastes via Ctrl+V/Cmd+V, **Then** link markup is preserved in editor (visible as hyperlink)
2. **Given** mixed text and hyperlinks pasted from rich text source, **When** user pastes into editor, **Then** all links remain functional and editable as links (not plain text)
3. **Given** user pastes and then saves document, **When** document is exported or reopened, **Then** hyperlinks remain intact

---

### User Story 3 - Auto-Linkify URLs on Paste (Priority: P2)

When users paste plain-text URLs into the editor, they are automatically converted to clickable hyperlinks without requiring manual link creation.

**Why this priority**: Convenience/productivity enhancement. Reduces friction for users pasting URLs as plain text from logs, chat, or terminal. Valuable but not blocking without it.

**Independent Test**: Can be fully tested by (1) pasting plain-text URL (e.g., https://example.com) into editor, (2) verifying URL becomes a clickable link. Works independently of other features.

**Acceptance Scenarios**:

1. **Given** plain-text URL pasted into editor (e.g., "https://example.com" or "http://example.org/path"), **When** paste completes, **Then** URL is automatically converted to a clickable hyperlink
2. **Given** multiple URLs in pasted text, **When** paste completes, **Then** each URL is linkified individually
3. **Given** URL already wrapped in markdown link syntax, **When** paste completes, **Then** no double-conversion occurs (remains as single link)

---

### User Story 4 - Apply Profile Stylesheet on Selection (Priority: P2)

When users select a profile that has a stylesheet defined in config, the editor automatically loads and applies that stylesheet to the document, ensuring consistent visual styling based on profile selection.

**Why this priority**: Workflow enhancement. Allows users to maintain profile-specific styling without manual intervention. Improves consistency when switching between profiles with different style requirements.

**Independent Test**: Can be fully tested by (1) selecting a profile with defined stylesheet from dropdown, (2) verifying stylesheet is loaded and applied to editor document. Works independently of other features.

**Acceptance Scenarios**:

1. **Given** profile with stylesheet path defined in config, **When** user selects profile from dropdown, **Then** stylesheet is loaded and applied to editor document immediately
2. **Given** profile without stylesheet defined, **When** user selects profile, **Then** system falls back to default/system stylesheet without error
3. **Given** user switches between profiles with different stylesheets, **When** profile selection changes, **Then** new stylesheet replaces previous one smoothly

---

### Edge Cases

- What happens when pasting rich content with broken/invalid links?
- How does editor handle paste of content with nested hyperlinks (link inside link)?
- What happens if user pastes URL that matches existing link text in document?
- How does system behave if profile config is missing default_document_path value?
- What happens when switching profiles while document with unsaved changes is open?
- What happens if stylesheet path in profile config is invalid or file doesn't exist?
- How does editor handle stylesheet switching if current document has inline CSS or user-applied styles?
- Should stylesheet be applied to unsaved documents when profile changes, or only new documents?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Editor main window MUST display available email profiles from config.yml as a dropdown/selector
- **FR-002**: Selecting a profile MUST immediately apply that profile's `default_document_path` to the file browser/open dialog
- **FR-003**: When a profile with `default_document_path` is selected, the editor MUST initialize file browser to that directory on next file open action
- **FR-004**: Editor MUST support Ctrl+V/Cmd+V paste operations that preserve HTML link markup from copied content
- **FR-005**: Pasted hyperlinks MUST remain clickable/editable as links in the editor document
- **FR-006**: When user pastes plain-text URLs (http://, https://, ftp://), editor MUST automatically detect and convert them to clickable hyperlinks
- **FR-007**: Profile selector MUST persist the last selected profile across editor sessions (restore on startup)
- **FR-008**: System MUST handle paste operations with mixed plain text and hyperlinks without data loss
- **FR-009**: When profile is selected and profile config defines a `styles` stylesheet path, editor MUST load and apply that stylesheet to the document
- **FR-010**: If stylesheet path in profile is invalid or file does not exist, editor MUST fall back to default/system stylesheet without error or warning dialog
- **FR-011**: When user switches profiles, the new profile's stylesheet MUST replace the previous stylesheet in the editor

### Key Entities

- **Profile**: Represents email configuration entry (from config.yml) with properties: name, default_document_path, SMTP settings, etc.
- **Document**: Editor document being edited - stores content with hyperlink markup
- **Clipboard Content**: Pasted content with optional HTML/link markup that must be preserved or processed

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can switch profiles and open documents from profile-specific directories in under 2 clicks from main window
- **SC-002**: 100% of hyperlinks from copied content remain functional after paste operation
- **SC-003**: Plain-text URLs are linkified automatically with zero manual action required
- **SC-004**: Last selected profile persists across editor restart (verified by launching editor and checking active profile)
- **SC-005**: Paste operations complete within 500ms even with large content containing multiple hyperlinks
- **SC-006**: Profile stylesheet loads and applies to editor within 200ms of profile selection
- **SC-007**: Stylesheet switching between profiles produces no visual artifacts or document corruption

## Assumptions

- Config.yml profile structure includes optional `styles` field containing path to CSS stylesheet
- Users have write access to config.yml for profile management
- Quill.js editor (current rich-text engine) supports HTML link preservation via paste events
- Hyperlink auto-detection should recognize standard URL schemes: http://, https://, ftp://
- Profile selector UI will be simple dropdown - no complex filtering required in v1
- Auto-linkification should only apply to plain text pastes, not already-formatted hyperlinks (avoid double-conversion)
- Markdown link syntax `[text](url)` should not be auto-linkified again if already in markdown format
- Stylesheet paths in profile config are absolute or user-expandable (support ~ for home directory)
- Stylesheet should be applied via Quill's styling API or CSS injection into editor canvas
- Profile without `styles` defined will use editor's default stylesheet (no fallback to previous profile's stylesheet)
