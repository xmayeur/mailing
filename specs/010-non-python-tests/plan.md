# Implementation Plan: Non-Python Test Coverage

**Branch**: `010-non-python-tests` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-non-python-tests/spec.md`

## Summary

Extend the existing pytest-based structural checks into a complete non-Python coverage suite. All checks land under `tests/unit/` as ordinary pytest tests, so every existing quality gate — the `.githooks/pre-commit` commit-time checks, `scripts/pre_push_checks.sh`, and the CI pytest jobs on the full 3-OS × 3-Python matrix — picks them up with no pipeline changes (FR-007). New modules: editor bundle consistency (asset references, bootstrap components, shipped-vendor script syntax), shell script syntax parsing plus static lint (via pip-installable `shellcheck-py`, satisfying FR-008 on all platforms), declarative config validation with duplicate-key strictness for every tracked YAML/JSON/TOML file, first-party stylesheet balance checks, and a self-audit check backed by a machine-readable coverage inventory that fails on any tracked non-Python asset belonging to no covered class and no documented exclusion (FR-012). Existing scripts flagged by the lint pass are remediated behavior-preservingly per the clarified scope.

## Technical Context

**Language/Version**: Python 3.12-3.14 (checks are pytest tests); assets under test are shell (bash), HTML + inline JS, CSS, YAML/JSON/TOML
**Primary Dependencies**: pytest 9 (existing runner), PyYAML (existing test dep), `bash` (syntax parse, all CI images ship it via Git), Node.js (existing `node --check` precedent, preinstalled on all GitHub-hosted runners), `shellcheck` via pip package `shellcheck-py` (new, `[dependency-groups] testing` — verified to ship prebuilt binaries for Linux/macOS/Windows), `tomllib` (stdlib)
**Storage**: N/A
**Testing**: pytest under `tests/unit/` — the only runner surface; inclusion in all gates is automatic
**Target Platform**: dev on macOS; CI on ubuntu-latest, macos-15, windows-latest (every check must execute on all three per FR-008)
**Project Type**: desktop application (PySide/PyQt email editor) plus repo automation
**Performance Goals**: added suite ≤ 30 s per gate (FR-010); expected well under 10 s — node startup × 3 assets, shellcheck × ~13 scripts, in-process parses for the rest
**Constraints**: no app-runtime behavior changes; the CI `--cov=src --cov-fail-under=80` gate is unaffected because new tests introduce no `src/` modules; line-ending safety on Windows checkpoints (normalize CRLF before `bash -n`); adding a dependency requires regenerating `poetry.lock` or the CI lockfile-check job fails
**Scale/Scope**: ~13 repo-authored shell scripts + `.githooks/pre-commit`; 1 editor bundle (3 local references, 1 QWebChannel object contract); ~15 tracked YAML/JSON/TOML config files (first-party and tool-installed); 1 first-party stylesheet; FR-012 self-audit over all tracked non-Python files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Status: **PASS (vacuously)** — `.specify/memory/constitution.md` is the unratified spec-kit template (all placeholders; no project-specific principles have been defined). Gates are therefore drawn from the template's example principles:

- Test-first: the feature is entirely tests and automation; the check suite is itself verified by a defect-injection trial (SC-002). Conforms.
- Simplicity / YAGNI: no new framework, no new CI job, no daemon; checks reuse the single existing runner surface. New dependency limited to one pip package (`shellcheck-py`) to satisfy a clarified scope decision. Conforms.
- Observability: gate outcomes are explicit — fail with file and reason, or skip with reason; never silent pass (FR-008). Conforms.

Recommendation (out of feature scope): ratify the project constitution separately so future features have real gates.

Post-Phase-1 re-check: **PASS** — the design changes no gate outcome semantics; it adds test modules, one pip dependency (`shellcheck-py`), and data files. No complexity violations to record.

## Project Structure

### Documentation (this feature)

```text
specs/010-non-python-tests/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (/speckit.specify output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── checklists/          # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

`contracts/` skipped: the feature is repo-internal test automation with no external interfaces (template guidance). The machine-readable coverage inventory schema it exposes internally is documented in `data-model.md`.

### Source Code (repository root)

```text
tests/
└── unit/
    ├── test_editor_assets.py         # EXTENDED: refs exist, bootstrap components, vendor JS syntax
    ├── test_shell_scripts.py          # NEW: bash -n (CRLF-safe) + shellcheck via shellcheck-py
    ├── test_declarative_configs.py    # NEW: YAML/JSON/TOML parse + duplicate top-level keys
    ├── test_stylesheets.py            # NEW: first-party CSS rule balance
    ├── test_coverage_inventory.py     # NEW: FR-012 self-audit over tracked non-Python files
    ├── coverage_inventory.json        # machine-readable inventory: classes + exclusions (FR-011/FR-012)
    ├── coverage_inventory.md          # FR-011 documentation: classes, defect classes, exclusions, extension guide
    └── support/
        └── repo_files.py              # git-ls-files helpers, strict YAML loader, CRLF-safe runner

pyproject.toml        # [dependency-groups] testing += "shellcheck-py"
poetry.lock           # regenerated (CI lockfile-check gate enforces sync)
scripts/*.sh          # remediation of shellcheck findings (behavior-preserving)
.githooks/pre-commit  # remediation if shellcheck flags it
src/editor_assets/    # untouched apart from defect-injection verification during development
```

**Structure Decision**: single-project layout; all checks are pytest unit tests because that one placement satisfies FR-007 (every existing gate already runs `pytest tests/unit`) and FR-008 (CI images provide the tools) without pipeline edits. Shared helpers coarse-located under `tests/unit/support/`; the inventory is data, not code, so the self-audit test and the documentation read the same object.

## Complexity Tracking

> Not used: no Constitution Check violations to justify.
