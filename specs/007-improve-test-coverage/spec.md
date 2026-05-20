# Feature Specification: Comprehensive Testing & Code Coverage Improvement

**Feature Branch**: `007-improve-test-coverage`  
**Created**: 2026-05-20  
**Status**: Draft  
**Input**: User description: "Codecov measures only 30-ish % of code coverage for this project. Create a new feature to fully test (ruff, mypy, pyright, vulture, pytest...) the current branch and make a plan to achieve >=80% of coverage overall"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Comprehensive Test Suite (Priority: P1)

Developers need ability to execute a unified test suite that validates code correctness, coverage, and quality across all components (email engine, editor, Google Drive integration, CLI argument parsing).

**Why this priority**: Core requirement for achieving coverage goals and catching regressions before deployment.

**Independent Test**: Can be tested by running `pytest` command and verifying output shows >=80% coverage report with detailed per-module breakdown.

**Acceptance Scenarios**:

1. **Given** developer on current branch, **When** running pytest command, **Then** all tests pass and coverage report shows >=80% overall
2. **Given** new code added to sendMail.py, **When** running tests, **Then** coverage report includes new code
3. **Given** test failure, **When** developer runs tests, **Then** failure message identifies exact file/line and reason

---

### User Story 2 - Validate Type Safety (Priority: P1)

Developers need type checking to catch runtime errors before execution. Current codebase uses some typing but lacks strict validation.

**Why this priority**: Type safety prevents entire classes of bugs (attribute errors, method signature mismatches) and documents expected input/output contracts.

**Independent Test**: Can be tested by running `mypy --strict` and `pyright` and verifying zero errors reported.

**Acceptance Scenarios**:

1. **Given** all modules, **When** running mypy with strict mode, **Then** no errors reported
2. **Given** all modules, **When** running pyright, **Then** no errors or warnings reported
3. **Given** untyped function parameter, **When** type checker runs, **Then** error explicitly identifies missing type annotation

---

### User Story 3 - Detect Code Quality Issues (Priority: P2)

Developers need automated feedback on code quality violations (style, unused imports, incorrect patterns) to maintain consistency with project standards.

**Why this priority**: Code quality issues don't block functionality but accumulate technical debt and make maintenance harder.

**Independent Test**: Can be tested by running `ruff check .` and verifying zero violations reported.

**Acceptance Scenarios**:

1. **Given** all Python files, **When** running ruff linter, **Then** no violations reported
2. **Given** unused import, **When** running ruff, **Then** violation identified with file/line
3. **Given** line exceeding 127 character limit, **When** running ruff, **Then** violation flagged

---

### User Story 4 - Identify Dead Code (Priority: P2)

Developers need to identify unreachable or unused code to reduce maintenance burden and clarify intent.

**Why this priority**: Dead code increases complexity for maintainers and can hide bugs. Lower priority than correctness checks but valuable for codebase health.

**Independent Test**: Can be tested by running `vulture` tool and reviewing report of unused code/imports.

**Acceptance Scenarios**:

1. **Given** all modules, **When** running vulture, **Then** report identifies unused functions/variables
2. **Given** unused test fixture, **When** vulture runs, **Then** fixture listed as unused with location
3. **Given** unused import in config.yml handling, **When** vulture runs, **Then** import flagged

---

### Edge Cases

- What happens when new file added without tests? (Coverage gap detection)
- How does system handle vendored/external code in dependencies? (Exclude from coverage)
- What if type hints contradict runtime behavior? (Type checker catches before merge)
- How to handle legacy untyped code? (Phased typing approach vs. gradual migration)
- Should test coverage report exclude certain paths? (e.g., build artifacts, vendor code)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Test suite MUST execute via single command and report coverage metrics to standard output
- **FR-002**: Coverage report MUST identify coverage percentage per module (sendMail.py, editor.py, googleDriveLib.py, config handling)
- **FR-003**: Type checking MUST execute via mypy with `--strict` mode and report zero errors
- **FR-004**: Type checking MUST execute via pyright and validate all type annotations
- **FR-005**: Code quality checker MUST execute via ruff and enforce project linting rules
- **FR-006**: Dead code detector MUST execute via vulture and report unused code
- **FR-007**: All checks MUST integrate into CI/CD pipeline and block merge on failure
- **FR-008**: Coverage report MUST track progress toward 80% target and identify uncovered code paths
- **FR-009**: Developers MUST have local command to run all checks before pushing (pre-commit equivalent)
- **FR-010**: CI pipeline MUST fail if coverage drops below 80% or checks fail

### Key Entities

- **TestSuite**: Collection of pytest tests covering all modules
- **CoverageReport**: Per-module coverage metrics and uncovered line identification
- **TypeAnnotations**: Function signatures, variable declarations with type hints
- **LintRules**: Project coding standards enforced by ruff (line length, imports, naming)
- **UnusedCode**: Functions, variables, imports identified as unreachable/unused

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Code coverage reaches 80% or higher as measured by pytest coverage plugin
- **SC-002**: All modules pass mypy type checking with zero errors in strict mode
- **SC-003**: All modules pass pyright type validation with zero errors
- **SC-004**: Ruff linting reports zero violations across codebase
- **SC-005**: Vulture identifies all unused code in comprehensive report (developers then triage findings)
- **SC-006**: All 4 test tools (pytest, mypy, pyright, ruff) can execute in under 30 seconds total
- **SC-007**: CI pipeline executes all checks and blocks PR merge if any check fails
- **SC-008**: Developers can run all checks locally with single command before push

## Assumptions

- Python version 3.12+ is target runtime (per pyproject.toml)
- Test coverage tools (pytest-cov, mypy, pyright, ruff, vulture) can be installed as dev dependencies
- Google API credentials/mocking is handled in existing test fixtures
- External library code (google-api-python-client, gspread, etc.) is excluded from coverage targets
- "80% coverage" refers to line coverage, not branch coverage
- Existing test structure in `tests/` directory is baseline for expansion
- Type annotations will be added incrementally to untyped code (gradual typing approach, not all-at-once)
- CI/CD pipeline uses GitHub Actions (per .github/workflows/)
- ruff configuration in pyproject.toml can be extended/updated without breaking existing linting
