# Feature Specification: Non-Python Test Coverage

**Feature Branch**: `010-non-python-tests`
**Created**: 2026-11-06
**Status**: Draft
**Input**: User description: "write additional tests for non-python code and include them in automation"

## Clarifications

### Session 2026-11-06

- Q: Which declarative configuration files must the checks cover? → A: All YAML/JSON/TOML files tracked in the repository regardless of purpose — CI/build/quality/docs configs as well as IDE metadata and tool-installed configuration (all-files option). FR-009 exclusions (release bundles, build outputs, dependency folders, third-party framework trees) still apply.
- Q: How should coverage completeness be enforced over time as new non-Python assets appear? → A: Maintain a machine-readable coverage inventory (covered classes plus exclusions) and a self-audit check that fails when a tracked non-Python file belongs to no covered class and no documented exclusion (self-audit alarm option), so coverage never decays silently.
- Q: How deep should shell script checks go? → A: Syntax-level plus a static-analysis lint pass (syntax + lint option); latent defects flagged in existing scripts are fixed as part of this feature, and environments without the analyzer fall back to FR-008 skip semantics for the lint portion.
- Q: Must every check run on every CI platform job? → A: Yes — every check must execute on all three CI operating systems in the matrix (all-platforms option); OS specifics such as shell availability and line-ending conversions are resolved during planning so no matrix leg skips.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Broken editor markup caught before it ships (Priority: P1)

As a developer changing the editor's embedded markup or scripting, when I introduce a defect — a reference to a missing asset, a removed structural component, or malformed script code — an automated check fails during my normal commit, push, or CI flow and tells me which file failed and why. I no longer discover a broken editor only when the app starts.

**Why this priority**: the editor asset bundle is under active development, existing Python-focused quality gates ignore it, and defects in this area are the ones the project has fixed after the fact most recently. Extending the existing checks from pure script syntax to full bundle consistency closes the biggest current gap.

**Independent Test**: Temporarily break one editor asset reference, run the automated suite, and observe a failure naming the file and the problem. Restore the asset and observe a pass.

**Acceptance Scenarios**:

1. **Given** editor markup references a script or stylesheet asset that does not exist in the location it is loaded from, **When** the automated suite runs, **Then** it fails and names the file and the missing reference.
2. **Given** editor markup is missing a structural component required for the editor to bootstrap, **When** the automated suite runs, **Then** it fails and identifies the missing component.
3. **Given** the editor markup, its references, and all shipped script assets are valid, **When** the automated suite runs, **Then** the editor checks pass.

---

### User Story 2 - Shell script defects caught automatically (Priority: P1)

As a developer editing any repo-authored shell script — build, signing, release wrapping, documentation, or the quality-gate scripts and local hook themselves — a syntax error, an invalid construct, or a latent static-analysis defect (such as an unquoted expansion or unset variable use) is caught by an automated check when I commit or push, on every platform where the automation runs.

**Why this priority**: these scripts package and release the app and enforce the project's quality flow. Nothing currently reads them; a broken script typically surfaces at release time under pressure. A static-analysis pass also catches the quieter defect classes that still bite at release time, provided the findings it surfaces in existing scripts are fixed.

**Independent Test**: Introduce a single-character syntax error into any one repo-authored script, run the suite, and observe a failure naming that file and the error.

**Acceptance Scenarios**:

1. **Given** a syntax error exists in any repo-authored shell script (including the local git hook entry), **When** the automated suite runs, **Then** at least one check fails and identifies the offending file.
2. **Given** all repo-authored shell scripts are syntactically valid, **When** the automated suite runs, **Then** the shell checks pass on every platform where the automation runs.
3. **Given** a repo-authored shell script contains a defect class static analysis flags (e.g., an unquoted expansion), **When** the automated suite runs, **Then** a check fails and identifies the file and the finding.

---

### User Story 3 - New checks everywhere, zero manual steps (Priority: P1)

As a contributor, I never invoke the new checks manually: they run as part of every existing quality gate — the commit-time checks, the pre-push checks, and the hosted CI test suite — exactly like the rest of the suite. Whatever gates I already run, I get non-Python validation with them.

**Why this priority**: this is the "include them in automation" half of the request. Checks that only a power user remembers to run do not protect the codebase.

**Independent Test**: Pick each gate surface, break a covered asset, and confirm that gate fails without any extra invocation or setup.

**Acceptance Scenarios**:

1. **Given** a defect is present in any covered non-Python asset, **When** the contributor runs only the existing commit-time checks, **Then** those checks fail, identifying the defect.
2. **Given** the same defect, **When** only the existing pre-push checks run on a fresh clone after standard environment setup, **Then** they also fail.
3. **Given** the same defect, **When** the hosted CI suite runs, **Then** the CI run fails on every platform job, and no covered check reports success while the defect is present.

---

### User Story 4 - Declarative configuration validated beyond workflows (Priority: P2)

As a maintainer editing any declarative configuration file tracked in the repo — CI pipeline definitions, build and packaging config, code-quality and coverage configuration, dependency update configuration, documentation build configuration, IDE settings, and tool-installed configuration alike — structural mistakes are caught, including ambiguous forms that a plain parse would silently tolerate, such as a duplicated top-level entry that silently overrides its predecessor.

**Why this priority**: pipeline and tool configuration errors either fail obscurely at run time or silently change behavior. Workflow YAML is already parsed; this extends the same safety to the remaining declarative files and to stricter structural mistakes.

**Independent Test**: Duplicate a top-level entry in any covered configuration file, run the suite, and observe a failure naming the file and the duplicate.

**Acceptance Scenarios**:

1. **Given** any covered declarative configuration file is unparseable (e.g., truncated or badly indented), **When** the automated suite runs, **Then** it fails and names the file.
2. **Given** a covered declarative configuration file contains an ambiguous duplicate top-level entry, **When** the automated suite runs, **Then** it fails and names the file and the duplicated entry.
3. **Given** all covered configuration files are well-formed, **When** the automated suite runs, **Then** the configuration checks pass.

---

### User Story 5 - Stylesheet defects caught early (Priority: P2)

As a developer editing a first-party stylesheet, a structural mistake such as an unbalanced rule block or a truncated file is caught at commit time instead of silently degrading the editor UI.

**Why this priority**: stylesheets ship to the user but are read by no quality gate. Lower priority than scripts and configuration because stylesheet defects are visual, rarely crash the app, and are more often noticed quickly by a human.

**Independent Test**: Remove a closing brace from a first-party stylesheet, run the suite, and observe a failure naming the file.

**Acceptance Scenarios**:

1. **Given** a first-party stylesheet contains an unbalanced rule block or is truncated, **When** the automated suite runs, **Then** it fails and names the file.
2. **Given** all first-party stylesheets are well-formed, **When** the automated suite runs, **Then** the stylesheet checks pass without false positives on current assets.

---

### User Story 6 - Vendor and build boundaries respected (Priority: P3)

As a developer, the new checks stay inside the working repository — repo-authored assets, the vendor scripts the editor loads from local storage, and the tracked declarative configuration files covered by FR-001 — while everything vendored, generated, or bundled (release bundles, build outputs, and checked-in third-party framework trees) is excluded. Third-party noise never blocks my work, and scanning huge vendored trees never slows my gates.

**Why this priority**: boundary discipline keeps checks meaningful and fast, but the value is protective rather than primary, and misclassification would surface the first time an exclusion wrongs a defect.

**Independent Test**: Corrupt a vendor script that ships with the editor and confirm a failure; add a trivial file inside an excluded tree and confirm the suite result and runtime are unaffected.

**Acceptance Scenarios**:

1. **Given** a vendor script asset loaded by the editor from local storage is corrupt or truncated, **When** the automated suite runs, **Then** it fails and names the file.
2. **Given** files change under excluded locations (release bundles, build outputs, third-party framework trees), **When** the automated suite runs, **Then** those files are not examined and the checks' runtime is unaffected.

### Edge Cases

- What happens when a support tool a check depends on is not installed on a contributor's machine? The check must be reported as skipped with an explicit reason, never silently passed; hosted CI must provide the tool so the check never skips there.
- What happens when a new non-Python asset or asset folder appears in the repo? Assets within an established class are picked up automatically; assets of a new class fail the self-audit check until a deliberate cover-or-exclude decision is recorded in the coverage inventory.
- What happens with empty, non-text, or non-UTF-8 asset files? The affected check must produce a clear verdict naming the file, not crash or hang.
- What happens with valid constructs a naive structural check could misread (e.g., braces inside stylesheet strings)? Such false positives must not occur on current repo assets; checks must be reliable enough to gate commits.
- What happens on a machine without a POSIX shell? Shell-dependent checks skip with a reason locally; hosted CI provides the required shell on every operating system in the matrix, so shell checks always run in CI on all three platforms.
- What happens if the repository intentionally contains a temporarily broken asset during a migration? No special allowance: gates stay consistent, and the exclusion inventory is the documented mechanism.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The automated suite MUST cover, for each non-Python asset class — (a) editor-embedded markup with its first-party and shipped-vendor scripts, (b) first-party stylesheets, (c) repo-authored shell scripts including the local git hook entry, and (d) every YAML/JSON/TOML file tracked in the repository, regardless of the file's purpose (CI pipelines, builds, quality and coverage tooling, dependency updates, documentation builds, IDE settings, and tool-installed configuration included) — every current asset of that class, not merely a sample.
- **FR-002**: Each check MUST, on failure, identify the offending file and a short reason a developer can act on.
- **FR-003**: The editor checks MUST validate at minimum: existence of every script and stylesheet asset referenced by the editor markup; presence of the structural components required for the editor to bootstrap; and syntactic validity of the embedded and shipped-vendor scripts.
- **FR-004**: The shell checks MUST detect, in every repo-authored shell script including the local git hook entry, both syntax-level defects and the latent defect classes a static analyzer can flag — at minimum unquoted expansions, unset variable use, and masked command failures. The syntax-level check MUST run in every environment that provides a POSIX shell; where no POSIX shell exists, FR-008 skip semantics apply, and the hosted CI environment provides a shell on every operating system in the matrix, so the syntax check never skips in CI. The static-analysis portion follows FR-008 skip semantics where the analyzer is unavailable locally and never skips in CI.
- **FR-005**: The declarative config checks MUST, for every covered configuration file, detect unparseable content and ambiguous duplicate mapping keys at any level — the duplicated top-level entry being the canonical silent-override case.
- **FR-006**: The stylesheet checks MUST detect unbalanced or truncated rules in every first-party stylesheet, without false positives on current assets.
- **FR-007**: All new checks MUST run as part of each existing quality gate — commit-time checks, pre-push checks, and the hosted CI test suite — with no invocation, installation, or configuration step beyond what those gates already require.
- **FR-008**: When a check's support tool is unavailable in an environment, the check MUST be reported as skipped with the reason; it MUST NOT be reported as passed, and the hosted CI environment MUST provide the required tools on every operating system in the matrix so no required check skips in CI.
- **FR-009**: Checks MUST apply only to assets inside the working repository — first-party assets, shipped-vendor editor scripts, and tracked declarative configuration per FR-001(d); release bundles, build outputs, dependency folders, and checked-in third-party framework trees MUST be excluded so their content and size never trigger failures or materially slow the checks.
- **FR-010**: The new checks MUST add no more than 30 seconds of runtime to each existing quality gate compared to the pre-feature baseline on a standard CI runner.
- **FR-011**: The non-Python check coverage MUST be documented in one discoverable place next to the checks: the asset classes covered, the defect classes caught, the exclusions, and how to extend coverage to a new asset class. The coverage inventory (asset classes plus exclusions) MUST additionally be maintained in a machine-readable form the self-audit check consumes.
- **FR-012**: The suite MUST include a self-audit check that fails, naming the file, when a tracked non-Python asset belongs to no covered class and no documented exclusion, so new asset classes cannot appear without a deliberate cover-or-exclude decision.

### Key Entities *(include if feature involves data)*

- **Editor asset bundle**: the embedded markup loaded by the editor plus the script and stylesheet assets it references; the unit that must stay internally consistent.
- **Automation script**: a repo-authored shell script that automates build, signing, release, documentation, or quality tasks, including the local git hook entry.
- **Declarative configuration**: a structured, machine-read YAML/JSON/TOML file tracked in the repository; covered regardless of purpose (CI pipeline, build, quality tooling, IDE metadata, tool-installed configuration), with family-specific shape checks where an expected top-level shape exists.
- **Quality gate**: an automated checkpoint (commit-time checks, pre-push checks, hosted CI suite) that must pass before work proceeds; every new check attaches to all of them.
- **Coverage inventory**: the machine-readable registry of covered asset classes and exclusions; consumed by coverage documentation (FR-011) and enforced by the self-audit check (FR-012).
- **Check**: one automated validation of one defect class across one asset class; reports pass, fail with file and reason, or skip with reason when its support tool is absent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The self-audit check holds on the current tree: zero tracked non-Python assets fall outside the inventory's covered classes and documented exclusions (continuous enforcement, not a one-time audit).
- **SC-002**: A defect-injection trial seeds one defect per class in FR-003 to FR-006 (missing reference, missing component, invalid script, script syntax error, unquoted-expansion script defect, unset-variable-use script defect, masked-failure script defect, unparseable config, duplicate config entry, unbalanced stylesheet rule) and 100% are caught by the automated suite, each with a message identifying the file.
- **SC-003**: Each seeded defect class, when placed in a covered asset, fails at least one existing gate — commit-time checks and pre-push checks locally, and hosted CI on every platform job — with no manual invocation beyond running the existing gates: every check executes on all three CI operating systems with no skips.
- **SC-004**: The added checks complete within the FR-010 budget: no existing gate's runtime grows by more than 30 seconds on a standard CI runner.
- **SC-005**: For one full release cycle after rollout, zero defects of the covered classes escape to a release (baseline: the recent post-hoc fixes to editor markup and workflow defects that existing automation did not catch).

## Assumptions

- The existing structural checks (editor embedded-script syntax, CI workflow parse) are the precedent to extend, not replace; no new test framework is introduced, and the new checks join the suite those checks already run in.
- "First-party" means repo-authored; "shipped-vendor" means third-party assets the editor loads from local storage (validated at parse level only); everything in release bundles and build outputs is excluded by default.
- "Automation" means all existing surfaces: the commit-time checks, the pre-push checks, and the hosted CI suite across its current platform and version matrix; the CI trigger scope itself is unchanged.
- The existing Python coverage gate is unaffected: the non-Python checks measure non-Python assets and do not count toward the Python coverage ratio.
- Support tools required by the new checks are expected to be available on hosted CI runners already, on every operating system in the matrix; during planning, each check's tool needs and OS specifics (shell availability, line-ending conversion on checkout) are reconciled so nothing required silently skips in CI.
- Introducing a new external tool dependency is acceptable only if it requires zero extra configuration in CI and is skip-safe locally; preferred are support tools already present in existing environments.
- The shell static-analysis pass is in scope together with fixing the latent defects it surfaces in existing repo-authored scripts; such fixes are limited to what the analysis flags and must not change script behavior.
- Checks are structural only; editor behavior remains the domain of the existing integration tests, which this feature does not change.

