# Phase 0 Research: Database Merge Fields (`011-database-merge-fields`)

## R1: Substitution engine — existing vs new

**Decision**: Reuse the existing `${field}` substitution in `src/sendMail.py:645 format_message()`; do not introduce a new engine.

**Rationale**: `format_message(template, row, header)` already implements `${column_name}` replacement with a regex (`r"\${(.*?)}"`) against the subscriber header row, and is already called per batch in `_build_and_send` (`src/sendMail.py:981`). The spec's syntax (`${ID}`) matches exactly, so the editor inserts tokens the pipeline already understands.

**Alternatives considered**:
- New template engine (e.g., Jinja2) — rejected: overkill, new dependency, different syntax than already shipped, larger blast radius.
- Editor-side substitution preview — rejected: out of scope per spec ("Out of Scope: preview").

**Key findings / gaps to fix** (drives R2–R4):
1. **Multi-recipient leak**: `_build_and_send` is called per *batch* with `bcc=",".join(addressees)` and formats the message with `row` — the **last row of the batch**. When `param.max_addr_per_mail` batches several recipients into one message, every recipient sees the last recipient's values today. Spec requires blank values in that case (US3). This is a behavior change to the batch path, not new plumbing.
2. **Unknown-field behavior**: current `format_message` returns the *entire original template* on any `ValueError`/`IndexError` (one bad marker rolls back all substitution). Spec FR-011 requires per-marker blanking. Fix inside `format_message`.
3. **Subject not substituted**: `build_email(..., subject=param.subject, ...)` receives the raw subject; `format_message` is only applied to the body. Spec FR-012 requires subject replacement with the same rules.

## R2: One-recipient vs multi-recipient semantics

**Decision**: Determine replacement mode from the batch size at `_build_and_send` time: 1 addressee → normal per-row substitution; ≥2 addressees → substitute empty string for every well-formed marker (body *and* subject). No change for malformed text (Regex only matches well-formed `${…}`).

**Rationale**: This is exactly where the system decides "one message, N recipients" (`addressees` list length, filled up to `param.max_addr_per_mail` in `send_campaign` at `src/sendMail.py:1076-1123`). It preserves the dominant one-recipient-at-a-time flow (`max_addr_per_mail == 1`) and implements the blank rule with a one-branch condition instead of a redesign.

**Alternatives considered**:
- Pass a per-recipient flag deeper into `build_email` — rejected: same result, more plumbing.
- Post-send MIME rewriting — rejected: replace before message assembly (flag order/charset concerns disappear).

## R3: Unknown-field and empty-value handling

**Decision**: `format_message` becomes per-marker resilient: well-formed marker with a known header → value (or empty string if the cell is empty); well-formed marker with an *unknown* header → empty string (FR-011, user-decided "Blank"); anything not matching `${…}` → untouched literal text (FR-009).

**Rationale**: Drawing from the clarified spec, a typo must never leak a literal `${FOO}` into a sent email. Per-marker resolution also removes today's "one bad marker rolls back everything" failure mode.

**Alternatives considered**: leave unknown markers unreplaced (rejected — literal marker visible to recipients); abort the send (rejected — user explicitly chose "Blank").

## R4: Subject-line replacement

**Decision**: Apply the same `format_message` call (same `row`/mode decision as the body) to `param.subject` in `_build_and_send`, passing the formatted subject to `build_email`. Headers with no value → blank per R3.

**Rationale**: FR-012 + clarification Q2 (subject included). Doing it at the same batch decision point guarantees subject and body can never disagree.

## R5: Editor insertion UX (Quill.js + QWebEngineView)

**Decision**: Add a native "Insert field" action (toolbar/menu button) in the editor that opens a QMenu (or Qt combo) listing field names from the existing schema pipeline: `_get_database_schema()` (`src/editor.py:1269`), fed by `SchemaCacheProvider` and refreshed in `_load_profile_defaults` (already done at `src/editor.py:1022-1042`). Selection calls the keyboard-shortcut JS path already used by the RichTextEditor: Quill `insertText` at the current selection/cursor via the existing `runJavaScript` / `qwebchannel` bridge.

**Rationale**: Schema retrieval, caching, per-profile refresh, and JS push infrastructure all exist (`setContent` pattern at `src/editor.py:3224`). The marker `${FIELD}` is plain text to Quill, so normal typing/undo/copy behave automatically and Quill keeps marker + surrounding text intact.

**Alternatives considered**:
- In-page HTML dropdown inside `editor.html` — rejected: duplicates schema plumbing through the bridge; native menu is simpler and consistent with other editor controls.
- Type-ahead inline completion — rejected: scope creep, not requested.

## R6: Marker preservation / stored content invariance

**Decision**: Substitution happens exclusively on `param.message`/`param.subject` copies at batch build time in the send path. The editor's content retrieval (`toHtml`/`get_content` path) and persistence are untouched.

**Rationale**: FR-007. Verified current flow: editor → `param.message` → `format_message` produces a fresh string (`re.sub` returns a new string); template is never mutated.

## R7: Testing strategy

**Decision**: Extend `tests/unit/test_sendmail_core.py` (format_message: known/unknown/empty values, malformed markers, multi-occurrence; blank-batch mode; subject formatting) and `tests/integration/test_sendmail_integration.py` (1 vs ≥2 addressee batching with `donotsend`); editor-side picker/insert covered in `tests/unit/test_editor.py` at the bridge level (mock WebEngine), consistent with existing editor tests.

**Rationale**: Follows the repo's established layout (`tests/unit`, `tests/integration`; note spec `010-non-python-tests` covers non-Python tests separately). pytest stack already configured in `pyproject.toml`.

**Alternatives considered**: behave BDD scenarios only — insufficient granularity for the substitution edge cases.
