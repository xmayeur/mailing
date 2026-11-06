# Non-Python Coverage Inventory

**Source of truth**: [`coverage_inventory.json`](coverage_inventory.json) — this
document is its human-readable companion (spec FR-011). The self-audit
([`test_coverage_inventory.py`](test_coverage_inventory.py), FR-012) enforces
that every tracked non-Python file matches a covered class or a documented
exclusion below; an unclassified file fails the gate naming the file.

## Covered classes

| Class | Patterns (fnmatch, `*` spans directories) | Defect classes checked | Owning test |
|---|---|---|---|
| editor-markup | `src/editor_assets/editor.html` | missing-reference, missing-bootstrap-component, invalid-inline-javascript, bridge-object-mismatch, unsafe-paste-attributes | `test_editor_assets.py` |
| shipped-vendor-js | `src/editor_assets/*.js` | syntax-corruption (parse-level only, never style-linted) | `test_editor_assets.py` |
| shipped-vendor-css | `src/editor_assets/*.css` | missing-reference (existence via markup references only, no balance lint) | `test_editor_assets.py` |
| first-party-css | `css/*.css` | unbalanced-rule, truncated-file | `test_stylesheets.py` |
| automation-scripts | `scripts/*.sh`, `.githooks/pre-commit`, `sendCambristi` | syntax-error, lint-unquoted-expansion, lint-unset-variable, lint-masked-command-failure | `test_shell_scripts.py` |
| declarative-configs | `*.yml`, `*.yaml`, `*.json`, `*.toml`, `poetry.lock` | unparseable-content, duplicate-key (any level) | `test_declarative_configs.py` |

Enumeration is `git ls-files` based: only *tracked* files are validated, which
keeps the spec's scope (untracked build output and local experiments never
fail gates).

## Documented exclusions

| Pattern | Family | Reason |
|---|---|---|
| `release/*` | release-bundle | Signed app bundle and vendored frameworks; FR-009 excludes release trees |
| `dist_nuitka/*` | build-output | Nuitka build output (also gitignored) |
| `*.md`, `*.rst`, `*.txt`, `docs/*` | documentation | Prose, notes, docs subtrees |
| `data/*` | fixtures | Input fixtures |
| `*.png`, `*.icns`, `*.ico`, `*.psd`, `*.jpeg`, `*.webp` | binary-media | Binary images |
| `*.zip` | binary-archive | Binary archive |
| `*.dylib` | binary-library | Binary shared library |
| `*.xml`, `*.plist`, `*.metainfo`, `*.entitlements`, `*.ui`, `*.qrc` | xml | XML family deliberately uncovered until an XML checker is adopted |
| `*.puml` | diagram | Diagram-as-code; no adopted checker yet |
| `.sonar/*` | scanner-artifacts | SonarCloud scanner working artifacts |
| `.junie/*` | agent-memory | Tool-maintained agent memory |
| `.idea/*` | ide-metadata | JetBrains project metadata |
| `*.DS_Store` | finder-metadata | macOS Finder metadata binary |
| `.specify/scripts/*`, `.specify/extensions/*/scripts/*`, `.specify/integrations/*/scripts/*` | tool-installed-code | Spec Kit installed shell framework; not repo-authored |
| `.specify/extensions/.registry` | tool-installed | Spec Kit extension registry data |
| `*.ps1` | powershell | Windows entry scripts; the shell class is POSIX-only |
| `.gitignore`, `.claudeignore` | tool-dotfile | Line-oriented tool configs, not structured formats |
| `sonar-project.properties`, `*.properties` | line-oriented-config | Java-style properties files; outside the YAML/JSON/TOML scope |
| `LICENSE` | documentation | License text |
| `editor.spec` | python-artifact | PyInstaller spec is Python code; the Python gates own it |
| `wget-log` | local-tool-output | Accidental wget log at repo root; not source |

## Skip semantics (FR-008)

When a support tool is unavailable in an environment (`bash`, `node`,
`shellcheck`), the check that needs it reports `SKIPPED` with the reason — it
never reports a silent pass. Hosted CI provides every tool on every operating
system in the matrix, so nothing skips there.

## Extending coverage

1. **Cover a new asset class**: add a `classes` entry to
   `coverage_inventory.json` (`id`, `description`, `patterns`, `defect_classes`,
   `owning_test`), implement or map the owning check (a defect class that reduces
   to a strict parse maps onto `tests/unit/test_stylesheets.py`-style modules),
   and add the row here. The owning test must exist (the audit enforces it once
   all modules land).
2. **Exclude a family**: add an `exclusions` entry (`pattern`, `family`,
   `reason`) — one line of reason, so the decision history stays legible — and
   add the row here.
3. The self-audit enforces both: an unclassified tracked non-Python file fails
   `test_coverage_inventory.py` naming the file until you decide cover-or-exclude.
