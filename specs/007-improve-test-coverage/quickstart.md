# Comprehensive Testing Quickstart

Getting started with the sendMail testing infrastructure for >=80% code coverage.

## Prerequisites

```bash
python -m pip install -e ".[testing,lint,dev]"
```

Installs all test, type-checking, linting, and dead-code detection tools.

## Quick Commands

### Run All Tests with Coverage

```bash
# Run pytest with coverage report
pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# Open HTML coverage report
open htmlcov/index.html
```

### Type Checking

```bash
# Strict type checking
mypy --strict src/

# Alternative type checker
pyright src/
```

### Linting & Code Quality

```bash
# Check code quality
ruff check src/ tests/

# Auto-fix linting issues (where possible)
ruff check --fix src/ tests/

# Detect dead/unused code
vulture src/ --exclude venv,tests
```

### Run All Checks at Once

```bash
# Parallel execution (recommended)
pytest tests/ --cov=src --cov-report=json & \
mypy --strict src/ & \
ruff check src/ && \
vulture src/ --exclude venv,tests && \
wait

# Sequential execution (slower, good for CI)
pytest tests/ --cov=src --cov-report=json && \
mypy --strict src/ && \
ruff check src/ && \
vulture src/ --exclude venv,tests
```

## Test Structure

### Unit Tests
Test individual functions with mocked dependencies.

```bash
pytest tests/unit/ -v
```

### Integration Tests
Test module interactions and external service integrations (with mocked APIs).

```bash
pytest tests/integration/ -v
```

### BDD Tests
User-facing behavior scenarios.

```bash
pytest tests/bdd/ -v
# or
behave tests/bdd/features/
```

## Coverage Goals

| Module | Target | How to Check |
|--------|--------|--------------|
| All modules | >=80% | `pytest --cov-report=term-missing` → look for overall % |
| sendMail.py | >=85% | `pytest --cov=src.sendMail` |
| editor.py | >=70% | `pytest --cov=src.editor` |
| googleDriveLib.py | >=80% | `pytest --cov=src.googleDriveLib` |

## Common Workflows

### Adding New Tests

1. Create test file in `tests/unit/` or `tests/integration/` with name `test_*.py`
2. Import the module to test: `from src import sendMail`
3. Write test function: `def test_function_name_scenario_expected():`
4. Use mocks for external calls: `from unittest.mock import patch, MagicMock`
5. Run tests: `pytest tests/ -v`
6. Check coverage: `pytest --cov-report=term-missing | grep -A5 sendMail`

Example:

```python
# tests/unit/test_sendmail_filtering.py
import pytest
from unittest.mock import MagicMock, patch
from src.sendMail import filter_recipients

def test_filter_recipients_empty_list():
    """Empty recipient list returns empty."""
    assert filter_recipients([]) == []

def test_filter_recipients_with_duplicates():
    """Duplicate recipients are removed."""
    recipients = [
        {"email": "alice@example.com"},
        {"email": "bob@example.com"},
        {"email": "alice@example.com"},  # Duplicate
    ]
    filtered = filter_recipients(recipients)
    assert len(filtered) == 2
    assert filtered[0]["email"] == "alice@example.com"
    assert filtered[1]["email"] == "bob@example.com"
```

### Mocking Google API Calls

Use fixtures from `tests/fixtures/mock_google_apis.py`:

```python
# tests/integration/test_google_drive_integration.py
from tests.fixtures.mock_google_apis import mock_google_drive_service

def test_download_file_from_drive(mock_google_drive_service):
    """Download file from Google Drive."""
    mock_service = mock_google_drive_service
    mock_service.files().get_media().execute.return_value = b"file content"
    
    from src.googleDriveLib import download_file
    content = download_file("file_id", service=mock_service)
    
    assert content == b"file content"
```

### Running Tests in Watch Mode

```bash
pytest tests/ -v --tb=short -x  # Stop on first failure
# Or use pytest-watch plugin (optional):
ptw tests/ -- -v
```

## Troubleshooting

### Tests Fail with Import Errors
Ensure `src/` is in Python path:
```bash
export PYTHONPATH=src:$PYTHONPATH
pytest tests/
```

### Coverage Report Shows 0%
Check that pytest.ini has correct `source` and `cov-report` settings:
```bash
cat pytest.ini | grep -A10 "coverage:run"
```

### Type Checking Errors (mypy/pyright)
Add type hints or use `# type: ignore` (with justification):
```python
from typing import Any

def legacy_function(obj: Any) -> None:  # type: ignore[arg-type]
    # Reason: Legacy code without proper typing
    pass
```

### Linting Violations Won't Go Away
Some violations can be auto-fixed by ruff:
```bash
ruff check --fix src/
```

Others require manual fixes. Check the specific violation:
```bash
ruff check src/ --select E501  # Line too long, for example
```

## CI Integration

The testing pipeline runs automatically on:
- Pull request creation
- Push to `master` or development branches
- Scheduled nightly builds

See `.github/workflows/tests.yml` for details.

## Next Steps

1. **Understand current coverage**: Run `pytest --cov-report=html` and review gaps
2. **Identify critical modules**: Focus on sendMail.py (email engine) first
3. **Add tests incrementally**: Unit tests first, then integration tests
4. **Monitor progress**: Track coverage.json over time

## Resources

- pytest docs: https://docs.pytest.org/
- mypy docs: https://mypy.readthedocs.io/
- ruff docs: https://docs.astral.sh/ruff/
- Coverage.py docs: https://coverage.readthedocs.io/
