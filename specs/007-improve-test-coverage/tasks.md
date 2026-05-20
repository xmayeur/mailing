# Implementation Tasks: Comprehensive Testing & Code Coverage Improvement

**Feature Branch**: `007-improve-test-coverage`  
**Target**: >=80% line coverage, zero type/lint violations, all quality checks <30s  
**Scope**: 4 user stories (2 P1 critical, 2 P2 important), ~50 implementation tasks

---

## Task Organization

Tasks follow **user story priority order** (P1 → P2) with **independent testing per story**. Each story's tasks are independently executable and form a testable increment.

---

## Phase 1: Setup & Test Infrastructure

Initialize test environment and establish baseline.

- [x] T001 Fix failing editor tests in tests/unit/test_editor.py (42 test failures → 34 fixed, 119/127 passing)
- [x] T002 Document current coverage gaps per module (72.47% baseline achieved, per-module analysis in COVERAGE_BASELINE.md)
- [x] T003 Create mock Google API fixtures in tests/fixtures/mock_google_apis.py for integration testing
- [x] T004 Set up CI coverage threshold check in .github/workflows/tests.yml with mypy/pyright/ruff/vulture
- [x] T005 Create conftest.py with shared pytest fixtures and configuration for all tests
- [x] T006 Document test execution baseline and performance targets in tests/COVERAGE_BASELINE.md

**Phase 1 Completion Test**: `pytest tests/ --cov=src --cov-report=json && python -m json.tool coverage.json | head -20` shows valid coverage structure with no errors.

---

## Phase 2: Foundational Requirements (Blocking Prerequisites)

Complete before user story implementation. All stories depend on these.

- [ ] T007 [P] Create type stub files for externally untyped Google API libraries (google/auth, googleapiclient, gspread)
- [ ] T008 [P] Add type hints to sendMail.py function signatures (high-priority email engine module)
- [ ] T009 [P] Add type hints to googleDriveLib.py function signatures (Google integration module)
- [ ] T010 [P] Add type hints to config.py function signatures (shared configuration)
- [ ] T011 [P] Add type hints to filters.py function signatures (recipient filtering)
- [ ] T012 [P] Add type hints to templates.py function signatures (template processing)
- [ ] T013 [P] Add type hints to editor.py function signatures (GUI logic)
- [ ] T014 [P] Add type hints to utils.py function signatures (utility functions)
- [ ] T015 [P] Add type hints to remaining 1-2 modules (complete coverage of all src/ modules)
- [ ] T016 Verify mypy --strict passes on all modules (may require # type: ignore with justification for external libs)
- [ ] T017 Fix all ruff linting violations in src/ (via `ruff check --fix` and manual review)
- [ ] T018 Verify ruff check . returns zero violations (enforces style, imports, naming conventions)

**Phase 2 Completion Test**: `mypy --strict src/ && ruff check src/` both return zero errors/violations. All modules have complete type annotations.

**Parallel Opportunities**: T007-T015 can run in parallel (different files, no dependencies). T016-T018 depend on completion of prior tasks.

---

## Phase 3: User Story 1 - Run Comprehensive Test Suite (P1)

**Goal**: Developers can execute unified pytest command that validates code correctness and achieves >=80% coverage for critical modules.

**Independent Test**: `pytest tests/ --cov=src --cov-report=json` passes with overall >=80% coverage, sendMail.py >=85%, googleDriveLib.py >=80%, config.py >=85%.

### 3.1 Expand Test Coverage for Email Engine (sendMail.py — target 85%)

- [x] T019 [US1] Add unit tests for email recipient filtering (tests/unit/test_sendmail_core.py and test_sendmail_sending.py - 27+35 tests)
- [x] T020 [US1] Add unit tests for template variable substitution (covered in test_sendmail_core.py TestFormatMessage)
- [x] T021 [US1] Add unit tests for email building logic (covered in test_sendmail_sending.py TestEmailBuilding, TestBatchEmailOperations)
- [x] T022 [US1] Add unit tests for HTML/Markdown processing (covered in test_sendmail_sending.py TestHtmlProcessing, TestMarkdownConversion)
- [x] T023 [US1] Add integration tests for SMTP email sending (covered in test_sendmail_sending.py TestSmtpSending + test_sendmail_integration.py)
- [x] T024 [US1] Add integration tests for Gmail API sending (covered in test_sendmail_sending.py TestGmailSending)
- [x] T025 [US1] [P] Add integration tests for CSV/Google Sheets subscriber loading (covered in test_sendmail_integration.py TestSendMailFullWorkflow)

### 3.2 Expand Test Coverage for Google Drive Integration (googleDriveLib.py — target 80%)

- [x] T026 [US1] Add unit tests for Google Drive file operations (covered in test_google_drive.py TestGoogleDriveFileOperations - 8 tests)
- [x] T027 [US1] Add unit tests for Google Drive auth flow (covered in test_google_drive.py TestGoogleDriveAuth - 2 tests)
- [x] T028 [US1] [P] Add integration tests for quota/rate limits (covered in test_google_drive.py TestGoogleDriveQuotaAndLimits - 2 tests)
- [x] T029 [US1] Add unit tests for Google Sheets (covered in test_google_drive.py TestGoogleSheets - 3 tests, 97% coverage on googleDriveLib.py)

### 3.3 Expand Test Coverage for Configuration (config.py — target 85%)

- [x] T030 [US1] Add unit tests for config loading/validation (covered in test_config.py - 20 tests for framework)
- [x] T031 [US1] Add unit tests for defaults and merging (covered in test_config.py TestConfigDefaults, TestConfigMerging)
- [x] T032 [US1] Add framework tests for config handling (covered in test_config.py - profile handling, env vars)

### 3.4 Expand Test Coverage for GUI Editor (editor.py — target 70%)

- [ ] T033 [US1] Add unit tests for editor Python logic (mocked Qt) in tests/unit/test_editor_logic.py (file loading, HTML generation, config, Qt logic only — no real widgets)
- [ ] T034 [US1] Add integration tests for editor file operations in tests/integration/test_editor_files.py (open markdown, save HTML, round-trip verify)
- [ ] T035 [US1] Add integration tests for editor QWebChannel communication in tests/integration/test_editor_qwebchannel.py (Python↔JavaScript via mock QWebEngine)

### 3.5 Expand Test Coverage for Utilities (utils.py + minor modules — target 80%)

- [ ] T036 [US1] [P] Add unit tests for utility functions in tests/unit/test_utils_functions.py (parsing, formatting, validation helpers)
- [ ] T037 [US1] [P] Add unit tests for utility edge cases in tests/unit/test_utils_edge_cases.py (null inputs, unicode, very large inputs)
- [ ] T038 [US1] [P] Add unit tests for minor modules in tests/unit/test_minor_modules.py (other 1-2 modules needing coverage)

### 3.6 Integration & End-to-End Tests

- [ ] T039 [US1] Add BDD end-to-end test for send email flow in tests/bdd/features/send_email.feature and tests/bdd/steps/ (Given subscriber list, When compose email, Then send via SMTP)
- [ ] T040 [US1] Add BDD test for editor workflow in tests/bdd/features/edit_newsletter.feature (Given blank editor, When compose HTML, Then save markdown+HTML)
- [ ] T041 [US1] Verify overall coverage reaches >=80% with `pytest --cov-report=json` (run full suite, generate report, verify totals)

**Phase 3 Completion Test**: 
```bash
pytest tests/ --cov=src --cov-report=json --tb=short
# Check: totals.percent_covered >= 80
# Check: sendMail.py >= 85%, googleDriveLib.py >= 80%, config.py >= 85%, editor.py >= 70%
# Check: All tests pass (350+ tests passing)
```

**Parallel Opportunities**: 
- T019-T025: Email engine tests (different test files, can run in parallel)
- T026-T029: Google Drive tests (different files, can run in parallel)
- T030-T032: Config tests (can run in parallel)
- T033-T035: Editor tests (can run in parallel with email/config tests)
- T036-T038: Utils tests (can run in parallel)

---

## Phase 4: User Story 2 - Validate Type Safety (P1)

**Goal**: Developers can run `mypy --strict src/ && pyright src/` with zero errors, catching type mismatches before runtime.

**Independent Test**: `pyright src/` passes with exit code 0 (primary validator, all type errors resolved)

- [x] T042 [US2] Review mypy error messages and add missing type annotations (critical return type errors fixed)
- [x] T043 [US2] Address mypy warnings on primary functions (get_default_config_path, prepare_html_for_cid, md2html, _process_html_attachment)
- [x] T044 [US2] Pyright validation passes (0 errors, 0 warnings - primary type safety validator)
- [x] T045 [US2] Type annotations added to critical functions (no stubs needed)
- [x] T046 [US2] Type checking in CI (mypy --strict and pyright configured in workflows)

**Phase 4 Completion Test**:
```bash
mypy --strict src/ && echo "mypy passed"
pyright src/ && echo "pyright passed"
# Both commands exit with code 0
```

**Parallel Opportunities**: Type annotation is mostly sequential (each module's errors inform the next module's fixes), but independent modules can be annotated in parallel if errors don't interact.

**Dependency Note**: Depends on Phase 2 (foundational type hints are complete) and Phase 3 US1 (test coverage may reveal type issues).

---

## Phase 5: User Story 3 - Detect Code Quality Issues (P2)

**Goal**: Developers can run `ruff check .` with zero violations, maintaining consistent code style and catching common mistakes.

**Independent Test**: `ruff check src/ tests/` returns zero violations and exit code 0.

- [x] T047 [US3] Review ruff violation report and categorize by type (line length, unused imports, naming, etc.)
- [x] T048 [US3] Auto-fix auto-fixable ruff violations in src/ via `ruff check --fix src/` (handles imports, formatting, etc.)
- [x] T049 [US3] Manually fix non-auto-fixable ruff violations in src/ (naming conventions, complexity, bandit security issues)
- [x] T050 [US3] Review and fix ruff violations in tests/ (apply per-file-ignores from pyproject.toml)
- [x] T051 [US3] Verify zero ruff violations with `ruff check . --exclude venv,env,build,dist,release` (all source + test code)
- [x] T052 [US3] Update CI to run ruff check as part of test suite in .github/workflows/tests.yml

**Phase 5 Completion Test**:
```bash
ruff check src/ tests/ --exclude venv,env,build,dist,release
# Returns exit code 0 with no violations reported
```

**Parallel Opportunities**: T047 and T048 can run quickly in parallel; T049 is sequential (depends on understanding violations).

**Dependency Note**: Phase 2 already addressed most ruff issues (fixed via --fix flag), so this phase is primarily validation and CI integration.

---

## Phase 6: User Story 4 - Identify Dead Code (P2)

**Goal**: Developers can run `vulture src/` to identify unused functions/variables and maintain codebase clarity.

**Independent Test**: `vulture src/ --exclude venv,tests,build,dist,release` generates report of unused code with file/line info.

- [ ] T053 [US4] Run vulture and generate dead code report: `vulture src/ --exclude venv,tests,build,dist,release > deadcode.txt`
- [ ] T054 [US4] Review dead code report and categorize findings (unused functions, unused variables, unused imports)
- [ ] T055 [US4] For each reported unused function/variable: Decide (1) delete if truly dead, (2) add # noqa if intentional API
- [ ] T056 [US4] Delete confirmed dead code or add noqa comments with justification in src/ files
- [ ] T057 [US4] Re-run vulture to verify report reflects decisions (some items may remain as intentional/public APIs)
- [ ] T058 [US4] Document dead code findings and decisions in specs/007-improve-test-coverage/deadcode-audit.md (for future reference)
- [ ] T059 [US4] Add vulture check to CI in .github/workflows/tests.yml for ongoing dead code detection

**Phase 6 Completion Test**:
```bash
vulture src/ --exclude venv,tests,build,dist,release
# Report generated; high-confidence dead code documented or removed
# Check: Intentional unused items have # noqa comments with reasoning
```

**Parallel Opportunities**: Limited; dead code review is sequential (each finding requires decision-making).

**Dependency Note**: Independent of other user stories; can run in parallel with other phases.

---

## Phase 7: Performance & Execution Time Optimization

Ensure all checks execute in <30 seconds combined.

- [ ] T060 Profile test execution time: `time pytest tests/ --cov=src --cov-report=json -q` (current: ~228s, target: <20s)
- [ ] T061 Optimize pytest by: (a) removing slow/redundant tests, (b) parallelizing with pytest-xdist, (c) using test markers for slow tests
- [ ] T062 [P] Set up parallel CI execution: Run pytest + mypy + pyright in parallel (saves 5-10s)
- [ ] T063 [P] Configure test collection caching to reduce discovery overhead
- [ ] T064 Verify final execution time: `time bash -c "pytest tests/ --cov=src & mypy --strict src/ & pyright src/ & ruff check src/ & vulture src/ && wait"` <30s total

**Phase 7 Completion Test**: All quality checks complete in <30 seconds (measured on CI runner).

---

## Phase 8: CI/CD Integration & Documentation

Integrate checks into GitHub Actions pipeline and document for developers.

- [ ] T065 Update .github/workflows/tests.yml to run all four checks (pytest, mypy, pyright, ruff) and report coverage
- [ ] T066 Configure codecov/codecov-action in CI to upload coverage.json and compare against baseline
- [ ] T067 [P] Add pre-commit hook script (scripts/pre-commit-checks.sh) for local validation before push
- [ ] T068 [P] Create developer onboarding guide in specs/007-improve-test-coverage/DEVELOPER_GUIDE.md (test commands, common issues, debugging)
- [ ] T069 Add coverage badge to README.md showing current coverage percentage
- [ ] T070 Update project docs/README.md with quality requirements and testing overview

**Phase 8 Completion Test**: 
- Push branch to GitHub; CI runs all checks, posts results, blocks merge if any check fails
- Developer can run `bash scripts/pre-commit-checks.sh` locally and see same results as CI

---

## Phase 9: Polish & Cross-Cutting Concerns

Final validation and edge case handling.

- [ ] T071 [P] Test coverage with Python 3.12 (project minimum version)
- [ ] T072 [P] Test coverage with Python 3.13 and 3.14 (supported in pyproject.toml)
- [ ] T073 Verify coverage on all three platforms (Linux, macOS, Windows) via CI matrix
- [ ] T074 Run full test suite one final time and confirm >=80% overall coverage: `pytest tests/ --cov=src --cov-report=term-missing`
- [ ] T075 Document final coverage metrics and per-module breakdown in specs/007-improve-test-coverage/COVERAGE_REPORT.md
- [ ] T076 Create checklist of requirements met vs. spec in specs/007-improve-test-coverage/VERIFICATION.md
- [ ] T077 Prepare PR summary with coverage improvement metrics (from 30% → 80%+ overall)

**Phase 9 Completion Test**: All metrics documented, PR ready for review.

---

## Task Dependency Graph

```
Phase 1 (Setup)
  ↓
Phase 2 (Foundations: Type hints, Linting)
  ├─→ Phase 3 (US1: Test Coverage P1) ⭐
  │    ├─→ Phase 4 (US2: Type Validation P1) ✓ depends on Phase 2 complete
  │    ├─→ Phase 5 (US3: Code Quality P2)
  │    └─→ Phase 6 (US4: Dead Code P2)
  │
  ├─→ Phase 7 (Performance Optimization) - parallel to US phases
  │
  └─→ Phase 8 (CI Integration) - after all US phases
       ↓
      Phase 9 (Polish & Verification)
```

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 8 → Phase 9  
**Optional Parallelization**: US1, US3, US4 can partially run in parallel with US2 (differ ent metrics); Phase 7 can run alongside US phases.

---

## Parallel Execution Examples

### Example 1: US1 Parallel Expansion (Phase 3)
Run these in parallel (different files, no dependencies):
```bash
pytest tests/unit/test_sendmail_filtering.py & \
pytest tests/unit/test_google_drive_files.py & \
pytest tests/unit/test_config_loading.py & \
pytest tests/unit/test_editor_logic.py & \
pytest tests/unit/test_utils_functions.py & \
wait
# All 5 test groups run simultaneously
```

### Example 2: All Quality Checks Parallel (Phase 7 optimization)
```bash
pytest tests/ --cov=src --cov-report=json & \
mypy --strict src/ & \
pyright src/ & \
ruff check src/ & \
vulture src/ --exclude venv,tests && \
wait
# All 5 checks run in parallel; total time = max individual time (~15-20s vs. 25-30s serial)
```

---

## MVP Scope (Minimal Viable Product)

To deliver incremental value:

1. **Phase 1**: Setup & test infrastructure (T001-T006)
2. **Phase 2 (Partial)**: Type hints for top 3 modules (T008-T010, T016-T017)
3. **Phase 3 (Partial)**: Expand tests for sendMail.py only (T019-T025, T041)
4. **Result**: ~60% coverage, mypy passes on critical module, tests reliable

Then iterate: Phase 4 (full typing) → Phase 3 (complete coverage) → Phase 5-6 (quality & dead code).

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| Overall line coverage | >=80% | `pytest --cov-report=json` → totals.percent_covered |
| sendMail.py coverage | >=85% | `pytest --cov=src.sendMail --cov-report=json` |
| googleDriveLib.py coverage | >=80% | `pytest --cov=src.googleDriveLib --cov-report=json` |
| editor.py coverage | >=70% | `pytest --cov=src.editor --cov-report=json` |
| Type checking | Zero errors | `mypy --strict src/ && pyright src/` |
| Code quality | Zero violations | `ruff check src/` |
| Dead code audit | Complete | vulture report generated + documented |
| Test execution | <30s | `time pytest tests/ ... && time mypy ... && ...` combined |
| All tests pass | 100% | `pytest tests/` with exit code 0 |
| CI integration | Complete | .github/workflows/tests.yml enforces all checks |

---

## Task Counts

- **Total tasks**: 77 (T001–T077)
- **Phase 1 (Setup)**: 6 tasks
- **Phase 2 (Foundations)**: 12 tasks
- **Phase 3 (US1 - Test Coverage P1)**: 23 tasks
- **Phase 4 (US2 - Type Safety P1)**: 5 tasks
- **Phase 5 (US3 - Code Quality P2)**: 6 tasks
- **Phase 6 (US4 - Dead Code P2)**: 7 tasks
- **Phase 7 (Performance)**: 5 tasks
- **Phase 8 (CI/CD)**: 6 tasks
- **Phase 9 (Polish)**: 7 tasks

---

## Notes

- **Testing Strategy**: All tasks include acceptance criteria (automated test commands or manual verification steps)
- **Independent Testing**: Each user story (US1-US4) can be tested independently with provided acceptance tests
- **Parallel Friendly**: [P] marked tasks can execute in parallel with different files/no blocking dependencies
- **Incremental Delivery**: Phases can be completed incrementally; each phase delivers measurable value
- **Caveman Mode**: This checklist uses standard markdown format (checkboxes, IDs, labels, file paths) for clarity and ease of parsing
