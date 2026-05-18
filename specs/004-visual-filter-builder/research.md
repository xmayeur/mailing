# Phase 0 Research: Visual Filter Builder

**Date**: 2026-05-18 | **Status**: Complete | **Findings**: 4/4 research questions resolved

## R001: Operator-to-Field-Type Mapping

**Question**: Which operators are valid for text vs. numeric fields?

**Analysis**:

From `sendMail.py` (_FILTER_OPS list, 26 operators):

```python
_FILTER_OPS = [
    "is",                        # Equality (ambiguous, works for any type)
    "is not",                    # Inequality (ambiguous)
    "gt", "lt", "ge", "le",      # Numeric comparisons
    "in", "not in",              # Set membership (ambiguous)
    "is empty", "is not empty",  # Null checks (universal)
    "greater than", "less than", "greater or equal to", "less or equal to",  # Numeric (verbose)
    "one of", "none of",         # Multi-value (ambiguous, works with text too)
    "is equal to", "is not equal to",  # Equality (explicit, universal)
    "eq", "ne",                  # Equality (abbreviated, universal)
    "contains", "does not contain",    # Text only
    "starts with", "ends with",        # Text only
    "matches", "does not match",       # Regex (text-focused but can work on any)
]
```

**Categorization**:

| Category | Operators | Applicable To |
|----------|-----------|---------------|
| **Universal** | `is`, `is not`, `is equal to`, `is not equal to`, `eq`, `ne`, `is empty`, `is not empty` | All field types |
| **Text-Only** | `contains`, `does not contain`, `starts with`, `ends with`, `matches`, `does not match` | String fields |
| **Numeric-Only** | `gt`, `lt`, `ge`, `le`, `greater than`, `less than`, `greater or equal to`, `less or equal to` | Numeric fields |
| **Set Membership** | `in`, `not in`, `one of`, `none of` | Any type (value is comma-separated list) |

**Decision**: Default field type to "text" (most common in subscriber databases). Provide optional field-type hints in schema detection (see R002).

---

## R002: Field Type Detection

**Question**: How to infer field types without schema metadata?

**Current State**: `DatabaseSchemaProvider.detect_and_extract()` returns only field names (no types).

**Options Evaluated**:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A: No type hints (default all text)** | Assume all fields are text; show universal + text operators | Simple, safe, works for most use cases | Numeric fields see text-only operators; no numeric comparison |
| **B: Column name heuristics** | Infer type from field names (e.g., "amount" → numeric, "date" → date) | Lightweight, works offline | Unreliable, fragile to naming changes |
| **C: Sample value inspection** | Scan first N rows to detect numeric/date patterns | Accurate | Requires data access at filter setup time; slow for large CSVs |
| **D: User hint in field dropdown** | Show all fields with optional type selector per field | Accurate, flexible | Adds UI complexity; user burden |

**Recommendation**: Start with **Option A** (default to text, all operators available). Extend to **Option C** (sample inspection) in Phase 2 if performance permits. Document assumption in quickstart.md.

**Rationale**: Subscriber databases are primarily text-based (emails, names, status strings). Numeric fields are rare. Safer to show more operators than fewer—users can ignore irrelevant ones.

---

## R003: Visual-to-YAML Synchronization

**Question**: Real-time sync or deferred (apply button)?

**Spec Requirement**: "Filter table updates reflect changes immediately (latency <100ms)" — mandates real-time.

**Qt Architecture**:
- FilterTableWidget emits `filter_changed()` signal on any row edit
- _SendDialog slot receives signal, calls `visual_editor.to_dict()` to get updated filter
- Update `filter_text_edit.setPlainText()` with new YAML
- Text editor emits `textChanged` signal
- _SendDialog updates `_session_filter` dict

**Validation**: Qt signal/slot is O(1) per edit. YAML generation via dict→YAML is O(n) where n = number of rows (typically <20). Total latency <10ms on modern hardware, well under 100ms target.

**Decision**: Implement real-time bidirectional sync:
- Visual editor change → trigger YAML update
- YAML text change → parse and update visual table (with validation)
- Both remain visible; changes propagate instantly

---

## R004: Operator Display Names

**Question**: User-facing labels vs. internal identifiers?

**Current Ambiguities**: Multiple names for same operation:
- "is" vs. "is equal to" vs. "eq"
- "is not" vs. "is not equal to" vs. "ne"
- "gt" vs. "greater than"

**User Experience Analysis**:
- Short forms ("is", "gt") are cryptic for non-technical users
- Long forms ("is equal to", "greater than") are verbose but clear
- Mixed naming creates confusion in dropdown

**Recommendation**: 

Use **user-friendly display names** in dropdown. Map to canonical operators at save time:

```python
OPERATOR_LABELS = {
    "Is equal to": ["is", "eq", "is equal to"],
    "Is not equal to": ["is not", "ne", "is not equal to"],
    "Greater than": ["gt", "greater than"],
    "Less than": ["lt", "less than"],
    "Greater or equal": ["ge", "greater or equal to"],
    "Less or equal": ["le", "less or equal to"],
    "Contains": ["contains"],
    "Does not contain": ["does not contain"],
    "Starts with": ["starts with"],
    "Ends with": ["ends with"],
    "Is empty": ["is empty"],
    "Is not empty": ["is not empty"],
    "In list": ["one of", "in"],
    "Not in list": ["none of", "not in"],
    "Matches regex": ["matches"],
    "Does not match": ["does not match"],
}
```

Internal representation: Use canonical form (prefer long form for clarity).

---

## Summary: Decisions Made

| Research Task | Decision | Impact |
|---------------|----------|--------|
| **R001** | Categorize operators by field type; show all unless field type known | Operator dropdown adapts as field selection changes |
| **R002** | Default all fields to "text" (can extend with type hints later) | Safe, simple; some numeric operators may be unused |
| **R003** | Real-time bidirectional sync with <10ms latency | Filter updates instantly; YAML editor always in sync with visual |
| **R004** | User-friendly display names; map to canonical operators at save | Dropdown shows "Greater than", internally stored as "gt" |

All findings are compatible with existing filter infrastructure (sendMail.filter, FilterValidator, FilterMatcher).

---

## Assumptions & Constraints

- Subscriber databases consist primarily of text fields (no type hints needed for MVP)
- Filter performance not critical (rows typically <20 conditions)
- PyQt6 signal/slot performance sufficient for real-time updates
- YAML round-trip (dict → YAML → dict) preserves filter semantics
