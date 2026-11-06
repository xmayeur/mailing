# Quickstart: Non-Python Test Coverage

**Branch**: `010-non-python-tests` | **Date**: 2026-11-06

How to run the coverage checks, read their outcomes, extend coverage, and verify the runtime budget.

## Run the checks

```bash
# Everything (this is exactly what every gate runs — pre-commit, pre-push, CI):
poetry run pytest tests/unit -q

# Targeted runs during development:
poetry run pytest tests/unit/test_editor_assets.py -q          # editor bundle consistency
poetry run pytest tests/unit/test_shell_scripts.py -q          # bash -n + shellcheck
poetry run pytest tests/unit/test_declarative_configs.py -q     # YAML/JSON/TOML strict parse
poetry run pytest tests/unit/test_stylesheets.py -q             # first-party CSS balance
poetry run pytest tests/unit/test_coverage_inventory.py -q      # FR-012 self-audit
```

No flags, env vars, or installation steps beyond the existing dev setup (`poetry install --with testing`), which now also provides the `shellcheck` binary via `shellcheck-py`.

## Reading outcomes

- **Failure**: names the offending file plus an actionable reason (e.g., `scripts/sign_app.sh: line 42: syntax error near unexpected token` or `.codecov.yml: duplicate top-level key 'coverage'`). Fix the asset, rerun.
- **Skip (expected only without support tools locally)**: reported as `SKIPPED (reason)` — e.g., `bash not found`, `node is not installed`, `shellcheck is not installed`. Skips are visible, never silent passes. On CI (all three operating systems) none of these tools is absent, so nothing skips there.
- **Clean tree**: all modules pass. The self-audit (`test_coverage_inventory.py`) passing means every tracked non-Python file is either covered or deliberately excluded in `coverage_inventory.json`.

## Extend coverage to a new asset class

1. Decide cover-or-exclude; record the decision:
   - Cover: add a `classes` entry to `tests/unit/coverage_inventory.json` — `id`, `description`, `patterns` (globs), `defect_classes`, `owning_test`.
   - Exclude: add an `exclusions` entry — `pattern`, `family`, `reason` (one line, so the decision history stays legible).
2. Implement or map the owning check. Typically: a defect class that reduces to "strict parse" maps onto `test_declarative_configs.py` mechanisms; anything else gets a new module. Keep the message contract: file + reason.
3. Document it in `tests/unit/coverage_inventory.md` (the FR-011 doc, generated from and kept in sync with the JSON).
4. The self-audit enforces all of this on the next run — an undeclared asset class fails the gate naming the file.

## Runtime budget verification (FR-010 / SC-004)

```bash
# on the same machine, before and after the feature:
poetry run pytest tests/unit -q --durations=10
```

Record both durations in the feature's completion notes; the added suite must stay within +30 s (expected: single-digit seconds).

## CI matrix expectations

The checks run inside the existing `Tests` workflow steps — no workflow edits. Every check executes on ubuntu-latest, macos-15, and windows-latest (properties FR-008): `bash` exists on all images (Git for Windows on Windows), `node` is preinstalled, and `shellcheck` arrives through the Python environment. Windows checkouts are CRLF-safe by design: the shell syntax check normalizes line endings before parsing, validating committed content rather than the local checkout mode.

## Defect-injection trial (SC-002 verification, post-implementation)

**Recorded verification evidence (T016-T018)**

- Commit gate: a seeded shell-syntax defect fails the exact commit-time pytest step (`pre-commit-checks.sh` → `pytest tests/unit/ -q --cov=src`) naming `scripts/build_doc.sh`; full commit-gate runs with the new checks active passed on a clean tree (41+ gate runs this development session).
- Pre-push: the same seed fails the pre-push pytest step (`pytest tests/unit --cov-fail-under=60 --cov=src`) naming the file; the integration suite runs green locally (36 passed), and the Python coverage ratio is unchanged at 91% (the new tests contribute no `src/` modules).
- CI: no workflow edits required — the new modules run inside the existing pytest steps (`Tests` matrix, Sonar, and badge jobs all run `tests/unit`). All three OS images preinstall node and bash; `shellcheck` ships through the exported testing requirements (`shellcheck-py` bundles per-platform shells, including `shellcheck.exe`). Matrix-run evidence will be captured from the first CI run of this branch's PR to master.

**Runtime budget (FR-010 / SC-004, T028)**

- Baseline (pre-feature, with coverage instrumentation): 438 passed in ~2.2s.
- After (with coverage instrumentation, across 41+ commit-gate runs): 475 passed in ~3.2-3.5s — delta ≈ +1.1s, well within the 30-second budget. Slowest added checks: shellcheck sweep 0.18s, vendor JS node parse 0.14s, bash -n sweep 0.14s.

**Full defect-injection trial (SC-002, T029) — 10/10 caught**

| # | Seed | Result |
|---|------|--------|
| 1 | Missing editor reference (`quill.snow.css` renamed to a nonexistent file) | Caught — names editor.html and the missing asset |
| 2 | Removed bootstrap component (`#editor-container` renamed) | Caught — names editor.html and the component |
| 3 | Broken inline JS (stray paren in the inline script) | Caught — names inline `<script>` block |
| 4 | Corrupted shipped-vendor script (truncated `quill.js`) | Caught — names src/editor_assets/quill.js |
| 5 | Shell syntax error (unterminated `if`) | Caught — names scripts/build_doc.sh (bash -n) |
| 6 | Unquoted expansion (`ls ${HOME}`) | Caught — SC2086 named |
| 7 | Unset variable (lowercase `$definitely_unset_var_xyz`) | Caught — SC2154 named |
| 8 | Masked command failure (`export VAR=$(false)`) | Caught — masked-exit class named |
| 9 | Unparseable config (tab-indented YAML `.codecov.yml`) | Caught — names .codecov.yml |
| 10a | Duplicate top-level config key (second `coverage:` block) | Caught — duplicate mapping key 'coverage' named |
| 10b | Unbalanced stylesheet (removed closing brace) | Caught — names css/styles.css with line and depth |

Plus the false-positive guard: a `content: "}"` rule appended to `css/styles.css` still passes. Every seeded defect failed naming the file; each injection was restored, tree verified clean afterwards.

**SC-003 gate-surface evidence (T030)**

- Seeded defects fail the commit-gate and pre-push pytest steps (see above); every one of the feature's commits was itself gated by the full commit-time suite (pymarkdown, black, ruff, vulture, pyright, mypy, pytest) with the new checks active — 41+ full gate runs green on the clean tree.
- CI matrix evidence is pending the branch's first PR run against master; all static prerequisites verified (see T018 record).

**Windows matrix findings (PR rounds 1-3)**

- Round 1: `which("bash")` on windows runners resolves to the System32 WSL stub ("WSL has no installed distributions", exit 1) — fixed by probe-resolving bash and falling back to Git for Windows bash (fafe9ff0).
- Round 2: shellcheck ran (absolutized path) but read the CRLF-converted on-disk files, flagging SC1017 literal-carriage-return on every line; the bash stdin pipe also tripped cp1252 on scripts' check-mark characters. Both fixed by linting the committed LF content through stdin with UTF-8 encoding — validated locally by converting a script to CRLF on disk and confirming both checks stay green.
- Takeaway recorded for the extension recipe: shell-class checks must always validate normalized committed content, never the local checkout mode.

Seed one defect per class (each in a scratch checkout, each expected to fail the suite with file-naming messages): missing editor reference (delete `quill.js`), removed bootstrap component (delete `#editor-container`), broken inline JS (delete a brace in the inline script), shell syntax error (stray `)` in a script), unquoted expansion (add unquoted `$1` usage), unset variable use (reference an undefined lowercase `$unset_var` with no default — all-caps names read as environment-provided and shellcheck suppresses SC2154 for them), masked command failure (a nonzero-exit command swallowed in a pipeline or unchecked fallback — construct per shellcheck's masked-exit class), unparseable config (tab-indent a YAML mapping), duplicate config key (paste an existing top-level key), unbalanced stylesheet (delete a closing brace). All ten must be caught — this trial doubles as the acceptance test for the user stories in `spec.md`.
