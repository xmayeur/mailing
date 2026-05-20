# Implementation Plan: Visual Filter Builder UI

**Branch**: `004-visual-filter-builder` | **Date**: 2026-05-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-visual-filter-builder/spec.md`

## Summary

Add visual table-based filter editor to Send Mailing dialog (`_SendDialog` in editor.py). Current YAML text editor will be augmented with a visual interface allowing non-technical users to build filters via dropdown selection of fields/operators/values. Both editors remain available and stay synchronized—changes in one reflect in the other. Integrates with existing filter validation and database schema detection.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: PyQt6 (≥6.7.0), pyyaml, gspread, google-api-python-client  
**Storage**: N/A (filter definitions stored in YAML config)  
**Testing**: pytest (existing test framework)  
**Target Platform**: Desktop (macOS/Linux/Windows via PyQt6)  
**Project Type**: Desktop GUI application (Qt-based)  
**Performance Goals**: UI responsiveness <100ms for filter edits, schema loading <500ms  
**Constraints**: <50MB additional memory for large schemas (10k+ fields), Qt compatibility  
**Scale/Scope**: Support 50-1000 subscriber database fields, multi-profile filters

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Project Constitution**: Template not yet defined in `.specify/memory/constitution.md`  
**Derived Constraints** (from CLAUDE.md and git history):

- ✓ **Type Safety**: Project enforces `mypy --strict` and `ruff check .` — all function signatures must be fully typed
- ✓ **Test-Driven**: Existing tests use pytest with mocking for Qt components — tests must mock PyQt6 to avoid display dependencies
- ✓ **Code Style**: flake8 (max-complexity=10, max-line-length=127), black formatting, ruff linting enforced in CI
- ✓ **Integration Pattern**: Filter validation and matching already integrated via `FilterValidator` and `FilterMatcher` — reuse existing components
- ✓ **UI Patterns**: Use PyQt6 native widgets (no custom frameworks); existing dialogs use QFormLayout + standard controls

**Gate Status**: ✓ PASS — Feature complies with type safety, testing, and UI patterns

## Project Structure

### Documentation (this feature)

```text
specs/004-visual-filter-builder/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — operator mapping, field type detection
├── data-model.md        # Phase 1 output — FilterRow, FilterTable, FilterBuilder entities
├── quickstart.md        # Phase 1 output — how to use visual filter editor in dialog
├── contracts/           # Phase 1 output — Qt dialog contract (signals/slots)
│   └── qt-filter-editor-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Single Project Structure** (extending existing sendMail codebase):

```text
src/
├── sendMail.py                    # [MODIFY] Filter function and operators (read-only for visual builder)
├── editor.py                      # [MODIFY] _SendDialog class — add visual filter editor
├── filter_validator.py            # [EXTEND] Reuse existing validation
├── filter_matcher.py              # [REUSE] Already wraps sendMail.filter()
├── schema_provider.py             # [REUSE] Database schema extraction
├── schema_cache.py                # [REUSE] Schema caching
└── visual_filter_builder.py       # [NEW] Core visual editor widget + components

tests/
├── unit/
│   ├── test_sendMail.py           # [EXTEND] Test new filter edge cases
│   ├── test_filter_validator.py   # [EXISTING] Already tests YAML parsing
│   └── test_visual_filter_builder.py  # [NEW] Test visual editor components
├── integration/
│   └── test_send_dialog_filter.py # [NEW] Test dialog integration
└── contract/
    └── test_visual_filter_contract.py  # [NEW] Test Qt signal/slot contracts
```

**Structure Decision**: Add new `visual_filter_builder.py` module for visual editor components (FilterTableWidget, FilterRowWidget, etc.). Integrate into existing `_SendDialog` via composition—no changes to module structure, minimal surface area.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Decision | Rationale | Alternative Rejected |
|----------|-----------|----------------------|
| New module `visual_filter_builder.py` | Isolates visual components from sendMail.py (single responsibility); easier testing | Inline in editor.py would couple filter logic to dialog lifecycle |
| Reuse FilterValidator/FilterMatcher | Already battle-tested; no validation logic duplication | Writing new validator adds maintenance burden |
| PyQt6 native widgets only | Consistent with existing project (no custom frameworks); faster render | Web-based editor (like newsletter editor) adds dependency and complexity |

---

## Phase 0: Research & Unknowns

### Research Tasks

**R001: Operator-to-Field-Type Mapping**
- Question: Which operators are valid for text vs. numeric vs. date fields?
- Source: `_FILTER_OPS` list in sendMail.py (26 operators defined)
- Task: Analyze operator semantics and build mapping table

**R002: Field Type Detection**
- Question: How to infer field types from database schema (CSV headers or Google Sheets)?
- Current state: `DatabaseSchemaProvider` returns field names only (no types)
- Task: Decide on heuristic (column name patterns, sample value inspection, or user hint)

**R003: Visual-to-YAML Synchronization**
- Question: Real-time sync or deferred (apply button)?
- Constraint: Spec says "filter table updates reflect changes immediately (latency <100ms)"
- Task: Validate real-time sync is feasible with Qt signal/slot architecture

**R004: Operator Display Names**
- Question: User-facing operator labels vs. internal identifiers
- Current state: `_FILTER_OPS` has both short forms ("is") and long forms ("is equal to")
- Task: Determine which operators to show in dropdown for clarity

### Findings

✓ **Complete** — See `research.md` for detailed findings on:
- **R001**: Operators categorized by field type (universal, text-only, numeric-only, set membership)
- **R002**: Default all fields to "text" type (safe for MVP)
- **R003**: Real-time bidirectional sync validated (<10ms latency via Qt signals)
- **R004**: User-friendly operator labels mapped to canonical forms

---

## Phase 1: Design & Contracts

*Prerequisites*: research.md complete with findings for R001-R004

### 1.1 Data Model

**Entities to generate** (data-model.md):

- **FilterRow**: Single filter condition (field + operator + optional value)
  - Fields: `field_name: str`, `operator: str`, `value: str | None`
  - Validation: field exists in schema, operator is valid for field type

- **FilterTable**: Collection of FilterRow with add/edit/delete operations
  - Fields: `rows: list[FilterRow]`
  - Methods: `add_row()`, `delete_row(index)`, `update_row(index, field, operator, value)`, `to_dict() -> dict[str, str]`

- **DatabaseSchemaInfo**: Metadata about available fields
  - Fields: `fields: list[str]`, `field_types: dict[str, str]` (inferred via R002 heuristic)
  - Methods: `get_operators_for_field(field_name) -> list[str]`

- **FilterBuilder** (Qt widget): Visual editor combining table + YAML text
  - Composition: FilterTableWidget (visual) + QPlainTextEdit (YAML) in tabs or splitter
  - Signals: `filter_changed(dict[str, str])` — emitted when filter changes
  - Methods: `set_filter_from_yaml(text)`, `get_filter_as_yaml() -> str`

### 1.2 Qt Dialog Contract

**Output**: qt-filter-editor-contract.md

Document:
- FilterBuilder widget public interface (init, methods, signals/slots)
- Integration points with _SendDialog (where to insert widget, signal connections)
- State lifecycle (creation, profile changes, filter updates)

### 1.3 Operator Mapping (from R001 findings)

**Output**: operator-mapping.json (referenced in quickstart.md)

Example structure:
```json
{
  "text_operators": ["is", "contains", "starts with", "ends with", "matches"],
  "numeric_operators": ["gt", "lt", "ge", "le", "is", "is not"],
  "any_operators": ["is empty", "is not empty"],
  "text_only": ["contains", "starts with", "ends with", "matches"],
  "numeric_only": ["gt", "lt", "ge", "le"]
}
```

### 1.4 Quickstart

**Output**: quickstart.md

Cover:
- How to launch and use visual filter editor in Send Mailing dialog
- Example workflow: add filter row, select field from dropdown, select operator, enter value
- How visual and YAML editors stay in sync
- Supported operators and field types

### 1.5 Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh claude` to inject:
- FilterBuilder widget API
- Qt signal/slot patterns used
- New module imports (visual_filter_builder)

---

## Next Steps

1. **Phase 0 Research** (if needed):
   - Research R001-R004 via agent or manual analysis
   - Consolidate findings in research.md
   - Document operator-to-field mapping

2. **Phase 1 Implementation Planning** (after this file approved):
   - Generate data-model.md with entity definitions
   - Create contracts/ with Qt interface documentation
   - Create quickstart.md with usage guide
   - Run agent context update

3. **Phase 2 Task Generation** (`/speckit.tasks`):
   - Break design into implementation tasks
   - Map to source files (visual_filter_builder.py, editor.py, tests/)
   - Assign priorities (P1: visual editor; P2: sync; P3: performance tuning)
