# Phase 1: Test Architecture & Coverage Model

**Date**: 2026-05-20  
**Purpose**: Define testing strategy, module-level coverage targets, and test structure

## Test Architecture

### Layers

```
Unit Tests (isolate logic via mocking)
├── Core email logic (sendMail.py)
├── Template processing (templates.py)
├── Filtering rules (filters.py)
├── Configuration (config.py)
├── Utilities (utils.py)
└── GUI logic with mocked Qt (editor.py — Python-only logic)

Integration Tests (test cross-module interactions)
├── Google Drive API with mock client
├── Email sending via SMTP/Gmail API with mock
├── File I/O and Google Sheets integration
├── Config → Email engine pipeline
└── GUI startup and QWebChannel communication

BDD Tests (user-facing workflows via Behave)
├── Send email campaign flow
├── Editor HTML compose → save → upload workflow
├── Filter and recipient list management

Acceptance Tests (system-level validation)
├── Full email sending with mocks
├── Editor binary startup and file operations
└── Multi-profile configuration handling
```

### Test Organization

```
tests/
├── unit/                        # Fast, isolated, mocked
│   ├── test_sendmail.py        # Email engine, recipient filtering
│   ├── test_templates.py       # Template variable substitution
│   ├── test_filters.py         # Filter parsing and evaluation
│   ├── test_config.py          # Config loading and validation
│   ├── test_utils.py           # Utility functions
│   ├── test_editor_logic.py    # Editor Python logic (mocked Qt)
│   └── test_html_processor.py  # HTML parsing and transformation
│
├── integration/                 # Moderate speed, real subsystems with mocks
│   ├── test_google_drive.py    # Google Drive operations (mock client)
│   ├── test_email_sending.py   # Email sending pipeline (mock SMTP/Gmail)
│   ├── test_editor_filter.py   # (existing) Editor filter validation
│   ├── test_config_email.py    # Config + email engine integration
│   └── test_google_sheets.py   # Google Sheets subscriber loading
│
├── bdd/                         # Behavior-driven scenarios
│   ├── features/
│   │   ├── send_email.feature
│   │   ├── edit_newsletter.feature
│   │   └── manage_recipients.feature
│   └── steps/
│       └── [behave step definitions]
│
├── acceptance/                  # System-level (optional, for critical flows)
│   └── test_full_campaign.py   # End-to-end campaign send
│
└── fixtures/                    # Shared test data & mocks
    ├── mock_google_apis.py     # Mock Google API clients
    ├── sample_emails.py        # Sample email configurations
    ├── sample_csvs.py          # Sample subscriber lists
    └── conftest.py             # pytest configuration & shared fixtures
```

---

## Module Coverage Model

| Module | Purpose | Current Status | Target Coverage | Testing Strategy | Complexity |
|--------|---------|-----------------|------------------|------------------|------------|
| **sendMail.py** | Email engine, CLI logic | Partial (est. 40%) | 85% | Unit: recipient filtering, template substitution, email building; Integration: SMTP/Gmail send | Medium |
| **editor.py** | PyQt6 HTML editor GUI | Low (est. 20%) | 70% | Unit: Python logic with mocked Qt; Integration: QWebEngine file I/O | High |
| **googleDriveLib.py** | Google Drive integration | Partial (est. 35%) | 80% | Unit: API call construction (mocked); Integration: file download/upload workflows | Medium |
| **config.py** | YAML config parsing | Low (est. 25%) | 85% | Unit: config loading, validation, defaults; Integration: config + email pipeline | Low |
| **templates.py** | Template variable substitution | Partial (est. 50%) | 85% | Unit: variable replacement, markdown→HTML, image embedding | Low |
| **filters.py** | Recipient filtering rules | Partial (est. 45%) | 85% | Unit: filter parsing, condition evaluation; Integration: filter + recipient list | Low |
| **utils.py** | Utility functions | Low (est. 30%) | 80% | Unit: all utilities with various inputs; edge cases | Low |
| **[4 other modules]** | Supporting functionality | Partial (est. 35%) | 80% | Module-specific unit + integration tests | Varies |
| **Overall** | All modules combined | 30% | 80% | Multi-layer approach above | — |

---

## Coverage Goals By Category

### Critical Path (Email Sending)
- sendMail.py: 85% (core business logic)
- filters.py: 85% (recipient filtering)
- templates.py: 85% (content processing)
- Overall email flow: E2E integration test

### Integrations (External Services)
- googleDriveLib.py: 80% (API interactions)
- config.py: 85% (config loading + validation)

### UI (GUI Editor)
- editor.py: 70% (GUI complexity + integration tests)
- Qt logic: Unit tested with mocks
- QWebEngine: Integration tested with real browser engine

### Quality & Utilities
- utils.py: 80% (utility functions)
- [other modules]: 80% (supporting code)

---

## Test Implementation Requirements

### Unit Test Requirements
- Arrange-Act-Assert pattern
- Mock all external dependencies (Google APIs, file I/O, Qt widgets)
- Test happy path + error cases + edge cases
- Parametrized tests for multiple scenarios (pytest.mark.parametrize)
- Clear test names describing scenario: test_<function>_<condition>_<expected_outcome>

### Integration Test Requirements
- Test cross-module interactions with mocked external services
- Use fixtures for mock Google API clients
- Realistic data samples (real email templates, recipient lists)
- Test error handling (API timeouts, auth failures, malformed responses)

### BDD Test Requirements
- Gherkin syntax: Given-When-Then
- User-focused scenarios (not implementation details)
- Shared step definitions reusable across scenarios

### Type Checking Requirements
- All function signatures fully typed (mypy --strict)
- No `type: ignore` without justification
- Type hints for all public APIs
- Internal functions may use type narrowing without explicit hints if obvious

### Linting Requirements
- ruff check passes with zero violations
- Line length 120 chars (per project config)
- Import organization (ruff I rule)
- Naming conventions (snake_case for functions/variables)

### Dead Code Requirements
- vulture reports identified unused code
- Unused functions/variables documented (keep if intentional API)
- Remove truly dead code in cleanup phase

---

## Performance Targets

| Check | Target Time | Rationale |
|-------|------------|-----------|
| pytest (all tests) | <20s | Depends on # tests & I/O; baseline ~15s |
| mypy --strict | <5s | Type checking entire codebase |
| pyright | <3s | Secondary type checker |
| ruff check | <1s | Fast linter |
| vulture | <1s | Dead code detection |
| **Total (serial)** | <30s | Acceptable for pre-commit hook |
| **Total (parallel)** | <20s | If pytest runs while type checking |

---

## Success Metrics

✅ Overall line coverage: >=80%  
✅ Module coverage breakdown: Per table above (editor.py ≥70%, others ≥80%)  
✅ Type checking: mypy --strict passes, pyright passes  
✅ Linting: ruff check zero violations  
✅ Dead code identified: vulture report generated and reviewed  
✅ Test execution: All checks complete in <30s  
✅ Test quality: 392+ existing tests passing + new tests for gaps  
✅ Documentation: Test coverage story documented per module  

---

## Test Data & Fixtures

### Mock Google API Client (tests/fixtures/mock_google_apis.py)

```python
# Mock objects for:
# - google.auth.transport.requests.Request
# - google.oauth2.credentials.Credentials
# - google.auth.service_account.Credentials
# - googleapiclient.discovery.build() → mock service
# - gspread.Spreadsheet, Worksheet, Cell
# - Mock file lists, upload responses, auth flows
```

### Sample Data (tests/fixtures/)

- sample_emails.py: Email templates, HTML, markdown samples
- sample_csvs.py: Subscriber lists (valid, malformed, edge cases)
- conftest.py: pytest fixtures, parametrize data, markers

### Configuration for Testing

- pytest.ini: Coverage threshold (already at --cov=. + --cov-report=html)
- pyproject.toml: Already has type checking + linting config
- Offline mode: Tests should not require internet (all mocks)
