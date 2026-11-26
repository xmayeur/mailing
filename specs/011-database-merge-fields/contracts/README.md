# Contracts: Database Merge Fields (`011-database-merge-fields`)

Internal desktop application — no external network/API surface is added. Contracts below cover the two seams work crosses: the send pipeline's substitution function and the editor's insertion bridge.

## C1: `format_message` — Python contract (`src/sendMail.py`)

```python
def format_message(
    template: str, row: list[Any], header: list[str]
) -> str:
    """Replace each ${FIELDNAME} in *template* per the merge-field rules.

    Guarantees (contract, to be enforced by tests):
    - Well-formed marker + known header        -> str(value) ("" if value empty/None)
    - Well-formed marker + unknown header      -> ""
    - Malformed text / non-markers             -> unchanged
    - Never raises for missing/unknown fields; always returns a new string
      (1:1 mapped today; of one bad field)
    - Every occurrence replaced
    """
```

Signature unchanged (all existing callers keep working); behavior contract of the unknown-field case documented and changed per FR-011 (today: whole-template rollback on error).

## C2: Batch substitution mode — internal contract

```python
def format_message_blank(template: str) -> str:
    """Replace every well-formed ${...} marker with "".

    Used when one message covers 2+ addressees. Same well-formedness
    regex as C1; malformed text untouched. Never raises.
    """
```

Call sites (contract):
- `_build_and_send` computes `mode = per-recipient if len(addressees) == 1 else blank` and must apply the same mode to **body and subject** passed to `build_email`.
- No recipient field value may reach `build_email` when |addressees| ≥ 2 (invariant I4, testable).

## C3: Editor insertion — Python↔JS contract

Python side (`src/editor.py`, RichTextEditor):

```python
def insert_field_marker(self, field_name: str) -> None:
    """Insert the marker f'${{{field_name}}}' at the current Quill cursor
    via the WebEngine bridge (fire-and-forget JS, no page reload).
    No-op if the view is unavailable; falls back to nothing (no corruption
    of content) — consistent with existing WebEngine-failure fallbacks."""

def get_field_names(self) -> list[str]:
    """Current subscriber database field names for the picker.
    Same source and caching as filter validation (_get_database_schema /
    SchemaCacheProvider); refresh follows profile/database change signals
    already wired in _load_profile_defaults and _on_database_input_changed."""
```

JS side (`src/editor_assets/editor.html`): relies on existing bridge path (`insertText` at current selection using Quill API, same convention as `setContent()` already exposed). No new page-level HTTP interface.

UI contract:
- "Insert field" entry point lists exactly the header names of the current subscriber database (SC-005), one action per field.
- If the database cannot be read: picker shows an informational message ("no fields available") and inserts nothing — content unchanged (US4 scenario 2).
- If the user dismisses the picker: no insertion (US1 scenario 3).

## C4: Observable behavior contract (send path)

Irrespective of SMTP/Gmail transport (both unchanged):
- Outgoing body (each existing part) and outgoing subject: markers resolved per C1/C2.
- Saved draft/template content and `param.message`/`param.subject` values after a send: markers still present (FR-007 / SC-004).
