# Feature Specification: Database Schema Caching

**Feature Branch**: `002-cache-db-schema`  
**Created**: 2026-05-17  
**Status**: Draft  
**Input**: User description: "Only read once the database schema and cache it so long the profile does not change"

## User Scenarios & Testing

### User Story 1 - Load Cached Schema on Profile Selection (Priority: P1)

When user opens Send Newsletter window or switches profiles, schema is loaded from cache if profile hasn't changed. Cache is only invalidated when a different profile is selected.

**Why this priority**: Performance foundation—eliminates redundant schema reads, speeds up filter validation and record preview.

**Independent Test**: Can be tested by selecting same profile multiple times and verifying schema load time is <50ms (cached) vs normal time (uncached).

**Acceptance Scenarios**:

1. **Given** fresh application start with profile A, **When** window opens, **Then** schema loads from database and caches with profile A as key
2. **Given** cached schema for profile A, **When** profile A selected again, **Then** schema loaded from cache (not from database)
3. **Given** cached schema for profile A, **When** user switches to profile B, **Then** cache invalidates and schema loads from database for profile B
4. **Given** profile B schema cached, **When** user switches back to profile A, **Then** original cached schema for A is still valid and reused

---

### User Story 2 - Detect Schema Changes Within Same Profile (Priority: P2)

User can manually refresh schema if underlying database has changed while same profile is selected. Optional refresh button or API.

**Why this priority**: Handles edge case where database schema changes (columns added/removed) without profile change.

**Independent Test**: Can be tested by modifying database structure and calling refresh, verifying updated schema is loaded.

**Acceptance Scenarios**:

1. **Given** cached schema, **When** database columns change and user requests refresh, **Then** schema reloads from database
2. **Given** no explicit refresh requested, **When** same profile remains selected, **Then** cached schema continues to be used (no automatic polling)

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST cache database schema keyed by profile name
- **FR-002**: Cache MUST persist for duration of application session (not persisted to disk)
- **FR-003**: Cache MUST invalidate and reload when profile changes
- **FR-004**: System MUST load schema from cache on subsequent profile selection if profile unchanged
- **FR-005**: System MUST provide optional manual refresh mechanism to reload schema even if profile unchanged
- **FR-006**: System MUST handle case where database connection fails—cache not updated, existing cache remains valid
- **FR-007**: Schema cache key MUST include profile name (not just database source)—different profiles may point to different databases

### Key Entities

- **Schema Cache**: In-memory map of profile name → database schema. Attributes: profile_name, field_names, loaded_timestamp
- **Profile**: Email profile from config.yml. Key attribute: name
- **Database Schema**: List of column names from active database source (CSV header row or Google Sheets column names)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Schema load from cache completes in <50ms (vs typical uncached load of 500ms+)
- **SC-002**: First-time schema load (uncached) latency unchanged from current behavior
- **SC-003**: Cache memory footprint <1MB for typical profiles (reasonable for session-scoped in-memory storage)
- **SC-004**: All user stories independently testable and pass acceptance scenarios

## Assumptions

- Cache scope is session-only (not persisted to disk between application runs)
- Profile identity determined by profile name string from config.yml
- Single profile active at time (serial profile switches, not concurrent)
- Schema doesn't change during session unless user explicitly requests refresh

## Clarifications

None at this time.
