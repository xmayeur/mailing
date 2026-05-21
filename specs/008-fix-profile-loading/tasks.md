# Tasks: Fix Profile Loading and Configuration

**Input**: Design documents from `/specs/008-fix-profile-loading/`  
**Prerequisites**: plan.md, spec.md, data-model.md, quickstart.md  
**Branch**: `008-fix-profile-loading`

**Tests**: Not explicitly requested in feature spec; integration tests recommended for profile loading flow  
**Organization**: Tasks grouped by user story (P1: US1, US2, US3 → P2: US4 → P3: US5)

## Format: `- [x] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3, US4, US5)
- All paths absolute or relative from repo root

---

## Phase 1: Setup (Project Structure & Test Infrastructure)

**Purpose**: Establish test structure and audit existing code

- [x] T001 Create test structure: `tests/test_profile_loading.py`, `tests/test_editor_styling.py`, `tests/test_filter_persistence.py`
- [x] T002 [P] Audit `src/sendMail.py` for log.info calls (doc list in `docs/logging-audit.md`)
- [x] T003 [P] Audit `src/editor.py` for log.info calls (add to audit doc)
- [x] T004 [P] Audit remaining modules (`src/*.py`) for log.info vs log.debug classification
- [x] T005 Create vault test fixture in `tests/conftest.py` (mock get-hc-secrets)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure for profile loading

**⚠️ CRITICAL**: Must complete before user story implementation

- [x] T006 [P] Add `Profile.vault_key` field to config.yml schema in `src/sendMail.py`
- [x] T007 [P] Add `filters` optional field to Profile structure in `src/sendMail.py`
- [x] T008 Implement `Profile.load_smtp_from_vault()` method in `src/sendMail.py` (returns SMTP dict, handles errors)
- [x] T009 Add error handling for missing/invalid vault keys in `src/sendMail.py` (ValueError with specific key)
- [x] T010 [P] Add vault integration tests to `tests/test_profile_loading.py` (mock vault responses)

**Checkpoint**: Profile vault loading infrastructure ready

---

## Phase 3: User Story 1 - Editor Applies Selected Profile Style (Priority: P1)

**Goal**: Editor renders profile-specific styling when file opened or profile selected

**Independent Test**: Open file in editor, select different profiles, verify styling updates match profile template

### Implementation for User Story 1

- [x] T011 [US1] Read profile template file path from profile config in `src/editor.py`
- [x] T012 [US1] Implement `Editor.get_profile_template()` method in `src/editor.py` (load template CSS/HTML)
- [x] T013 [US1] Implement `Editor.apply_profile_styling(profile_name)` in `src/editor.py` (applies CSS, updates Quill theme)
- [x] T014 [US1] Add profile selection dropdown to editor UI in `editor_assets/editor.html` (or Qt widget)
- [x] T015 [US1] Connect profile selection to `apply_profile_styling()` in `src/editor.py`
- [x] T016 [US1] Test: Verify styling persists when switching profiles in `tests/test_editor_styling.py`
- [x] T017 [US1] Test: Verify inline content preserved when styling changes in `tests/test_editor_styling.py`

**Checkpoint**: Editor applies profile styling on selection and file open

---

## Phase 4: User Story 2 - SMTP Parameters Loaded from Vault (Priority: P1)

**Goal**: Profile SMTP credentials loaded from vault when profile selected

**Independent Test**: Select artscroises profile, verify SMTP host/port/auth come from vault, not config defaults

### Implementation for User Story 2

- [x] T018 [US2] Modify profile selection logic in `src/sendMail.py` to call `Profile.load_smtp_from_vault()`
- [x] T019 [US2] Cache SMTP params in profile object after vault fetch (store in `Profile.smtp_host`, etc.)
- [x] T020 [US2] Validate vault key format in config.yml ("mailconfig: xxx") in `src/sendMail.py`
- [x] T021 [US2] Add retry logic for vault fetch in `src/sendMail.py` (3 retries, 100ms backoff)
- [x] T022 [US2] Log vault fetch success/failure in `src/sendMail.py` (at log.debug level)
- [x] T023 [US2] Add test for successful vault fetch in `tests/test_profile_loading.py`
- [x] T024 [US2] Add test for missing vault key error handling in `tests/test_profile_loading.py`
- [x] T025 [US2] Add test for stale cache invalidation in `tests/test_profile_loading.py` (reload profile)

**Checkpoint**: Profile vault loading works end-to-end

---

## Phase 5: User Story 3 - Fix SMTP Error for Artscroises Profile (Priority: P1)

**Goal**: Artscroises profile sends emails without SMTP connection error

**Independent Test**: Select artscroises profile, send test email, verify no SMTP error

**Note**: This story depends on US2 (vault loading) but can be tested independently once US2 complete

### Implementation for User Story 3

- [x] T026 [US3] Verify SMTP connection before send in `src/sendMail.py` (use loaded vault params, not defaults)
- [x] T027 [US3] Add SMTP connection timeout handling in `src/sendMail.py` (5s timeout, specific error message)
- [x] T028 [US3] Log SMTP connection details (host, port, timeout) at log.debug level in `src/sendMail.py`
- [x] T029 [US3] Add specific error message for SMTP auth failures in `src/sendMail.py`
- [x] T030 [US3] Test: Send email via artscroises profile (integration test) in `tests/test_profile_loading.py`
- [x] T031 [US3] Test: Handle SMTP connection failure gracefully in `tests/test_profile_loading.py`
- [x] T032 [US3] Test: Verify error messages include host/port/auth for debugging in `tests/test_profile_loading.py`

**Checkpoint**: Artscroises profile sends emails successfully (SMTP error fixed)

---

## Phase 6: User Story 4 - Replace Debug Logging (Priority: P2)

**Goal**: Production logs at INFO level contain only user-relevant events

**Independent Test**: Run app, filter logs at INFO level, verify no diagnostic debug messages

### Implementation for User Story 4

- [x] T033 [US4] Replace debug-level log.info with log.debug in `src/sendMail.py` (2 calls: lines 953, 960)
- [x] T034 [P] [US4] Replace debug-level log.info with log.debug in `src/editor.py` (11 calls converted)
- [x] T035 [P] [US4] Replace debug-level log.info in `src/googleDriveLib.py` (no calls found)
- [x] T036 [P] [US4] Replace debug-level log.info in `src/schema_provider.py` (no calls found)
- [x] T037 [P] [US4] Replace debug-level log.info in remaining modules (no calls found)
- [x] T038 [US4] Test: Verify no debug messages at INFO level in `tests/test_profile_loading.py` ✓ PASS
- [x] T039 [US4] Test: Verify debug messages appear at DEBUG level in `tests/test_profile_loading.py` ✓ PASS

**Checkpoint**: All debug logging migrated to log.debug

---

## Phase 7: User Story 5 - Save Filter to Profile Config (Priority: P3)

**Goal**: Users can save active filters to profile; filters restore on profile load

**Independent Test**: Apply filter, save to profile, restart app, verify filter restored

### Implementation for User Story 5

- [x] T040 [US5] Extend Profile class with `filters` field in `src/sendMail.py`
- [x] T041 [US5] Implement `Profile.save_filters(filter_criteria)` method in `src/sendMail.py` (serialize to config.yml)
- [x] T042 [US5] Implement `Profile.load_filters()` method in `src/sendMail.py` (deserialize from config.yml)
- [x] T043 [US5] Update profile load in `src/sendMail.py` to call `load_filters()` on startup
- [x] T044 [US5] Add filter save UI trigger to `src/editor.py` or `src/sendMail.py` (on user request)
- [x] T045 [US5] Validate filter criteria before save in `src/sendMail.py` (schema check via existing validator)
- [x] T046 [US5] Test: Save and restore filter to profile config in `tests/test_filter_persistence.py`
- [x] T047 [US5] Test: Verify filter persists across restart (file I/O test) in `tests/test_filter_persistence.py`
- [x] T048 [US5] Test: Handle invalid filter criteria on save in `tests/test_filter_persistence.py`

**Checkpoint**: Filter persistence to profile config works

---

## Phase 8: Integration & Polish

**Purpose**: End-to-end testing and cross-cutting improvements

- [x] T049 [P] Integration test: Full flow (profile select → vault load → SMTP connect) in `tests/integration/test_profile_flow.py`
- [x] T050 [P] Integration test: Editor + sendMail profile sync in `tests/integration/test_profile_flow.py`
- [x] T051 Documentation: Add profile vault configuration guide to `docs/PROFILES.md`
- [x] T052 Documentation: Update CLAUDE.md with profile loading architecture
- [x] T053 Code review: Check all profile loading paths use vault params, not defaults
- [x] T054 Test quickstart.md validation scenarios in `tests/test_profile_loading.py`
- [x] T055 Verify no regressions in existing email sending (other profiles still work)

**Checkpoint**: Feature complete and integrated

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Phase 1 (Setup)**: No dependencies → START IMMEDIATELY
2. **Phase 2 (Foundational)**: Depends on Phase 1 → BLOCKS all user stories
3. **Phases 3-7 (User Stories)**: All depend on Phase 2 completion
   - US1 (Editor, P1): Can start after Phase 2
   - US2 (Vault, P1): Can start after Phase 2
   - US3 (SMTP, P1): Depends on US2 completion but can be tested independently
   - US4 (Logging, P2): Can start after Phase 2 (independent)
   - US5 (Filters, P3): Can start after Phase 2 (independent)
4. **Phase 8 (Polish)**: Depends on most/all user stories

### Critical Path

```
Phase 1 (5h) 
  ↓
Phase 2 (8h) ← BLOCKS stories
  ↓
Phase 3 (US1: Editor, 6h) ─┐
Phase 4 (US2: Vault, 8h) ──┼→ Phase 5 (US3: SMTP, 4h, depends on US2)
Phase 6 (US4: Logging, 4h) ┤
Phase 7 (US5: Filters, 6h) ┘
  ↓
Phase 8 (Polish, 3h)
```

### Parallel Opportunities

- **Phase 1**: All audit tasks [P] can run in parallel (T002-T004)
- **Phase 2**: Schema updates [P] can run in parallel (T006-T007)
- **Phase 3 & 4**: US1 (Editor) and US2 (Vault) can run in parallel (different files)
- **Phase 4 & 6**: US2 (Vault) and US4 (Logging) can run in parallel
- **Phase 6**: Logging changes [P] can run in parallel (T034-T037, different files)
- **Post Phase 2**: If 5-person team, assign: US1 + US2 + US4 + US5 in parallel, then US3

### Parallel Example: Phase 6 (Logging Migration)

```
Team A: T033 (sendMail.py) - 1h
Team B: T034 (editor.py) - 1h  [P]
Team C: T035 (googleDriveLib.py) - 30m  [P]
Team D: T036 (schema_provider.py) - 30m  [P]
Team E: T037 (other modules) - 1h  [P]

Then sequential: T038-T039 (testing, 1h)
```

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

For fastest delivery with core value:
1. **Phase 1**: Setup + audits (1 day)
2. **Phase 2**: Foundational vault loading (1 day)
3. **Phase 4**: US2 vault loading (1 day) ← Core value: fix SMTP error
4. **Phase 5**: US3 SMTP fix verification (0.5 day)

**Total MVP: 3.5 days**  
**Delivers**: Artscroises profile SMTP error fixed ✅

### Incremental Delivery

1. **Iteration 1** (4 days): MVP above
2. **Iteration 2** (3 days): Add US1 (editor styling) + Phase 8 integration
3. **Iteration 3** (2 days): Add US4 (logging) + US5 (filters)
4. **Iteration 4** (1 day): Polish and final testing

---

## Summary

**Total Tasks**: 55  
**Critical Path Duration**: ~30h (with parallel work)  
**MVP Scope**: T001-T010, T018-T032 (20 tasks, ~18h)

| Story | Tasks | Duration | Priority | Status |
|-------|-------|----------|----------|--------|
| US1 (Editor) | T011-T017 | 6h | P1 | Blocked on Phase 2 |
| US2 (Vault) | T018-T025 | 8h | P1 | Blocked on Phase 2 |
| US3 (SMTP) | T026-T032 | 4h | P1 | Blocked on US2+Phase 2 |
| US4 (Logging) | T033-T039 | 4h | P2 | Blocked on Phase 2 |
| US5 (Filters) | T040-T048 | 6h | P3 | Blocked on Phase 2 |

**Checkpoints**:
- ✅ After Phase 1: Test infrastructure ready
- ✅ After Phase 2: Vault loading works
- ✅ After Phase 3: Editor styling works
- ✅ After Phase 4: SMTP vault params load
- ✅ After Phase 5: SMTP error fixed (MVP complete)
- ✅ After Phase 6: Logging cleaned up
- ✅ After Phase 7: Filter persistence works
- ✅ After Phase 8: Feature fully integrated
