# Implementation Tasks: Database Schema Caching

**Feature**: Database Schema Caching  
**Branch**: `002-cache-db-schema`  
**Status**: Ready for implementation  
**Total Tasks**: 18  
**Estimated Phases**: 4 (Setup + Foundational + US1 + US2)

---

## Task Summary by Story

| Phase | User Story | Tasks | Status |
|-------|-----------|-------|--------|
| 1 | Setup | T001–T002 | Ready |
| 2 | Foundational | T003–T006 | Ready |
| 3 | US1: Cache Load | T007–T013 | Ready |
| 4 | US2: Manual Refresh | T014–T018 | Ready |

---

## Dependencies & Execution Order

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) — MUST complete before user stories
    ↓
Phase 3 (US1) ← Can run independently after Phase 2
    ↓
Phase 4 (US2) ← Depends on US1 (refresh needs working cache)
```

**Parallel Execution Within Phases**:
- Phase 2: T003 [P] and T004 [P] can run in parallel (independent files)
- Phase 3: T009 [P] and T010 [P] can run in parallel (unit tests)
- Phase 3: T012 [P] and T013 [P] can run in parallel (integration tests)

---

## Phase 1: Setup

**Goal**: Initialize project structure and dependencies for schema caching

- [x] T001 Ensure pyproject.toml has required testing dependencies (pytest, pytest-cov)
- [x] T002 Create specs/002-cache-db-schema/research.md with resolved unknowns (profile identity, cache ownership, thread safety)

---

## Phase 2: Foundational

**Goal**: Establish foundation layer—schema provider understanding, cache design, tests

**Prerequisites for all user stories**: All Phase 2 tasks must complete before US1/US2

- [x] T003 [P] Read DatabaseSchemaProvider class in src/schema_provider.py and document interface (from_csv, from_google_sheets methods)
- [x] T004 [P] Document profile loading in sendMail.py (args.conf[args.profile]) and editor.py to identify profile identity mechanism
- [x] T005 Design SchemaCacheProvider class interface (get, invalidate, refresh methods) in specs/002-cache-db-schema/data-model.md
- [x] T006 Create src/schema_cache.py with SchemaCacheProvider skeleton (docstrings, type hints, no implementation)

---

## Phase 3: User Story 1 — Load Cached Schema on Profile Selection

**Story Goal**: When user selects profile, schema loads from cache if profile unchanged; cache invalidates on profile change  
**Priority**: P1  
**Independent Test Criteria**:
- Schema loaded from cache in <50ms (vs uncached ~500ms)
- Cache key is profile name string
- Cache invalidated when profile changes
- Can be tested in isolation without US2

### Story 1 Setup

- [x] T007 [US1] Create test file tests/unit/test_schema_cache.py with fixtures for mock DatabaseSchemaProvider and test profile names

### Story 1 Implementation

- [x] T008 [US1] Implement SchemaCacheProvider.__init__() and basic cache dict in src/schema_cache.py
- [x] T009 [P] [US1] Write unit test for cache hit (T009a: test_get_returns_cached_schema_on_second_call) in tests/unit/test_schema_cache.py
- [x] T010 [P] [US1] Write unit test for cache invalidation (T010a: test_invalidate_clears_cache, T010b: test_profile_change_invalidates_old_profile) in tests/unit/test_schema_cache.py
- [x] T011 [US1] Implement SchemaCacheProvider.get(profile_name, loader) method in src/schema_cache.py
- [x] T012 [P] [US1] Write integration test for profile switching in tests/integration/test_schema_cache_integration.py (load Profile A schema, switch to B, verify B loads fresh)
- [x] T013 [P] [US1] Implement SchemaCacheProvider.invalidate(profile_name=None) method in src/schema_cache.py

### Story 1 Acceptance

- [x] T014 [US1] Integration test: Load editor, select profile A, verify schema cached; select A again, verify <50ms load; switch to profile B, verify cache miss; verify B cached on next select

---

## Phase 4: User Story 2 — Detect Schema Changes Within Same Profile

**Story Goal**: User can manually refresh schema if database changed while same profile selected  
**Priority**: P2  
**Depends on**: US1 (cache must exist and work)  
**Independent Test Criteria**:
- refresh() reloads schema from database even if profile unchanged
- refresh() updates cache with new schema
- Can be tested independently from US1 once cache infrastructure exists

### Story 2 Setup

- [x] T015 [US2] Add test fixtures for database schema changes in tests/unit/test_schema_cache.py (mock database returning different schemas)

### Story 2 Implementation

- [x] T016 [US2] Implement SchemaCacheProvider.refresh(profile_name, loader) method in src/schema_cache.py
- [x] T017 [P] [US2] Write unit tests for refresh in tests/unit/test_schema_cache.py (T017a: test_refresh_reloads_schema, T017b: test_refresh_updates_cache_with_new_schema)
- [x] T018 [US2] Integration test: Edit database schema while cached, call refresh(), verify new schema loaded and cache updated in tests/integration/test_schema_cache_integration.py

---

## Implementation Strategy

### MVP Scope (US1 only)

Deliver core caching with profile-based invalidation:
- Complete Phase 1–3 (T001–T014)
- Skip US2 for initial release
- Core value: 10x schema load speedup for filter validation in editor

### Incremental Delivery

1. **MVP Release**: US1 cache loading (T001–T014)
   - Users see immediate schema load speedup on profile selection
   - Minimal API surface (get, invalidate methods)
   
2. **Enhancement Release**: US2 manual refresh (T015–T018)
   - Enable schema reloads without app restart
   - Handles edge case of in-session database changes

### Integration Points (Phase 5 — outside this spec)

Once cache is implemented, integrate with:
- `src/editor.py`: Filter validation calls cache instead of DatabaseSchemaProvider
- `src/sendMail.py`: Profile config loading uses cache for field lookups
- (Filter editor feature 001-filter-editor-database will consume this)

---

## Validation Checklist

- [ ] All tasks have Task ID (T001–T018)
- [ ] User story tasks labeled [US1] or [US2]
- [ ] Setup/Foundational tasks have no story label
- [ ] Parallelizable tasks marked [P]
- [ ] Each task has exact file path
- [ ] Each user story independently testable
- [ ] Tests match Acceptance Scenarios from spec.md
- [ ] No task larger than 1–2 hours of effort

---

## Notes for Implementer

1. **Thread Safety**: Current plan assumes single-threaded (verify in Phase 0 research). If async required, add locks to cache dict.
2. **Session Scope**: Cache is in-memory only, not persisted to disk. Implement as application singleton or pass to components via dependency injection.
3. **Profile Identity**: Verify profile is keyed by name string (not object reference). Check both sendMail.py and editor.py for profile representation.
4. **Memory**: Typical schema is 50–300 fields → ~1–5KB per profile. Assume <100 profiles typical, <1MB total footprint.
5. **Performance**: <50ms cache hit goal should be easily met (dict lookup). Validate with actual data if necessary.

---

**Next Step**: Start Phase 1 (Setup). Review plan.md Phase 0 research to confirm profile identity, cache ownership, and thread safety before implementation.
