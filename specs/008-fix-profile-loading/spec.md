# Feature Specification: Fix Profile Loading and Configuration

**Feature Branch**: `008-fix-profile-loading`  
**Created**: 2026-05-21  
**Status**: Draft  
**Input**: User description: "Create a new branch and a new feature to address the following fixes: when opening a file in the editor.py, the default style is applied instead of the one from the selected profile; when selecting artscroises profile, SMTP parameters are not loaded from mailconfig: artscroisesmailing vault key; in sendMail.py, using artscroises profile, sending a mail returns an SMTP error; many log.info messages are debug messages -> replace by log.debug() instead; save filter to profile config (on request)"

## Clarifications

### Session 2026-05-21

- Q1: SMTP caching strategy → A: Per-session cache (invalidate on profile switch, no stale values mid-session)
- Q2: Editor profile initialization → A: Remember last used profile per session (standard editor UX pattern)
- Q3: Vault unreachable fallback → A: Fail hard with specific error (security-critical credentials, no silent stale fallback)
- Q4: Filter column validation on schema change → A: Validate on load, skip invalid criteria with warning (non-blocking)
- Q5: Profile loading logging level → A: Debug level only (verbose flag enables DEBUG output, reduces INFO noise)

## User Scenarios & Testing

### User Story 1 - Editor Applies Selected Profile Style (Priority: P1)

When a user opens a newsletter file in the editor, the HTML/styling should reflect the selected email profile's template style, not the default style.

**Why this priority**: Editor must respect user profile choice immediately to provide correct visual previews of outgoing emails.

**Independent Test**: Can be fully tested by opening a file in editor with different profile selections and verifying style matches profile template.

**Clarification**: Editor remembers last used profile per session. On startup, editor loads the profile from the previous session (standard editor UX). User can change profile via dropdown before or after opening file.

**Acceptance Scenarios**:

1. **Given** user opens editor with no file, **When** editor loads last profile and user opens a file, **Then** file renders using that profile's styling
2. **Given** file is open in editor, **When** user switches profile selection from dropdown, **Then** content re-renders with new profile's style
3. **Given** editor opens a .html file, **When** profile context is loaded, **Then** any existing inline styles are preserved but template defaults match profile

---

### User Story 2 - SMTP Parameters Loaded from Vault (Priority: P1)

When selecting a profile in sendMail.py or editor.py, SMTP connection parameters should be loaded from the configured vault key (e.g., "mailconfig: artscroisesmailing") rather than falling back to defaults.

**Why this priority**: SMTP connection is essential for sending emails; incorrect parameters cause send failures. This is the root cause of the artscroises SMTP error.

**Independent Test**: Can be fully tested by selecting artscroises profile and verifying SMTP host/port/auth parameters are loaded from vault, not defaults.

**Clarifications**: 
- **Caching**: SMTP parameters cached per-session. When user switches profile, cache invalidated and fresh vault fetch occurs. This ensures "no cached stale values" within a session.
- **Vault Failure**: If vault is unreachable/times out, system fails with specific error message (e.g., "Vault unreachable: connection timeout"). No fallback to stale credentials. User must resolve vault access or choose different profile.
- **Logging**: Profile loading (vault fetch, SMTP validation) logged at log.debug level only. Enable with verbose flag for troubleshooting. No INFO-level logging during profile selection.

**Acceptance Scenarios**:

1. **Given** artscroises profile is selected, **When** sendMail initializes SMTP, **Then** SMTP host/port come from vault key "mailconfig: artscroisesmailing" and cached for session
2. **Given** vault key contains updated SMTP credentials, **When** profile is switched, **Then** new credentials fetched (cache invalidated on profile change)
3. **Given** vault key is missing or unreachable, **When** profile is selected, **Then** user receives specific error message with cause (e.g., "Vault unreachable" or "Vault key not found: mailconfig: artscroises")

---

### User Story 3 - Fix SMTP Error for Artscroises Profile (Priority: P1)

Sending emails via artscroises profile currently fails with an SMTP error. Root cause is incorrect SMTP parameters; fixing Story 2 (vault loading) resolves this.

**Why this priority**: Feature is non-functional for this profile; users cannot send emails. This is the highest-impact blocker.

**Independent Test**: Can be fully tested by selecting artscroises profile, composing a test email, and verifying send succeeds without SMTP error.

**Acceptance Scenarios**:

1. **Given** artscroises profile is configured in config.yml, **When** user sends test email via sendMail, **Then** email sends successfully
2. **Given** SMTP parameters are correct (loaded from vault), **When** multiple emails are sent, **Then** all send without connection errors
3. **Given** SMTP fails to connect, **When** error occurs, **Then** log contains specific error (host/port/auth details) for debugging

---

### User Story 4 - Replace Debug Log.info with Log.debug (Priority: P2)

Many log.info calls emit debugging information that should use log.debug level instead, reducing noise in production logs.

**Why this priority**: Improves observability by reducing info-level log spam; log.debug only appears when debug logging enabled.

**Independent Test**: Can be fully tested by running app and verifying info logs contain only user-relevant events, not debug details.

**Acceptance Scenarios**:

1. **Given** app runs with default logging, **When** debug messages are emitted, **Then** they appear at log.debug level, not log.info
2. **Given** developer enables debug logging, **When** app runs, **Then** detailed debug messages are visible
3. **Given** production logging at INFO level, **When** app runs, **Then** only relevant operational events appear in logs

---

### User Story 5 - Save Filter to Profile Config (Priority: P3)

On request, the system should save active filters to the profile configuration so they persist across sessions.

**Why this priority**: Nice-to-have workflow improvement; user must explicitly request it (not automatic).

**Independent Test**: Can be fully tested by applying a filter, saving to profile, restarting app, and verifying filter is restored.

**Acceptance Scenarios**:

1. **Given** user applies a filter in sendMail, **When** user requests "save filter to profile", **Then** filter criteria saved to config.yml
2. **Given** filter is saved to profile, **When** app restarts and profile is loaded, **Then** filter is automatically applied
3. **Given** user removes or modifies filter, **When** profile is saved again, **Then** previous saved filter is overwritten

---

### Edge Cases

- What happens when vault key is misconfigured in config.yml?
- How does system handle profile with no SMTP parameters defined?
- What if editor opens file before profile is fully loaded?
- How should filter saving handle invalid or conflicting filter criteria?

## Requirements

### Functional Requirements

- **FR-001**: System MUST load SMTP parameters from configured vault key when profile is selected; MUST cache per-session and invalidate on profile switch
- **FR-002**: System MUST apply selected profile's styling/template when opening files in editor; editor remembers last used profile per session
- **FR-003**: Editor MUST update rendered style when profile selection changes; existing content preserved
- **FR-004**: System MUST validate SMTP parameters before attempting connection and report specific errors; if vault unreachable, fail with specific error (no stale credential fallback)
- **FR-005**: System MUST use log.debug for non-critical diagnostic messages instead of log.info; profile loading logged at debug level only (enable with verbose flag)
- **FR-006**: System MUST provide mechanism for user to request filter persistence to profile config
- **FR-007**: System MUST load saved filters from profile config on startup; validate filter criteria against current schema, skip invalid with warning
- **FR-008**: System MUST handle missing or invalid vault keys with specific error messages (vault unreachable vs. key not found); fail hard, no silent fallback

### Key Entities

- **Profile**: Configuration containing email service settings, styling/template preferences, rate limits, and optional persistent filters; SMTP params cached per-session
- **SMTP Parameters**: Host, port, authentication credentials, encryption method; loaded from vault, cached per-session, invalidated on profile switch
- **Vault Key**: Reference to secrets manager entry (e.g., "mailconfig: artscroisesmailing") containing SMTP credentials; failure to load results in specific error (no fallback)
- **Filter**: User-defined criteria for subscriber filtering, optionally persisted to profile; validated on load against current schema, invalid criteria skipped with warning

## Success Criteria

### Measurable Outcomes

- **SC-001**: Artscroises profile sends emails successfully on first attempt (100% send success rate vs. current SMTP error)
- **SC-002**: Editor renders profile-specific styling immediately when profile is selected (no manual refresh needed)
- **SC-003**: Profile-specific SMTP parameters load from vault within 500ms of profile selection
- **SC-004**: Production logs at INFO level contain no debug-level diagnostic messages (reduction in info log volume)
- **SC-005**: Users can save and restore filters via profile config with 100% persistence across sessions
- **SC-006**: Error messages for vault/profile configuration issues are specific enough to guide user to fix (zero ambiguous "profile failed" errors)

## Assumptions

- Vault infrastructure (get-hc-secrets) is available and configured in config.yml
- Profile names match vault key names (e.g., profile "artscroises" → vault key "mailconfig: artscroisesmailing")
- Log.debug is sufficient for diagnostic messages; no separate logging infrastructure needed
- Filter persistence format uses existing config.yml structure (YAML)
- Editor profile selection is persisted in session state (not across app restarts unless explicitly saved)
- SMTP error currently occurs because vault key is not being loaded (root cause, not design issue)
