# Research: Non-Python Test Coverage

**Branch**: `010-non-python-tests` | **Date**: 2026-11-06
Phase 0 output: decisions resolving all Technical Context unknowns. Each entry records Decision / Rationale / Alternatives considered.

## R-01: Where the checks live and how they enter automation

- **Decision**: All new checks are pytest test modules under `tests/unit/` (extending the precedent of `tests/unit/test_editor_assets.py`). No pipeline files change for inclusion.
- **Rationale**: FR-007 requires inclusion in every existing gate with zero extra invocation. The commit-time gate `.githooks/pre-commit` → `scripts/pre-commit-checks.sh` runs `poetry run pytest tests/unit/`; `scripts/pre_push_checks.sh` re-runs it; the CI test job runs `pytest tests/unit` on the full 3-OS × 3-Python matrix; sonar and coverage-badge jobs run the same. One placement covers every surface in FR-007, including the Windows runner.
- **Alternatives**: pre-commit-framework hooks in `.pre-commit-config.yaml` (rejected: adds a second enforcement point with different tool availability semantics and does not run in the CI test job); a dedicated CI lint job step (rejected: coverage outside `tests/unit` would not hit the commit/push gates — violates FR-007); a Makefile/manual target (rejected: manual invocation is exactly what the spec forbids for inclusion).

## R-02: How assets are enumerated ("tracked" semantics)

- **Decision**: File discovery uses `git ls-files` from the repo root, with glob-pattern matching per class, in a shared helper (`tests/unit/support/repo_files.py`).
- **Rationale**: The spec scope is *tracked* files (FR-001(d), Clarifications). `git ls-files` equals that set exactly, automatically excludes untracked noise (`dist_nuitka/`, stray certs), and is available everywhere the gates run (clone-based CI, local repos). 
- **Alternatives**: filesystem walk (rejected: cannot distinguish tracked from untracked, so local build output and untracked experiments would trigger false gate failures); pre-commit's own file discovery (rejected: only valid inside that framework).

## R-03: Shellcheck provisioning across the 3-OS CI matrix

- **Decision**: `shellcheck` is provided by the pip package `shellcheck-py`, added to `[dependency-groups] testing` (which CI already installs via `poetry export --with testing`); `poetry.lock` regenerated in the same change (lockfile-check job enforces sync).
- **Rationale**: The clarified scope (all-platforms) requires the analyzer on ubuntu/macos *and* windows runners with zero CI configuration (spec assumption: skip-safe locally, zero-config in CI). Verified on PyPI/GitHub: the package "provides a convenient way to download the pre-built shellcheck binary for your particular platform" and "the shellcheck binary should be available in your environment (or shellcheck.exe on windows)". CI images (Ubuntu 22.04/24.04, macOS, Windows Server) all supported. Locally without the package, the lint check skips with an explicit reason (FR-008 semantics per FR-004) while `bash -n` still runs.
- **Alternatives**: runner-image shells of apt/brew/choco installs in `tests.yml` (rejected: per-OS pipeline edits contradict FR-007's zero-config intent and drift from local dev); relying on preinstalled image tools (rejected: shells/shellcheck presence varies by OS image and none is guaranteed on Windows — would violate FR-008); dropping the lint pass (rejected: clarification decision B requires it).

## R-04: Shell syntax checking that survives Windows CRLF checkouts

- **Decision**: Shell scripts are read as UTF-8 text in Python, line endings normalized (`\r\n` → `\n`), then fed to `bash -n` via stdin (`subprocess.run(["bash", "-n"], input=normalized)`). `shutil.which("bash")` guard skips with reason when no shell exists (locally only; CI images all ship bash — Windows via Git for Windows).
- **Rationale**: GitHub Windows runners may check out LF-committed scripts with CRLF endings (autocrlf), and `bash -n` on CRLF text reports spurious syntax errors — a guaranteed false-failure matrix leg. Normalizing validates the committed content, not the local checkout mode, and makes the check portable across all three CI operating systems (FR-008).
- **Alternatives**: running `bash -n` directly on files (rejected: the CRLF failure mode above); skipping on Windows (rejected: violates the all-platforms clarification; also loses representation of half the matrix); `sh -n` (rejected: scripts are bash — gate/backtick/bashism parsing differs and would reject valid constructs).

## R-05: YAML validation with duplicate-key strictness

- **Decision**: A strict `yaml.SafeLoader` subclass that raises on duplicate mapping keys (standard `construct_mapping` override checking `Loader.construct_mapping` key duplicates at any level), used to parse every covered YAML file. Parse errors and duplicate-key errors both fail naming file and key.
- **Rationale**: FR-005 requires detecting unparseable content and ambiguous duplicate top-level entries. `yaml.safe_load` silently accepts duplicate keys (last-wins), which is precisely the silent-override defect US-4 targets. The subclass is ~10 lines, dependency-free (PyYAML is already a test dependency and typed via `types-pyyaml`).
- **Alternatives**: `yamllint` (rejected: adds a dependency and a style-rule surface that the spec's false-positive edge case forbids — styling flags are out of scope); plain `safe_load` (rejected: misses the defect class FR-005 names).

## R-06: JSON and TOML validation

- **Decision**: JSON parsed with `json.loads` using an `object_pairs_hook` that raises on duplicate keys. TOML parsed with stdlib `tomllib` (Python ≥3.11; repo floor is 3.12), which rejects duplicate keys natively.
- **Rationale**: Same FR-005 rationale as R-05 with stdlib-only tooling; duplicate JSON keys are the classic silent-override defect (config merging, tool-generated files).
- **Alternatives**: third-party validators (`jsonschema`, `toml`) (rejected: no schema exists to validate against; `toml` package is deprecated and less strict than `tomllib`).

## R-07: Stylesheet balance checking without false positives

- **Decision**: A small tokenizer walks first-party CSS: strips `/*...*/` comments, string literals (`"..."`/`'...'`), and url tokens, then asserts `{`/`}` balance and that rule-introducing braces are properly opened/closed. Applied to `css/styles.css` (first-party per FR-006).
- **Rationale**: FR-006 requires detecting unbalanced/truncated rules *without false positives on current assets*; the edge-case section calls out braces-in-content (`content: "}"`) exactly. A tokenizer that respects strings/comments handles that; a raw brace count does not.
- **Alternatives**: raw brace counting (rejected: false positive on `content` strings); tinycss2 dependency (rejected: unnecessary; format-linting via a full parser exceeds the defect class).

## R-08: Editor bundle consistency checks (grounded in current `editor.html`)

- **Decision**: Extend `tests/unit/test_editor_assets.py` with: (1) every local reference in the markup resolves — current set discovered by research: `quill.snow.css`, `qwebchannel.js`, `quill.js` (relative refs → must exist in `src/editor_assets/`); (2) bootstrap components present — `#editor-container`, `#toolbar`, exactly one `new QWebChannel(qt.webChannelTransport...)` and one `new Quill(...)`; (3) host↔editor object-name contract — the object registered by `src/editor.py:2965` (`self._channel.registerObject("bridge", ...)`) must appear as `channel.objects.bridge` in the inline JS; (4) shipped-vendor scripts (`quill.js`, `qwebchannel.js`) parse via the existing `node --check` path alongside the inline block.
- **Rationale**: FR-003 validation exists. The reference and object-name contracts catch the two defect classes that have actually required post-hoc fixes in this repo (broken editor bootstrap after markup surgery); vendor parse catches corrupted vendored files, which FR-001(a) includes, without style-linting vendor code.
- **Alternatives**: full DOM parse with html.parser for references (deferred: regex on `<script src=`/`<link href=` matches the file's actual simple structure; revisit if markup gains templating); headless-editor end-to-end assertions (already covered by `tests/integration/test_editor_filter.py` — out of the structural scope).

## R-09: Coverage inventory format and self-audit design (FR-011/FR-012)

- **Decision**: A machine-readable `tests/unit/coverage_inventory.json` with two lists: covered classes (id, description, match patterns, defect classes checked, owning test module) and exclusions (pattern, family, reason). The self-audit test (`test_coverage_inventory.py`) walks every tracked non-Python file; each file must match ≥1 class or ≥1 exclusion, otherwise it fails naming the file — the "cover-or-exclude" decision mandated by the drift-alarm clarification. `coverage_inventory.md` (FR-011) documents classes, defect classes, exclusions, and the extension recipe, reading the same inventory.
- **Rationale**: The clarification chose the registry + alarm model. JSON is validated by the suite itself (strict loader from R-06), is diff-reviewable, and keeps documentation and enforcement against the same object — documentation cannot drift from enforcement.
- **Alternatives**: YAML registry (rejected: same content, but duplicated-key pitfalls in the very file that guards duplicates; JSON + strict hook is cleaner); pure-document inventory with glob logic hardcoded in tests (rejected: drift between doc and code is exactly what FR-011/FR-012 separates); failing the audit only on new extensions (rejected: "unsupported extension" is the drift signal; extensions are the top new-class vector).

## R-10: The exclusion set (initial inventory contents)

- **Decision**: Initial `exclusions` (deliberate, each with reason):
  - FR-009 scope: `release/**`, `dist_nuitka/**` — release bundles, build outputs, third-party framework trees.
  - Documentation/data: `*.md`, `*.rst`, `*.txt`, `docs/**`, `data/**` — prose and fixtures, not machine-read code.
  - Binary/media: `*.png/vnd.*`, `*.icns`, `*.ico`, `*.psd`, `*.jpeg`, `*.webp`, `*.zip`, certs/keys (`*.p12`, `*.der`, `*.crt`, `*.key`), `*.dylib`, fonts.
  - XML family: `**/*.xml`, `**/*.metainfo`, `**/*.plist` — current XML is IDE metadata (`.idea/`), Qt scan artifacts (`.sonar/`), app bundle resources: deliberately uncovered until an XML checker is wanted; recorded so the alarm fires if XML starts appearing in first-party source paths.
  - XML-ish/graph formats: `**/*.puml`, `**/*.udg`, `**/*.ir`, `**/*.ucfg` — diagrams and scanner artifacts.
  - `.specify/**` scripts and `*.ps1` — tool-installed framework code, not repo-authored automation scripts.
  - `Makefile`, `*.bat` — build entry glue; covered classes are POSIX scripts (record and revisit if Windows build scripts multiply).
  - Extensionless dotfiles (`.gitignore`, `.claudeignore`, `.pre-commit-config.yaml` is YAML-covered, `.githooks/pre-commit` *is* covered as a script).
- **Rationale**: Edge case "new asset class appears": the alarm must fire only on genuinely unclassified files; a curated exclusion list with reasons is the documented cover-or-exclude ledger. Binaries and vendored trees must never be parsed (FR-009, runtime budget).
- **Alternatives**: allowlisting only covered files (rejected: inverts the model — a new script folder then lands in "excluded-by-default"; the alarm must catch *additions*, so classes are matched by pattern and exclusions are explicit); no initial exclusions (rejected: the alarm would immediately fail on the 13 k-file release bundle).

## R-11: Remediation policy for lint findings

- **Decision**: Run shellcheck (once provisioned) across the ~13 scripts + `.githooks/pre-commit` first to get a baseline; fix findings behavior-preservingly (quote fixes, `--` guards, explicit error handling), one script per commit grouped by finding type, with the defect-injection trial (SC-002) verifying the checks after remediation.
- **Rationale**: Clarification decision B put remediation in scope; the spec constrains fixes to "what the analysis flags" and forbids behavior changes. Sequencing remediation before activating the checks keeps every commit green (CI is the arbiter once tests land).
- **Alternatives**: landing checks with `shellcheck` suppressed per-finding, remediate later (rejected: violates FR-004-in-CI — checks must be active and passing to gate; suppression inventory is exactly the failure mode FR-012 exists to prevent earlier); rewrite scripts wholesale (rejected: behavior constraint).

## R-12: Runtime budget measurement

- **Decision**: Measure with `pytest tests/unit -q --durations=10` before and after the change on the same machine; record both numbers in `quickstart.md`. Expectation: subprocess-dominated cost (node × 3 invocations, shellcheck × ~13, bash ~14) ≪ FR-010's 30 s.
- **Rationale**: SC-004 verifiability needs a stated method; `--durations` is built into the existing runner.
- **Alternatives**: CI timing extraction (rejected: noisy, matrix-variance obscures the delta); no measurement (rejected: SC-004 must be verifiable).

## R-13: Need for external research agents

- **Decision**: None. All unknowns resolved by direct repository research (editor markup structure, Python↔JS bridge contract, dependency groups, hook activation, config census) plus one external verification (shellcheck-py platform coverage, R-03).
- **Rationale**: The feature operates entirely within known repo boundaries; no architecture, dataset, or external API unknowns remain.
