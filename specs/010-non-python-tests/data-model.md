# Data Model: Non-Python Test Coverage

**Branch**: `010-non-python-tests` | **Date**: 2026-11-06

Entities the feature introduces or operates on. This feature manifests entirely as test-time data and checks — there is no runtime schema, no persistent storage, and no external interface (contracts/ skipped per plan). The **Coverage Inventory** is the one machine-readable artifact with a schema, defined here.

## Coverage Inventory (`tests/unit/coverage_inventory.json`)

The registry both the documentation (FR-011) and the self-audit check (FR-012) consume.

**Fields**:

```text
coverage_inventory
├── version: string ("1")
├── classes: [class]
│   ├── id: string                 # "shell-scripts", "declarative-configs", ...
│   ├── description: string        # human-readable class scope
│   ├── patterns: [string]         # git-ls-files-scoped globs, repo-root-relative
│   ├── defect_classes: [string]   # what the owning check detects
│   └── owning_test: string        # test module path, e.g. "tests/unit/test_shell_scripts.py"
└── exclusions: [exclusion]
    ├── pattern: string            # glob, repo-root-relative
    ├── family: string             # "release", "binary", "documentation", ...
    └── reason: string             # deliberate decision record
```

**Validation rules** (enforced by `test_coverage_inventory.py`):

- The JSON must parse with the strict loader (no duplicate keys).
- `patterns` must be non-empty; `owning_test` must reference an existing file.
- Every tracked non-Python file must match ≥1 class or ≥1 exclusion — otherwise failure naming the file (FR-012).
- Mirror classes exist for each spec class: shells and hook, editor bundle, configs, first-party CSS, vendor scripts.

**Initial class instances** (pattern → files, from research):

| id | patterns (summary) | defect classes | owning test |
|---|---|---|---|
| editor-markup | `src/editor_assets/editor.html` | missing refs, missing bootstrap components, invalid inline JS, bridge object mismatch | `test_editor_assets.py` |
| shipped-vendor-js | `src/editor_assets/*.js` | syntax corruption | `test_editor_assets.py` |
| first-party-css | `css/**/*.css` | unbalanced/truncated rules | `test_stylesheets.py` |
| automation-scripts | `scripts/*.sh`, `.githooks/pre-commit` | syntax errors, lint-scriptable defects | `test_shell_scripts.py` |
| declarative-configs | `*.yml`, `*.yaml`, `*.json`, `*.toml` (tracked, outside FR-009 trees) | unparseable content, duplicate keys | `test_declarative_configs.py` |

## Asset classes (spec FR-001 ↔ inventory)

- **Editor asset bundle**: markup file + its local references (`quill.snow.css`, `quill.js`, `qwebchannel.js`, relative to `src/editor_assets/`), bootstrap components (`#editor-container`, `#toolbar`, single `new QWebChannel(qt.webChannelTransport...)`, single `new Quill(...)`), and the host-side object registration (`registerObject("bridge", ...)` at `src/editor.py:2965`) paired with `channel.objects.bridge` in the markup. Validation: references exist; components present exactly once; object names match across the host/markup boundary.
- **Automation script**: repo-authored shell scripts — `scripts/*.sh` (13), `.githooks/pre-commit` — including the gate scripts that enforce the suite themselves. Validation: parses under `bash -n` on normalized line endings; shellcheck-clean after remediation.
- **Declarative configuration**: every tracked YAML/JSON/TOML file (~15 first pass: `.codecov.yml`, `.github/build.yml`, `.github/dependabot.yml`, `.github/workflows/*.yml`, `.pre-commit-config.yaml`, `.readthedocs.yaml`, `poetry.toml`, `pyproject.toml`, `pyrightconfig.json`, `src/config.yml`, `.specify/extensions.yml`, `.specify/extensions/git/git-config.yml`, `.specify/init-options.json`, `.specify/integration.json`). Validation: strict parse (no duplicate keys), errors name file + entry.
- **Shipped-vendor asset**: `quill.js`, `qwebchannel.js`, `quill.snow.css` — third-party files loaded from local storage. JS validated at parse level only; CSS at existence level only (FR-006 bounds balance checks to first-party CSS).

## Check

- **Fields**: id; asset class; defect class; implementation (in-process parse or subprocess tool); skip condition (tool absent); message contract ("file + reason").
- **Validation rules**: a check may report pass, fail, or skip-with-reason — never pass under skip (FR-008); every failure names the offending file and an actionable reason (FR-002); subprocess runs carry timeouts so a hung tool cannot hang a gate.
- **Relationships**: a Check consumes one inventory class; Quality gates run every Check.

## Quality gate

- **Fields**: name (commit-time checks, pre-push checks, CI test matrix — 3 OS × 3 Pythons —, sonar job, badge job); runner (`pytest tests/unit`); outcome (pass/fail/skip-visible).
- **Validation rules**: all checks execute on every gate unchanged (FR-007); on CI, no required check skips, on any OS (FR-008); Python coverage ratio unaffected (new tests contribute no `src/` modules — the `--cov=src` denominator is unchanged).
- **Relationships**: gates host all Checks; the CI lockfile gate additionally enforces `poetry.lock` sync when the `shellcheck-py` dependency lands (see research R-03).

## State transitions

Gate outcomes only: `pass → fail (defect found)` on defect introduction; `fail → pass` on fix; `pass → skip-with-reason (tool absent)` only in local environments lacking a support tool (never on CI). Coverage state: `covered | excluded-by-decision`, with the self-audit as the transition guard — a file arriving in neither state is an explicit defect of the inventory.
