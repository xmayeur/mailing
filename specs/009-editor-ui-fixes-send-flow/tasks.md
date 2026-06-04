# Tasks: Editor UI Fixes & Send Workflow

**Input**: Design documents from `/specs/009-editor-ui-fixes-send-flow/`  
**Branch**: `009-editor-ui-fixes-send-flow`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase
- **[Story]**: Maps to user story in spec.md
- All implementation in `src/editor.py` and `src/editor_assets/editor.html`

---

## Phase 1: Foundational

**Purpose**: Verify baseline — no new infrastructure needed, just confirm test suite passes before touching code.

- [ ] T001 Run `pytest tests/ -v` and confirm 0 failures on branch HEAD in project root

**Checkpoint**: Green baseline confirmed. All story work can proceed.

---

## Phase 2: User Story 1 — Insert Hyperlink via Menu (Priority: P1)

**Goal**: "Insert Hyperlink" menu item calls same code path as Ctrl+K toolbar button, pre-filling selected text.

**Independent Test**: Select text → Format menu → Insert Hyperlink → enter URL → OK → `<a href="...">selected text</a>` inserted, identical to Ctrl+K result.

- [ ] T002 [P] [US1] Replace `_menu_insert_link()` body with `self._run_js("handleLinkInsert()")` in `src/editor.py:3881` — delete the 12-line manual JS block, single `_run_js` call delegates to existing JS handler
- [ ] T003 [P] [US1] Verify `handleLinkInsert` function in `src/editor_assets/editor.html:840` is in `window` scope (plain `function` declaration inside `<script>` is already global; no change needed if confirmed)

**Checkpoint**: Ctrl+K and menu item produce identical output. Selected text pre-fills display field.

---

## Phase 3: User Story 2 — Anchor Tag Uses `id` Attribute (Priority: P1)

**Goal**: Anchor blot writes `id="name"` not `data-anchor-id="name"`. Browser `#anchor-name` links resolve correctly.

**Independent Test**: Insert anchor "section1" → view saved HTML → confirm `<a id="section1"></a>` present, zero occurrences of `data-anchor-id`.

- [ ] T004 [P] [US2] Fix `AnchorBlot.create()` in `src/editor_assets/editor.html:445` — change `node.setAttribute('data-anchor-id', id)` to `node.setAttribute('id', id)`
- [ ] T005 [P] [US2] Fix `AnchorBlot.value()` in `src/editor_assets/editor.html:452` — change `node.getAttribute('data-anchor-id')` to `node.getAttribute('id')`
- [ ] T006 [US2] Add `@staticmethod _sanitize_anchor_name(name: str) -> str` to `EditorWindow` in `src/editor.py` after `_menu_insert_anchor` — lowercase, replace spaces with `-`, strip chars not in `[a-z0-9_-]`, strip leading `-`, return `""` if result empty
- [ ] T007 [US2] Update `_menu_insert_anchor()` in `src/editor.py:3895` to call `_sanitize_anchor_name(name)` before `_run_js(f"insertAnchor(...)")` — skip insert if sanitized name is empty

**Checkpoint**: Saved HTML has `id=` anchors. `#anchor-name` links in HTML resolve in browser. Spaces in anchor names become hyphens.

---

## Phase 4: User Story 4 — Send Workflow with Live Session Log (Priority: P1)

**Goal**: Send button opens `_SessionLogDialog` immediately; log lines stream live as send runs in background thread; confirmation prompt before close; test-mode lock/unlock.

**Independent Test**: Click Send in editor → Send dialog opens (Test locked) → click Send → log dialog opens immediately (before send completes) → log lines appear as send runs → after completion confirmation prompt appears → confirm → test unlocked → second send → log dialog → confirm → Send dialog stays open.

- [ ] T008 [US4] Extend `_SessionLogDialog.__init__()` in `src/editor.py:284` — add `log_line_received = pyqtSignal(str)` class attr, `_send_complete: bool = False` instance attr; connect `log_line_received` to `append_log`
- [ ] T009 [US4] Add `closeEvent(self, event)` override to `_SessionLogDialog` in `src/editor.py` — if `_send_complete` is False, call `event.ignore()` and show `QMessageBox.warning` "Send in progress — wait for completion"; otherwise `event.accept()`
- [ ] T010 [US4] Add `set_complete(self, success: bool, is_test: bool) -> None` to `_SessionLogDialog` in `src/editor.py` — sets `_send_complete = True`; shows `QMessageBox.question` ("Test received?" for test, "Send complete. OK?" for bulk); returns user's response as bool; enables Close button
- [ ] T011 [US4] Add `_SendWorker(QThread)` class to `src/editor.py` after `_SessionLogDialog` — fields: `log_line = pyqtSignal(str)`, `finished = pyqtSignal(str)`, `_dialog: _SendDialog`, `_send_fn: Callable`; `run()` installs `_LogCapture` handler that emits `log_line` per record, calls `_send_fn(_dialog)`, emits `finished(result)`; on exception emits `finished(f"ERROR: {exc}")`; removes handler in `finally`
- [ ] T012 [US4] Add `_on_send_finished(self, result: str, dialog: _SendDialog, log_dialog: _SessionLogDialog) -> None` to `EditorWindow` in `src/editor.py` — calls `log_dialog.set_complete(success, is_test)`, on test success+confirm calls `dialog._unlock_test_mode()` + unchecks `test_check`; re-enables `dialog.send_button`
- [ ] T013 [US4] Refactor `_on_send_dialog_send()` in `src/editor.py:3982` — replace synchronous send block with: disable Send button, create `_SessionLogDialog(self)`, create `_SendWorker(dialog, self._send_with_sendmail)`, connect `worker.log_line → log_dialog.log_line_received`, connect `worker.finished → lambda r: self._on_send_finished(r, dialog, log_dialog)`, start worker, call `log_dialog.exec()` (blocks until user closes after confirmation)

**Checkpoint**: Log dialog opens before send completes. First log line appears within 2s. Confirmation prompt blocks close. Test unlock works after confirmation.

---

## Phase 5: User Story 3 — View HTML Source (Priority: P2)

**Goal**: "View HTML Source" action opens read-only dialog with current document HTML and Copy to Clipboard button.

**Independent Test**: Type content in editor → click View menu → View HTML Source → dialog shows full HTML → click Copy → paste in text editor → content matches.

- [ ] T014 [US3] Add `_HtmlSourceDialog(QDialog)` class to `src/editor.py` after `_SessionLogDialog` — constructor `(parent, html_content: str)`; `QPlainTextEdit` read-only monospaced; Copy button calls `QApplication.clipboard().setText(html_content)`; Close button; minimum size 800×600
- [ ] T015 [US3] Add `_menu_view_source(self) -> None` to `EditorWindow` in `src/editor.py` — calls `self._bridge.get_current_html()`, opens `_HtmlSourceDialog(self, html)` via `exec()`
- [ ] T016 [US3] Add "View &HTML Source" action to a "View" top-level menu in `_build_menus()` in `src/editor.py:3474` — shortcut `Ctrl+Shift+U`, connect to `_menu_view_source`; insert View menu between Format and Table menus (or after Settings if no logical place)

**Checkpoint**: Source dialog opens under 500ms. Content matches saved HTML. Copy button puts full HTML on clipboard. Dialog close does not modify document.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T017 Run `ruff check src/editor.py` and fix any new lint errors introduced by changes in `src/editor.py`
- [ ] T018 Run `mypy src/editor.py --ignore-missing-imports` and fix any new type errors
- [ ] T019 Run `pytest tests/ -v` and confirm all existing tests still pass
- [ ] T020 Execute manual verification checklist from `specs/009-editor-ui-fixes-send-flow/quickstart.md` — all 5 items checked

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: No dependencies — start immediately
- **Phase 2 (US1)**: After Phase 1 baseline confirmed
- **Phase 3 (US2)**: After Phase 1; independent of Phase 2 — can run in parallel with Phase 2
- **Phase 4 (US4)**: After Phase 1; independent of Phases 2–3 — can run in parallel
- **Phase 5 (US3)**: After Phase 1; independent of Phases 2–4 — can run in parallel
- **Phase 6 (Polish)**: After all story phases complete

### Within Phase 4 (US4 send workflow)

T008 → T009 → T010 (extend `_SessionLogDialog` sequentially — same class)  
T011 (new class, independent of T008–T010 edits)  
T012 depends on T010 (calls `set_complete`), T011 (references `_SendWorker`)  
T013 depends on T008–T012 all complete

---

## Parallel Opportunities

### Phase 2 + 3 can run together

```
Task A (Phase 2): T002 — fix _menu_insert_link in src/editor.py
Task B (Phase 3): T004 + T005 — fix AnchorBlot in src/editor_assets/editor.html
```

### Phase 4 + 5 can start after Phase 1

```
Task A (Phase 4): T008–T013 — send workflow in src/editor.py
Task B (Phase 5): T014–T016 — HTML source view in src/editor.py
```
*(Note: both touch `editor.py` — coordinate to avoid conflicts if working in parallel)*

---

## Implementation Strategy

### MVP (P1 stories only)

1. T001 — baseline
2. T002–T003 — US1 hyperlink fix
3. T004–T007 — US2 anchor fix
4. T008–T013 — US4 send workflow
5. Validate P1 stories independently

### Full Delivery

Add Phase 5 (US3) after P1 stories validated.

---

## Notes

- `editor.py` is 4305 lines — use line number references from plan.md when navigating
- `_SessionLogDialog` is at line 281, `_SendDialog` at 394, `EditorWindow._menu_insert_link` at 3881
- AnchorBlot fix (T004–T005) is 2 lines in `editor.html` — high confidence, low risk
- `_menu_insert_link` fix (T002) is replacing ~12 lines with 1 — verify `handleLinkInsert` is in global scope first (T003)
- `_SendWorker` must use Qt signals for all UI updates — never call widget methods from `run()`
