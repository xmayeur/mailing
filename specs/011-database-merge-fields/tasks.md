# Tasks: Database Merge Fields in Mailing Content

**Input**: Design documents from `/specs/011-database-merge-fields/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included — the spec defines measurable acceptance scenarios per story (SC-002, SC-003, SC-004, SC-005) and plan.md research decision R7 defines the test strategy (pytest unit + integration).

**Organization**: Tasks grouped by user story; each phase is an independently testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4 from spec.md)
- Exact file paths included in every description

## Path Conventions

Single project: `src/` and `tests/` at repository root (per plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a green baseline before any code changes.

- [X] T001 Run `pytest tests/unit/test_sendmail_core.py tests/unit/test_sendmail_sending.py tests/unit/test_editor.py tests/integration/test_sendmail_integration.py -q` from repo root and record the baseline result (expected: all pass — 3.7 s per commit hook runs) in the task notes

**Checkpoint**: Green baseline confirmed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Substitution core shared by US2 (per-recipient) and US3 (blank mode). MUST complete before user story phases.

**⚠️ CRITICAL**: No send-time story work can begin until this phase is complete.

- [X] T002 [P] Add unit tests for the new `format_message` contract (C1 in specs/011-database-merge-fields/contracts/README.md) to `tests/unit/test_sendmail_core.py`: known field → `str(value)`; empty/None value → `""`; unknown field → `""` per marker (not whole-template rollback); malformed text (`${`, `${X`) untouched; multiple occurrences all replaced; template argument never mutated; function never raises for data-shape reasons
- [X] T003 Harden `format_message` in `src/sendMail.py:645` to satisfy T002: resolve each `${FIELDNAME}` marker independently (known header → value or `""`, unknown header → `""`, non-markers untouched), keeping the existing signature, regex `r"\${(.*?)}"` header-lookup semantics and case-sensitivity (exact match per data-model.md)
- [X] T004 [P] Add unit tests for the new blank mode helper `format_message_blank(template) -> str` (C2 in specs/011-database-merge-fields/contracts/README.md) to `tests/unit/test_sendmail_sending.py`: every well-formed marker → `""`, malformed text untouched, never raises, returns a new string
- [ ] T005 Implement `format_message_blank` in `src/sendMail.py` co-located with `format_message` (reuse the same well-formedness regex)

**Checkpoint**: Substitution core ready — send-time stories (US2, US3) can proceed.

---

## Phase 3: User Story 1 — Insert a Database Field into the Mailing (Priority: P1) 🎯 MVP

**Goal**: User inserts `${FIELDNAME}` at the editor cursor and the marker behaves as ordinary text.

**Independent Test**: Open editor with a known-profile database, insert field, verify marker text at cursor (spec US1 scenarios 1–4).

- [X] T006 [P] [US1] Add unit tests to `tests/unit/test_editor.py` for `RichTextEditor.insert_field_marker(field_name)`: builds marker text `${FIELDNAME}`; fires the WebEngine bridge insertion (mock `runJavaScript`/view); is a no-op when the view is unavailable (existing WebEngine-failure fallback pattern)
- [X] T007 [US1] Implement `insert_field_marker` on the rich text editor class in `src/editor.py` (~line 2915 RichTextEditor): insert plain text `${{field_name}}` at the current Quill cursor via the existing `runJavaScript` bridge convention (same path as `setContent`, `src/editor.py:3224`); no page reload; no markup transformation

**Checkpoint**: MVP — a marker can be typed or inserted and reaches the stored message content unchanged.

---

## Phase 4: User Story 2 — Replace Fields with the Recipient's Value at Send Time (Priority: P1)

**Goal**: One-recipient-at-a-time sends carry that recipient's values in body and subject.

**Independent Test**: Send (or `donotsend` run) a mailing with markers to a one-recipient batch; verify outgoing body AND subject contain the values (spec US2 scenarios 1–6).

**Depends on**: Phase 2 complete.

- [X] T008 [P] [US2] Add integration tests to `tests/integration/test_sendmail_integration.py`: batch of exactly 1 addressee → body and subject markers replaced with that row's values; empty cell → `""` alongside remaining text; unknown field → `""` instead of literal marker; multiple markers → all replaced (mock transport is fine, follow existing test patterns in that file)
- [X] T009 [US2] In `_build_and_send` (`src/sendMail.py:981`): when `len(addressees) == 1`, format both the body (`format_message(param.message, row, header)`, existing) and the subject (`format_message(param.subject, row, header)` — new) and pass the formatted subject to `build_email`; keep `param.subject`/`param.message` themselves unmodified (FR-007, SC-004)

**Checkpoint**: Per-recipient personalization works end-to-end for the default flow (`max_addr_per_mail == 1`), subject included.

---

## Phase 5: User Story 3 — Blank Replacement When One Message Reaches Several Recipients (Priority: P2)

**Goal**: Batch messages to ≥2 addressees carry blank values — never a subscriber's data.

**Independent Test**: Batch two addresses in one message; verify blank where markers were (spec US3 scenarios 1–2, invariant I4 in data-model.md).

**Depends on**: Phase 2 complete (both T009 and T011 touch `_build_and_send` — implement sequentially; T009 first).

- [X] T010 [US3] In `_build_and_send` (`src/sendMail.py:981`): when `len(addressees) >= 2`, replace markers in body AND subject using `format_message_blank` from T005 instead of the last-row `format_message`; assert by construction that no row value reaches `build_email` in this branch (FR-006)
- [X] T011 [P] [US3] Add unit tests to `tests/unit/test_sendmail_sending.py` exercising the batch branch: ≥2 addressees → markers blank (no last-recipient values anywhere in outgoing message); 1 addressee → still per-recipient (guards I3 in data-model.md: no behavior change for the standard flow)

**Checkpoint**: Privacy invariant I4 holds; standard one-recipient flow unchanged.

---

## Phase 6: User Story 4 — Field Picker Lists the Actual Database Fields (Priority: P2)

**Goal**: Picker lists exactly the current profile's subscriber database headers and refreshes with profile/database changes.

**Independent Test**: Open picker with a known database; verify list equals its headers; verify refresh and unreadable-database fallback (spec US4 scenarios 1–3, SC-005).

**Depends on**: T007 (insert target must exist).

- [X] T012 [P] [US4] Add unit tests to `tests/unit/test_editor.py`: `get_field_names` returns exactly the list from `_get_database_schema()` (`src/editor.py:1269`, `SchemaCacheProvider` cached); picker list refreshes when profile/database changes (reuse existing `_load_profile_defaults` wiring at `src/editor.py:1022-1042` in the test setup); unreadable database → empty list + informational message, no insert
- [X] T013 [US4] Implement the "Insert field" entry point in `src/editor.py`: native QMenu (or equivalent Qt listing consistent with existing editor controls) whose items are the field names from `get_field_names`; each item calls `insert_field_marker(field_name)`; dismissed picker inserts nothing; unreadable database → informational message, content unchanged

**Checkpoint**: Field names come from the live database — typos via picker become impossible.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T014 Run the full check suite from repo root: `pytest tests/unit/test_sendmail_core.py tests/unit/test_sendmail_sending.py tests/unit/test_editor.py tests/integration/test_sendmail_integration.py -q` plus `pyright`, `mypy`, `ruff`, `black`, `vulture` (same set the pre-commit hook runs) and fix any new findings
- [X] T015 Execute `specs/011-database-merge-fields/quickstart.md` manual walkthrough (insert → persist → one-recipient → multi-recipient → robustness) and record results
- [ ] T016 [P] Verify success criteria SC-001–SC-005 against the implementation and update `specs/011-database-merge-fields/checklists/requirements.md` notes if acceptance gaps surface

---

## Dependencies & Execution Order

```text
Phase 1: Setup (T001)
   │
Phase 2: Foundational — substitution core (T002→T003, T004→T005)
   │
   ├─ Phase 4: US2 send-time per-recipient (T008, then T009)
   │
   └─ Phase 5: US3 blank mode (T010 after T009 — same function; T011)
        │
Phase 3: US1 insert marker (T006 → T007) — independent of Phase 2
   │
Phase 6: US4 field picker (T012, T013 after T007)
   │
Phase 7: Polish (T014 → T015 → T016)
```

### Story completion order

1. **US1** (Phase 3) — MVP: insert markers
2. **US2** (Phase 4) — personalization at send (needs Phase 2)
3. **US3** (Phase 5) — privacy blanking for batches (needs Phase 2 + T009)
4. **US4** (Phase 6) — picker hardening (needs T007)

### Parallel opportunities

- T006 ∥ T008 ∥ T012 (different test files, independent)
- T002 ∥ T004 (different test files in Phase 2)
- T011 ∥ T013 (US3 tests ∥ US4 implementation [different files])
- T016 independent of T015

## Implementation Strategy

- **MVP first**: Complete Phases 1–4 (Setup + Foundational + US1 + US2) — markers insertable and personalized single-recipient sends work; demoable increment.
- **Incremental delivery**: US3 fixes batch privacy, US4 improves picker fidelity — each isolated, each leaves the tree green.
- All send-path edits concentrate in `_build_and_send` (T009, T010): implement sequentially to avoid churn.
- Refer to `specs/011-database-merge-fields/contracts/README.md` (C1–C4) and `data-model.md` (substitution rule table) for exact expected behavior; `quickstart.md` for verification commands.
