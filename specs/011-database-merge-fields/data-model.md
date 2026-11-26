# Phase 1 Data Model: Database Merge Fields (`011-database-merge-fields`)

## Entities

### MergeField (marker)

| Attribute | Type | Rule |
|-----------|------|------|
| Syntax | String | `${FIELDNAME}` — literal `${` prefix, `}` suffix |
| FieldName | String | Exact header name of the subscriber database field (case-sensitive, matches existing `header.index(key)` semantics in `format_message`) |
| Occurrence | — | Repeats freely; every occurrence processed |

Validation rules:
- Well-formed marker: matches `r"\${(.*?)\}"` (existing regex in `format_message`, `src/sendMail.py:665`).
- Resolvable marker: well-formed AND `FieldName` exists in the current database header list.
- Non-marker / malformed text: never modified (FR-009).

State transitions: none (static text in stored content). Lifecycle: inserted while editing → carried unchanged into the stored message → resolved at batch build time in a fresh output string.

### Subscriber database

| Attribute | Type | Rule |
|-----------|------|------|
| Source | CSV file / Excel file / Google Sheet | Existing profile `database` setting |
| Header (fields) | list[str] | First row; source of truth for picker list and marker resolution |
| Records | list[list[Any]] | One row per recipient; column order matches header |

Relationships: a profile references exactly one subscriber database; a MergeField references one header entry; a recipient record supplies values for all fields.

### Batch (send-time concept, existing)

| Attribute | Type | Rule |
|-----------|------|------|
| Addressees | list[str] | Email addresses in the current message; built by `send_campaign` up to `param.max_addr_per_mail` |
| Row | list[Any] | Last row of the batch; used for substitution when |Addressees| == 1 |
| Mode | enum | `per-recipient` (|Addressees| == 1) / `blank` (|Addressees| ≥ 2) — **new**; passed to `build_email` as `merge_row`/`merge_header` or `blank_merge=True` (see research.md R8) |

State transitions: none (ephemeral per batch).

## Substitution rules (consolidated)

| Input                                    | One-recipient message          | Multi-recipient message  |
|------------------------------------------|--------------------------------|--------------------------|
| ${KNOWN} with non-empty value            | recipient's value (FR-005)     | "" (FR-006)              |
| ${KNOWN} with empty/missing value        | "" (FR-010)                    | "" (FR-006)              |
| ${UNKNOWN} (field not in header)         | "" (FR-011)                    | "" (FR-011)              |
| Malformed / literal text (`${`, `${X`)   | unchanged (FR-009)             | unchanged (FR-009)       |

Applied to: message body (all parts that exist — HTML or plain) and subject line (FR-012/FR-013). Stored content is never modified (FR-007).

## Invariants

- I1: `format_message(template, row, header)` never raises for data-shape reasons; unknown fields degrade to "" per marker.
- I2: The stored template is a pure input: `format_message` always returns a new string.
- I3: With `max_addr_per_mail == 1` (the standard flow), output is identical to today's behavior for known fields; only the unknown-field rollback case changes.
- I4: A multi-recipient message never contains a subscriber's field value (privacy requirement behind US3).
