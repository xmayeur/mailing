# sendMail Documentation

This directory contains the Sphinx documentation for the sendMail project.

## Building the Documentation

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Build HTML Documentation

To build the HTML documentation locally:

```bash
cd docs
make html
```

The generated HTML files will be in `_build/html/`. Open `_build/html/index.html` in your browser to view the documentation.

### Other Build Formats

Sphinx supports multiple output formats:

- **HTML**: `make html` - Standard HTML documentation
- **PDF**: `make latexpdf` - PDF via LaTeX (requires LaTeX installation)
- **EPUB**: `make epub` - EPUB format for e-readers
- **Man pages**: `make man` - Unix manual pages
- **Plain text**: `make text` - Plain text output

### Clean Build

To remove all build artifacts:

```bash
make clean
```

## ReadTheDocs Theme

This documentation uses the [ReadTheDocs Sphinx Theme](https://sphinx-rtd-theme.readthedocs.io/), which provides:

- Responsive mobile-friendly design
- Clean, professional appearance
- Easy navigation with collapsible sidebar
- Search functionality
- Customizable theme options

## Configuration

The main configuration file is `conf.py`, which includes:

- Project metadata (name, author, version)
- Sphinx extensions (autodoc, napoleon, viewcode, etc.)
- Theme configuration and options
- Module mocking for dependencies

## Structure

- `index.rst` - Main documentation page
- `sendMail.rst` - sendMail module API reference
- `googleDriveLib.rst` - Google Drive library API reference
- `conf.py` - Sphinx configuration
- `Makefile` - Build commands (Unix/Mac)
- `make.bat` - Build commands (Windows)

## ReadTheDocs Hosting

This project includes a `.readthedocs.yaml` configuration file in the repository root for hosting on ReadTheDocs.io. The configuration specifies:

- Python version (3.11)
- Ubuntu build environment
- Documentation requirements
- Sphinx configuration path

To host on ReadTheDocs:

1. Create an account at https://readthedocs.org/
2. Import your repository
3. The documentation will build automatically on each commit

## Viewing the Documentation

After building, open the documentation in your browser:

```bash
open _build/html/index.html  # macOS
xdg-open _build/html/index.html  # Linux
start _build/html/index.html  # Windows
```

## Code Quality Requirements

All code contributions must meet the following quality standards:

### Test Coverage

- **Overall Target**: ≥80% code coverage
- **Core Modules** (sendMail.py, googleDriveLib.py): ≥85% coverage
- **Configuration Modules** (config.py): ≥85% coverage
- **GUI Modules** (editor.py): ≥70% coverage (complex Qt interactions)

Current coverage: 72.5% — See [Coverage Reports](../build/coverage-reports/index.html)

### Type Checking

- **mypy --strict**: All code must pass strict type checking
  - Full type annotations required on all functions
  - No implicit Any types allowed
  - Use `# type: ignore` only for untyped external libraries (with justification)

- **pyright**: Secondary type checker for validation
  - Catches issues mypy may miss
  - Configuration in `pyproject.toml`

### Code Quality (Linting)

- **ruff check**: Fast Python linter enforcing:
  - PEP 8 style (E/W codes)
  - Import sorting (I codes)
  - Naming conventions (N codes)
  - Unused code detection (F codes)
  - Security checks (S codes)
  - Complexity rules (C codes)

- **Maximum line length**: 120 characters (enforced by ruff)
- **Code formatter**: black (optional, but ruff compatible)

### Dead Code Detection

- **vulture**: Identifies unused code and variables
  - Runs on `src/` directory
  - Warnings-only (non-blocking), but reviewed in each release
  - Framework callbacks and public APIs exempt from dead code warnings

## Testing Overview

### Test Structure

Tests are organized in `tests/` directory:

- **Unit tests** (`tests/unit/`): Fast tests with mocked dependencies
  - `test_sendmail_core.py` — Email engine functions
  - `test_sendmail_sending.py` — Message composition and sending
  - `test_google_drive.py` — Google Drive integration
  - `test_config.py` — Configuration handling
  - `test_editor.py` — GUI logic with mocked Qt

- **Integration tests** (`tests/integration/`): Real-world scenarios
  - `test_sendmail_integration.py` — End-to-end workflows
  - `test_editor_filter.py` — Filter loading (known xfail)

### Running Tests

```bash
# Run all tests
pytest tests/ -q

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test file or class
pytest tests/unit/test_sendmail_core.py -v
pytest tests/unit/test_sendmail_core.py::TestFormatMessage -v

# Run tests matching pattern
pytest -k "test_send" -v
```

### Pre-Commit Validation

Before pushing, run all quality checks:

```bash
bash scripts/pre-commit-checks.sh
```

This script validates:
- ✅ pytest (unit & integration tests with coverage)
- ✅ mypy --strict (type checking)
- ✅ pyright (secondary type validation)
- ✅ ruff check (code quality)
- ⚠️ vulture (dead code detection, warnings only)

Exit code 0 means ready to commit; non-zero indicates issues to fix.

### Known Issues

**Test Isolation**: Some test classes fail in batch execution but pass individually:
- `TestEditorWindowHelpers`, `TestSmallDialogs`, `TestConfigDialogTabBuilders`
- `TestGoogleDriveAuth`, `TestGoogleDriveErrorHandling`
- `test_editor_filter.py`

These are marked with `@pytest.mark.xfail()` and documented in source code. Root cause is shared module state in `src/editor.py` across test class executions. See `specs/007-improve-test-coverage/DEVELOPER_GUIDE.md` for workarounds.

### Continuous Integration

CI/CD pipeline runs on every push and pull request:
- Tests: pytest with coverage ≥80% threshold
- Type checking: mypy --strict + pyright
- Code quality: ruff check + vulture
- Multi-platform: Ubuntu, macOS, Windows
- Multi-version: Python 3.11+

## Developer Resources

For detailed testing and quality guidelines, see:

- [Developer Guide](../specs/007-improve-test-coverage/DEVELOPER_GUIDE.md) — Complete testing guide, type checking patterns, linting rules
- [Specification](../specs/007-improve-test-coverage/spec.md) — Feature specification for test coverage improvements
- [Code Coverage Report](../build/coverage-reports/index.html) — Detailed per-module coverage breakdown
