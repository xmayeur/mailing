# Tasks: Non-Python Test Coverage

**Input**: Design documents from `/specs/010-non-python-tests/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md (contracts/ skipped: repo-internal tooling)

**Tests**: This feature consists of test modules, so every story's implementation tasks are checks; each story additionally includes a defect-injection verification task, requested by the spec via SC-002 (write check, inject defect, confirm red-then-green).

**Organization**: Tasks grouped by user story (spec.md priorities) so each story can be implemented and tested independently. All paths repository-root-relative.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story from spec.md (US1..US6); setup/foundational/polish tasks carry no story label
- Exact file paths in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency and helper groundwork, no behavior change to any gate yet.

- [x] T001 Add `"shellcheck-py"` to the `[dependency-groups] testing` list in `pyproject.toml` and regenerate `poetry.lock` (`poetry lock`); the CI lockfile-check job must stay green
- [x] T002 [P] Create `tests/unit/support/repo_files.py`: repo root resolution, `git ls-files` tracked-file enumeration with glob-pattern matching per class (R-02), and a not-a-git-repo guard that skips with reason

**Checkpoint**: `poetry run pytest tests/unit -q` unchanged-green; `shellcheck --version` resolves inside the poetry env.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared checker helpers and the FR-011/FR-012 coverage registry that every story registers against. MUST be complete before any user story.

- [x] T003 [P] Extend `tests/unit/support/repo_files.py`: strict duplicate-key-rejecting YAML loader (`yaml.SafeLoader` subclass) and JSON loader (`object_pairs_hook`, R-05/R-06); CRLF-normalizing `bash -n` runner via stdin (R-04); shellcheck sub-process harness with `shutil.which` skip-with-reason guards and subprocess timeouts (FR-008)
- [x] T004 Create `tests/unit/coverage_inventory.json`: machine-readable registry per `specs/010-non-python-tests/data-model.md` — the five classes (editor-markup, shipped-vendor-js, first-party-css, automation-scripts, declarative-configs) with patterns/defect-classes/owning-test fields, and the full exclusion ledger from research R-10 (release trees, dist_nuitka, binaries/certs, XML family, diagram formats, `.specify` scripts, Makefile/.bat, extensionless dotfiles)
- [x] T005 Create `tests/unit/test_coverage_inventory.py`: registry validation (strict parse, patterns non-empty, exclusion entries carry reasons) plus the FR-012 self-audit — every tracked non-Python file matches at least one class or one exclusion, otherwise fail naming the file
- [x] T006 Create `tests/unit/coverage_inventory.md`: the FR-011 documentation — covered classes, defect classes caught, exclusions with reasons, and the cover-or-exclude extension recipe — generated from and kept in sync with `tests/unit/coverage_inventory.json`

**Checkpoint**: `tests/unit/test_coverage_inventory.py` passes on the untouched tree (all tracked non-Python files map to a class or exclusion) — the registry-first design keeps each subsequent story commit green.

---

## Phase 3: User Story 1 — Broken editor markup caught before it ships (Priority: P1) — MVP

**Goal**: The editor asset bundle (`src/editor_assets/`) is internally consistent and structurally verified on every gate run.
**Independent Test**: Delete or corrupt one editor asset in a scratch clone — the suite fails naming the file; restore it — the suite passes.

### Implementation for User Story 1

- [x] T007 [US1] Extend `tests/unit/test_editor_assets.py`: reference-existence check — every local `<script src=...>`/`<link href=...>` in `src/editor_assets/editor.html` resolves to a file under `src/editor_assets/` (today: `quill.js`, `qwebchannel.js`, `quill.snow.css`)
- [x] T008 [US1] Extend `tests/unit/test_editor_assets.py`: bootstrap-component invariants — `#editor-container` and `#toolbar` present, exactly one `new QWebChannel(qt.webChannelTransport...` and one `new Quill(` in `src/editor_assets/editor.html`
- [x] T009 [US1] Extend `tests/unit/test_editor_assets.py`: shipped-vendor script syntax — `node --check` over `src/editor_assets/quill.js` and `src/editor_assets/qwebchannel.js`, same skip-with-reason guard as the existing inline-script test
- [x] T010 [US1] Extend `tests/unit/test_editor_assets.py`: host↔editor bridge contract — object names from `registerObject(...)` in `src/editor.py` must appear as `channel.objects.<name>` in `src/editor_assets/editor.html` (research R-08)
- [x] T011 [US1] Defect-injection verification (SC-002 subset) in a scratch clone: missing reference, removed bootstrap component, broken inline JS, corrupted vendor JS — each fails naming the file; update the US1 section of `tests/unit/coverage_inventory.md`

**Checkpoint**: MVP — editor bundle guarded on commit, push, and CI; remaining stories can proceed in parallel.

---

## Phase 4: User Story 2 — Shell script defects caught automatically (Priority: P1)

**Goal**: Every repo-authored shell script parses and passes static analysis; latent findings are fixed behavior-preservingly.
**Independent Test**: A single-character syntax error or an unquoted expansion seeded in any script fails the suite naming that file.

### Implementation for User Story 2

- [x] T012 [US2] Create `tests/unit/test_shell_scripts.py`: `bash -n` syntax check for every file matched by the automation-scripts inventory patterns (`scripts/*.sh`, `.githooks/pre-commit`), using the CRLF-normalizing stdin runner and which-guard from `tests/unit/support/repo_files.py`
- [x] T013 [US2] Extend `tests/unit/test_shell_scripts.py`: shellcheck static-analysis pass (error and warning severities fail) for the same pattern set, skip-with-reason when `shellcheck` is absent locally, never on CI
- [x] T014 [US2] Baseline and remediation: run shellcheck across all inventory automation scripts; fix flagged findings behavior-preservingly (quoting, `--` guards, explicit error handling) in `scripts/*.sh` and `.githooks/pre-commit`, one finding-group per commit (research R-11)
- [x] T015 [US2] Defect-injection verification in a scratch clone: seeded syntax error plus one defect per FR-004 lint class — unquoted expansion, unset variable use, masked command failure — each fails naming file + finding; update the US2 section of `tests/unit/coverage_inventory.md`

**Checkpoint**: All repo-authored shell scripts parse, lint clean, and are gated everywhere.

---

## Phase 5: User Story 3 — New checks everywhere, zero manual steps (Priority: P1)

**Goal**: Inclusion in every existing quality gate is proven, not assumed: commit-time, pre-push, and the 3-OS CI matrix, with no silent skips.
**Independent Test**: A seeded defect in a covered asset fails at each gate surface with no extra invocation or setup.
**Note**: T016–T019 verify with the US1/US2 checks in place; config/style classes from later phases re-verify collectively in Phase 9 (T030).

- [x] T016 [US3] Commit-gate verification: run `scripts/pre-commit-checks.sh` against a seeded defect on a scratch clone — the existing `.githooks/pre-commit` flow fails naming the file with zero script edits (record evidence in `specs/010-non-python-tests/quickstart.md`)
- [x] T017 [US3] Pre-push verification: same seeded defect fails via `scripts/pre_push_checks.sh` including the coverage-gated pytest invocation; confirm the `--cov=src` ratio is unaffected by the new test modules
- [x] T018 [US3] CI verification: confirm `.github/workflows/tests.yml` needs no edit — the pytest steps pick up the new modules; verify (and record) that all three operating systems provide `bash` and `node`, and that `shellcheck` arrives via the exported testing requirements, so no check skips on any matrix leg
- [x] T019 [US3] Skip-transparency verification: every new module reports skips only as `SKIPPED (reason)` (tool absent), surfaced via `pytest -rs`; assert the helper contract in `tests/unit/support/repo_files.py` (skip-with-reason, never silent pass — FR-008)

**Checkpoint**: Wiring proven end-to-end; every asset class added by later stories inherits the same surfaces automatically.

---

## Phase 6: User Story 4 — Declarative configuration validated beyond workflows (Priority: P2)

**Goal**: Every tracked YAML/JSON/TOML file — first-party, IDE, and tool-installed alike — parses strictly, including duplicate-key detection.
**Independent Test**: Duplicating a top-level entry in a covered config fails the suite naming file and key; well-formed tree passes.

### Implementation for User Story 4

- [x] T020 [P] [US4] Create `tests/unit/test_declarative_configs.py`: strict YAML, strict JSON, and `tomllib` parsing for every file matched by the declarative-configs inventory patterns; failures name file and offending entry (helpers from `tests/unit/support/repo_files.py`)
- [x] T021 [US4] Migrate the existing `test_github_workflows_are_valid_yaml` in `tests/unit/test_editor_assets.py` onto the strict loader so duplicate workflow keys are caught too
- [x] T022 [US4] Defect-injection verification in a scratch clone: truncated YAML in `.codecov.yml` and a duplicated top-level key each fail naming file + entry; update the US4 section of `tests/unit/coverage_inventory.md`

**Checkpoint**: The full declarative config surface (~15 files: `.codecov.yml`, `.github/build.yml`, `.github/dependabot.yml`, `.github/workflows/*.yml`, `.pre-commit-config.yaml`, `.readthedocs.yaml`, `poetry.toml`, `pyproject.toml`, `pyrightconfig.json`, `src/config.yml`, `.specify/*.yml`, `.specify/*.json`) is gated.

---

## Phase 7: User Story 5 — Stylesheet defects caught early (Priority: P2)

**Goal**: First-party stylesheets fail gates when structurally broken, without false positives on valid content braces.
**Independent Test**: Removing a closing brace from `css/styles.css` fails the suite naming the file; the current asset passes.

### Implementation for User Story 5

- [x] T023 [US5] Create `tests/unit/test_stylesheets.py`: comment- and string-aware brace tokenizer over the first-party-css inventory patterns (`css/**/*.css`); assert rule-block balance and non-truncation, per research R-07
- [x] T024 [US5] Defect-injection verification in a scratch clone: unbalanced rule fails naming `css/styles.css`; a content-string containing `}` passes (false-positive guard); update the US5 section of `tests/unit/coverage_inventory.md`

**Checkpoint**: Stylesheet class gated with zero false positives on current assets.

---

## Phase 8: User Story 6 — Vendor and build boundaries respected (Priority: P3)

**Goal**: Checks stay inside the working repository: excluded trees are provably unexamined, vendor JS is parse-only, vendor CSS is existence-only.
**Independent Test**: A corrupted vendor script fails; files under excluded trees never affect outcomes or runtime.

### Implementation for User Story 6

- [x] T025 [US6] Extend `tests/unit/test_coverage_inventory.py` (pattern-level, via `tmp_path` fixture copies of the registry — never by committing files to excluded trees): files matching FR-009 exclusions (`release/**`, `dist_nuitka/**`, binary/cert/diagram families, `.specify` scripts) are never enumerated by any class check
- [x] T026 [US6] Assert vendor semantics in `tests/unit/test_editor_assets.py` and document in `tests/unit/coverage_inventory.md`: shipped-vendor JS parse-checked only (no style lint), `quill.snow.css` checked for existence only (FR-006 bounds balance checks to first-party CSS)

**Checkpoint**: Boundary discipline is itself tested; misclassification becomes a visible gate failure.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Invariant hardening and the feature's own acceptance measures.

- [x] T027 [P] Harden `tests/unit/test_coverage_inventory.py` per the data-model rule: every class's `owning_test` path must exist on disk (all five owning modules now present) and every exclusion entry must carry a reason
- [x] T028 [P] Runtime budget (FR-010/SC-004): measure `poetry run pytest tests/unit -q --durations=10` before and after the feature on the same machine; record both values in `specs/010-non-python-tests/quickstart.md`
- [x] T029 Run the full SC-002 defect-injection trial — all ten defect classes listed in `specs/010-non-python-tests/quickstart.md` — and record 100%-caught evidence in that file
- [x] T030 Final SC-003 gate-surface run: repeat the seeded-defect verification across commit-time, pre-push, and CI matrix evidence; record results in `specs/010-non-python-tests/quickstart.md`
- [x] T031 Final consistency pass: `tests/unit/coverage_inventory.md` matches `tests/unit/coverage_inventory.json`; run the `specs/010-non-python-tests/quickstart.md` steps end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. T001 and T002 are independent of each other.
- **Foundational (Phase 2)**: Depends on T001 (shellcheck runtime for the harness) and T002 (enumeration). T003 is independent of T004–T006. T005 depends on T004; T006 follows T004.
- **User Stories (Phases 3–8)**: All depend on Phase 2 completion (registry + helpers). Stories are otherwise independent and can proceed in parallel except US3's verifications (T016–T018), which need US1 and US2 checks landed.
- **Polish (Phase 9)**: Depends on all stories complete.

### User Story Completion Order

Recommended: US1 → US2 → US3 → US4 → US5 → US6. US3's evidence is completed by T030 after later stories land; US4/US5/US6 may run in parallel with US3.

### Within Each User Story

Checks first, defect-injection verification last (red-then-green), documentation update attached to the same task that lands the class.

### Parallel Opportunities

- Phase 1: T001 ∥ T002
- Phase 2: T003 ∥ (T004 → T005 → T006)
- After Phase 2: US1, US2, US4, US5, US6 are file-disjoint and fully parallelizable (five separate `tests/unit/test_*.py` modules + doc sections); US2's T014 remediation is self-contained
- Phase 6: T020 ∥ T021
- Phase 9: T027 ∥ T028

---

## Parallel Example: User Story 2 alongside User Story 4 (different files)

```text
Task: "T012 [US2] Create tests/unit/test_shell_scripts.py: bash -n syntax check ..."
Task: "T020 [US4] Create tests/unit/test_declarative_configs.py: strict YAML/JSON/TOML parsing ..."
# different test modules, different asset classes — safe to run in parallel
```

---

## Implementation Strategy

### MVP First (Foundational + US1)

1. Complete Phase 1 and Phase 2 (registry + helpers + self-audit passing)
2. Complete Phase 3 (US1)
3. **STOP and VALIDATE**: inject the four US1 defects; all four fail naming files
4. MVP: the highest-defect-rate asset class (editor bundle) is guarded on every existing gate with zero pipeline changes

### Incremental Delivery

1. Setup + Foundational → registry green on untouched tree
2. + US1 → validate → MVP
3. + US2 (checks, then baseline remediation) → validate
4. + US3 → gate-surface evidence
5. + US4 → + US5 → validate (defect injections)
6. + US6 → boundary tests
7. Polish → runtime budget, full SC-002 trial, SC-003 evidence, docs freeze

Each increment leaves the tree green and the gates active.

---

## Notes

- [P] tasks = different files, no dependencies between them
- Story labels map tasks to spec.md user stories for traceability
- Every check must fail with file + reason (FR-002) and skip only with reason (FR-008) — assert both in the defect-injection tasks
- Commit after each task or logical group; the pre-commit gate itself runs the growing suite
- Defect injections happen in scratch clones only — never commit broken assets
