## 1.6.0 (2026-04-29)

### Feat

- **editor**: introduce Markdown fallback and enhance stylesheet loading

### Fix

- **sonarqube**: address critical security and code quality issues

## 1.5.0 (2026-04-29)

### Feat

- **config**: add initial mailing list configurations for multiple accounts
- **editor**: add new Gmail API fields and improve profile handling

## 1.4.0 (2026-04-29)

### Feat

- **editor**: add PyInstaller spec for standalone WYSIWYG editor build

### Refactor

- **editor**: extract and modularize widget configuration and loading methods
- **editor**: centralize constants and improve maintainability

## 1.3.0 (2026-04-28)

### Feat

- **editor**: add settings dialog for managing sendMail YAML config profiles

## 1.2.0 (2026-04-28)

### Feat

- **editor**: add WYSIWYG newsletter editor with Quill.js

### Fix

- **editor**: preserve local anchor links

## 1.1.5 (2026-04-18)

## 1.1.4 (2026-04-14)

## 1.1.3 (2026-03-12)

## 1.1.2 (2026-03-10)

## 1.1.1 (2026-03-09)

## 1.1.0 (2026-03-07)

## 1.0.7 (2026-03-06)

## 1.0.6 (2026-03-06)

## 1.0.5 (2026-03-05)

## 1.0.4 (2026-03-03)

## 1.0.3 (2026-02-20)

## 1.0.2 (2026-02-19)

## 1.0.1 (2026-02-13)

## v1.7.0 (2026-05-17)

### Feat

- add Google Sheets schema validation support to filter editor
- add filter editor with database preview to SendDialog (Phase 1-7 complete)

### Fix

- skip Qt GUI tests on Linux CI (no display server)
- add graphics libraries for PyQt6 on Linux
- use xvfb for Qt6 headless testing on Linux
- use offscreen Qt platform for headless CI testing
- install Qt6 system dependencies on Linux for CI
- add noqa comments for UP040 ruff warning (TypeAlias for Python 3.10/3.11 compatibility)
- improve sys.path handling and add src package init
- resolve all remaining type checking errors
- update record preview after applying filter
- suppress warning for invalid filter fields during validation
- update filter display when test mode toggle is clicked
- add Google Sheets support to load_database_records()
- update record display when Apply Filter button is clicked
- handle Google Sheets profiles in filter validation
- ensure database path is set before filter validation
- **sonarqube**: refactor test_send_menu_and_dirty_flow to reduce duplication and line lengths
- resolve mypy type errors in test files
- exclude build artifacts and editor tests from pyright type checking

### Refactor

- reorganize tests into unit and integration directories

## v1.6.0 (2026-04-29)

### Feat

- **editor**: introduce Markdown fallback and enhance stylesheet loading
- **config**: add initial mailing list configurations for multiple accounts
- **editor**: add new Gmail API fields and improve profile handling
- **editor**: add PyInstaller spec for standalone WYSIWYG editor build
- **editor**: add settings dialog for managing sendMail YAML config profiles
- **editor**: add WYSIWYG newsletter editor with Quill.js

### Fix

- **sonarqube**: address critical security and code quality issues
- **editor**: preserve local anchor links

### Refactor

- **editor**: extract and modularize widget configuration and loading methods
- **editor**: centralize constants and improve maintainability

## v1.0.1 (2026-02-12)
