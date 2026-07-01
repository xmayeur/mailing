## v1.14.0 (2026-07-01)

### Feat

- cancel-in-progress sending, non-blocking send dialog, fix test crash

### Fix

- editor crash on startup and silent config-field data loss

## v1.13.2 (2026-06-23)

### Fix

- **editor**: replace hardcoded /tmp paths with cross-platform tempfile.gettempdir()

## v1.13.1 (2026-06-22)

### Fix

- **filter**: numeric field filtering and currency value parsing
- **readme**: use new-style workflow badge URL

## v1.13.0 (2026-06-13)

### Feat

- **editor**: display version number in status bar
- **editor**: Shift+Enter inserts soft line break inside table cells

### Fix

- **sendCambristi**: chmod 644 uploaded files so nginx can read them

## v1.12.0 (2026-06-13)

### Feat

- **editor**: apply heading styles inside table cells without splitting

### Fix

- **sendCambristi**: per-file CSS to avoid CSP and stylesheet collision
- **sendCambristi**: strip inline style block before scp, replace with css link

## v1.11.0 (2026-06-04)

### Feat

- **editor**: fix hyperlink menu, anchor id attr, add source view, live send log
- Automate builds on push to master with version-based releases
- Enable single-file executable for Windows/Linux in editor.spec

### Fix

- add PyQt6.QtWebEngineCore to test mocks; fix ruff/vulture/pymarkdown
- Exclude test files from SonarCloud coverage calculation
- Fix coverage.xml path and import order for SonarCloud
- Fix coverage.xml paths for SonarCloud source mapping
- Pin action SHAs and add missing coverage tests
- Resolve SonarCloud security hotspots and coverage path
- Remove sonar.sources=src to fix coverage path mismatch
- Bump build Python to 3.12 (type statement requires 3.12+, project requires >=3.12)
- Use PEP 695 'type' statement instead of TypeAlias (S6794, Python 3.12+)
- Point SonarCloud to coverage.xml for coverage reporting
- Add NOSONAR to last remaining S8544 pip install in main.yml
- Add NOSONAR to ssl.create_default_context line (S5527 reported there)
- Exclude editor_assets from SonarCloud; inline pinned pip versions in CI
- Add NOSONAR suppressions for remaining SonarCloud issues
- Use block scalar for pip install in main.yml (YAML colon in :all: broke syntax)
- Resolve remaining SonarCloud issues
- Rename sendMailEditor_bin to sendMailEditor before packaging
- Remove duplicate sonarcloud.properties (sonar-project.properties is canonical)
- Resolve SonarCloud issues across codebase
- Reduce SonarCloud issues
- Resolve ruff linting errors
- Resolve mypy strict type checking errors
- Update test assertions to match log.exception calls
- Remove unused exception variables in exception handlers
- Add SonarCloud exclusions and fix logging/SSL issues
- suppress spurious vault 404 error when no MAILCONFIG key configured
- **editor**: block target=_blank new windows; strip target from anchor links
- **editor**: expose handleLinkInsert globally; block link-click navigation
- Refactor high-complexity functions and address SSL security warning
- Address SonarCloud Python issues
- Correct PyInstaller asset paths for Linux/Windows onefile
- Include runtime deps in editor.spec onefile bundle for Windows/Linux
- Run unit tests only in coverage-badge job
- Exclude tests, docs, and scripts from CodeCov calculation
- Specify coverage.xml path in codecov action
- Exclude visual_filter_builder.py from CodeCov to align with local coverage
- Update workflow for single-file executables and improve stability

### Refactor

- Merge pre-commit check scripts into single scripts/pre-commit-checks.sh
- Reduce cognitive complexity in 5 functions for SonarQube

## v1.10.0 (2026-05-21)

### Feat

- **Phase 8**: Integration tests, documentation, and verification
- **US4**: Migrate debug log.info calls to log.debug
- Fix profile loading and configuration (008-fix-profile-loading)
- Complete Phase 9 — Multi-version Python testing (T071-T074)
- Phase 3 start - comprehensive email engine test suite (T019)
- Phase 2 partial - add type hints to critical sendMail functions
- implement Phase 1 test infrastructure and baseline
- add comprehensive testing & coverage improvement spec
- improve `Open File` dialog to respect profile-specific default paths
- raise test coverage from 61% to 81% with GUI and unit test expansion
- raise test coverage from 61% to 81% with GUI and unit test expansion
- raise test coverage from 61% to 81% with GUI and unit test expansion
- Complete 005-editor-profile-clipboard feature - all 4 user stories
- Implement profile selector and clipboard infrastructure (Phase 1-3 core)
- Allow comma-separated list values in filter editor (B054)
- implement T041-T042 - Error handling UI and validation
- integrate FilterBuilder with _SendDialog (T035-T038)
- implement responsive filter, dialog clarity, and template safety (US2-US5)
- implement persistent document folder for editor (US1)

### Fix

- Address flake8 code quality warnings
- Pin black version to 26.5.1 in CI workflow
- Add --target-version py312 to black in GitHub workflow
- Align GitHub workflow lint checks with local testing
- Apply noqa comments to ruff violations in editor.py and sendMail.py
- Use cast(Any) for ServiceAccountCredentials.from_json_keyfile_dict scopes
- Add version constraints to requirements.txt
- Add type: ignore for untyped google-auth library functions
- Remove unused type ignore comments
- Add type: ignore for untyped google-auth functions
- Resolve ruff linting issues
- Use cast() for untyped google-auth function
- Add auto-patch fixture for profile_manager.get_secret
- Remove unused type ignore comment
- Move mock setup to conftest.py and fix verbose logging level
- Add type casts for mypy --strict compatibility
- Downgrade SMTP TLS to 1.2 and disable strict cert verification for OVH
- Complete vault key parsing and SMTP field validation
- Load stylesheet from current profile, not hardcoded default
- Fix type narrowing for untyped yaml returns
- Add type:ignore[no-any-return] for yaml untyped returns
- Install project dependencies in lint CI job for proper mypy type checking
- correct mypy type ignore error codes and remove unused comments
- Use bare type:ignore comments for better cross-version compatibility
- Register Office file MIME types for Windows compatibility
- Resolve remaining mypy --strict type checking errors
- Mark untestable Qt dialog classes with pragma:no-cover
- Exclude visual_filter_builder.py from coverage (unit tests mock it)
- Mark visual_filter_builder.py with pragma:no-cover (unit tests mock it)
- Resolve all mypy/pyright type checking errors
- Correct return type annotation for setup_argparse
- Add type annotations to sendMail.py functions
- align type annotations with Python 3.13 + stubs environment
- resolve all 50 pre-existing mypy errors in src/
- clean up ruff warnings in test files
- Complete 006-send-dialog-improvements - all bugs resolved
- Revert async deferral, restore sync loading for Send dialog
- Use consistent config file path across all editor dialogs
- Pass selected profile to Settings/Config dialog
- Pass selected profile to Send mailing dialog
- Always update file dialog path when profile selected
- Handle empty string in default_documents_path from config
- _open_template() also uses profile's default_documents_path
- Use correct config key 'default_documents_path' in profile loader
- Profile selection file dialog opens to default_document_path (BF001)
- Add Excel file support to editor database loading
- Enable Excel file support in schema provider using calamine
- Prevent UI blocking during filter editing - defer record loading and add caching (B053)
- Suppress combo signals during schema refresh to prevent cascading loads (B052)
- Skip row_changed signal during schema refresh if no rows (B051)
- Use repaint() for immediate visual update of combos (B049)
- Force visual update of combo boxes when populated (B049)
- Preserve operator selection during schema refresh (B048)
- Case-insensitive config keys in load_database_records (B047)
- Handle both uppercase and lowercase config keys (B047)
- Improve Google Sheets schema loading diagnostics (B045)
- Center text vertically in QLineEdit value inputs (B044)
- Handle list values in FilterRow for multi-value operators
- Debug and resolve three critical filter widget bugs (B001-B003)
- use directory picker for default_documents_path config field
- force light palette for all UI elements
- use Fusion style for light mode UI in all dialogs
- force light mode in macOS app - disable dark theme support
- PyInstaller bundle - fix module imports and log file paths

### Refactor

- Use system defaults for fallback paths instead of hardcoded 'data'
- reorder imports in sendMail.py for readability and consistency

### Perf

- Defer expensive database operations during Send dialog init
- Add timing measurements for schema and record loading (B050)

## v1.9.0 (2026-05-17)

### Feat

- add support for string filter operations (contains, starts with, matches)

### Fix

- use correct type: ignore syntax for mypy
- resolve SonarQube issues
- handle None filter values to eliminate repetitive NoneType error
- suppress logging during filter editing in editor
- integrate SchemaCacheProvider into editor to prevent Google Sheets quota hits

## v1.8.0 (2026-05-17)

### Feat

- complete filter editor and schema caching features

### Fix

- update integration test expectations for improved error messages
- reorder imports in test_sendMail.py to resolve style issue
- reorganize CHANGELOG to put v1.7.0 at top
- add requests to docs build requirements
- normalize CHANGELOG whitespace

### Refactor

- use log.debug for filter operation errors and fix yaml module pollution

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
