# Phase 0: Testing & Coverage Research

**Date**: 2026-05-20  
**Goal**: Resolve unknowns and establish testing strategy for >=80% coverage goal

## Research Findings

### R1: GUI Testing Strategy for PyQt6 + Quill.js

**Unknown**: How to test PyQt6 editor GUI without launching full application? What's testable at unit level vs. integration level?

**Investigation**:
- PyQt6 testing: Can use QTest framework for UI interactions, or mock Qt components for logic testing
- Quill.js integration: JavaScript-heavy; best tested via integration tests (QWebEngine handles JS execution)
- Current approach in editor.py: Uses QWebChannel for Python↔JS communication
- Project structure: editor.py is independent binary (never imported by sendMail.py per CLAUDE.md)

**Decision**: 
- **Unit tests**: Test Python logic (toolbar state, config loading, file I/O) by mocking Qt components where possible
- **Integration tests**: Test editor binary startup, Quill.js rendering, Python-JS communication via QWebEngine
- **GUI interactions**: Limited unit testing; focus on functional coverage (save, load, HTML generation)
- **Coverage target for editor.py**: 70% (GUI code inherently harder to test than core logic)

**Rationale**: PyQt6 GUI logic is testable, but widget interactions require integration tests. Quill.js is tested via QWebEngine interactions. Pragmatic balance: strict unit testing for business logic, integration tests for UI flows. 70% target reflects GUI complexity while pushing for higher coverage on testable components.

**Alternatives considered**:
- Mock all Qt components: Too brittle; loses confidence in actual rendering/widget behavior
- Only integration tests: Too slow; misses unit-testable logic
- Exclude GUI from coverage: Violates feature requirement (comprehensive testing)

---

### R2: Current Coverage Gaps by Module

**Unknown**: Which modules have lowest coverage? Where to focus expansion efforts?

**Investigation**:
- Run coverage baseline to identify gaps
- 9 source modules, 392 existing tests
- Priority modules from spec: sendMail.py (email logic), googleDriveLib.py (API integration), editor.py (GUI)

**Decision**:
- Generate coverage report identifying modules <80%
- Prioritize in order: 
  1. Core email logic (sendMail.py) — highest impact for business function
  2. Google Drive integration (googleDriveLib.py) — external API, needs mocking strategy
  3. Configuration handling (config.py) — shared across CLI/GUI
  4. Template processing (templates.py) — complex string logic
  5. GUI editor (editor.py) — last due to complexity

**Rationale**: Focus on critical path first (email sending), then integrations, then nice-to-haves. This order maximizes value per test written.

**Alternatives considered**:
- Equal effort across all modules: Inefficient; some code is simpler to test
- GUI first: Slow return on investment; GUI testing is expensive

---

### R3: Test Execution Performance

**Unknown**: Can all checks (pytest, mypy, pyright, ruff, vulture) run in <30s target?

**Investigation**:
- Current pytest count: 392 tests
- Typical pytest + coverage: 10-20s for this size
- mypy --strict: 2-5s
- pyright: 1-3s
- ruff check: <1s
- vulture: <1s
- Total: ~15-30s baseline (likely achievable)

**Decision**:
- Target 30s total execution time for all checks combined
- Parallelize where possible (ruff, vulture are fast; can run in parallel with pytest)
- Optimize pytest discovery (already configured in pytest.ini)

**Rationale**: 30s is acceptable for pre-commit/CI context. Parallel execution achieves goal without sacrificing coverage.

**Alternatives considered**:
- Stricter 15s target: Too aggressive; mypy + pyright alone approach this
- Lazy execution (skip some checks): Reduces quality gates

---

### R4: Google API Mocking & Integration Testing

**Unknown**: Should Google API calls be mocked in tests or use integration tests with real credentials?

**Investigation**:
- Project uses service accounts for Google API access (per googleDriveLib.py)
- oauth2client + google-auth + google-auth-oauthlib in dependencies
- Test fixtures exist (pytest-mock available)
- CI environment: GitHub Actions (can inject credentials as secrets)

**Decision**:
- **Unit tests**: Mock Google API responses using pytest-mock (googleapiclient.discovery.build returns mock client)
- **Integration tests**: Optional, only for critical flows; use real credentials in CI via GitHub Secrets
- **Mocking strategy**: Create fixture for mock Google Drive client in tests/fixtures/mock_google_apis.py
- **Credentials handling**: Test code should never hardcode credentials; use environment variables in CI

**Rationale**: Mocking allows fast, isolated tests. Integration tests provide confidence for critical flows. Separation lets developers run unit tests locally without credentials.

**Alternatives considered**:
- All integration tests: Too slow; not practical for TDD workflow
- No mocking (real API calls in tests): Fragile, rate-limited, slow, security risk

---

### R5: Coverage Measurement & Reporting

**Unknown**: How to track progress toward 80% goal? What coverage metrics matter most?

**Investigation**:
- pytest-cov already configured (line coverage, term-missing, html, json reports)
- Coverage report: --cov-report=html, --cov-report=json
- Codecov integration: Currently at 30%

**Decision**:
- Metric: **Line coverage** (% of lines executed by tests), not branch coverage
- Tracking: Use pytest-cov JSON report for CI integration
- Success: >=80% overall, with per-module breakdown
- Exclude: build/, dist/, release/, venv/, tests/ themselves
- Report format: HTML + JSON for CI systems + manual review

**Rationale**: Line coverage is standard, easier to reason about than branch/path coverage. JSON report integrates with CI dashboards.

**Alternatives considered**:
- Branch coverage: More strict but overkill for this codebase
- Exclude more code: Reduces actual coverage, defeats purpose

---

## Summary of Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| GUI testing | Unit (mocked Qt) + Integration (QWebEngine) | Balance test isolation with real widget behavior |
| Coverage target for editor.py | 70% (vs. 80% for other modules) | GUI code inherently harder to test |
| Module priority | Email logic → Integrations → Config → Templates → GUI | Critical path first |
| Test performance | Parallel execution, <30s target | Pre-commit/CI practicality |
| API mocking | Mock unit tests + optional integration tests | Fast development loop + confidence |
| Coverage metric | Line coverage, >=80% overall, per-module breakdown | Standard, CI-friendly, measurable |

## Assumptions Validated

✅ pytest + coverage infrastructure in place  
✅ Type checking tools available (mypy 2.0+, pyright 1.1+)  
✅ Linting tools available (ruff 0.15+)  
✅ Dead code detector available (vulture 2.16+)  
✅ CI environment supports parallel test execution  
✅ Google API credentials can be mocked/injected  
✅ PyQt6 testing is feasible via Qt framework + integration tests  

## Next Phase

Phase 1 will use these decisions to:
1. Create data-model.md with test module architecture
2. Define coverage goals per module (sendMail.py: 85%, googleDriveLib.py: 80%, editor.py: 70%, etc.)
3. Create quickstart.md for running test suite
4. Define contract for coverage reports (JSON format, per-module breakdown)
