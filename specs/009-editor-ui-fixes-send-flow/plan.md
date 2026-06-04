# Implementation Plan: Editor UI Fixes & Send Workflow

**Branch**: `009-editor-ui-fixes-send-flow` | **Date**: 2026-06-04 | **Spec**: [spec.md](spec.md)

## Summary

Fix four broken/missing editor features: (1) Insert Hyperlink menu calls JS `handleLinkInsert()` directly instead of duplicating logic; (2) Anchor blot uses `id` attribute instead of `data-anchor-id`; (3) New read-only HTML source view dialog; (4) Send workflow opens `_SessionLogDialog` immediately with live log streaming via background thread, confirmation prompt before close, and test-mode unlock gate.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: PyQt6 6.7+, PyQt6-WebEngine, Quill.js v2 (in editor_assets/)  
**Storage**: Local filesystem (.html/.md files)  
**Testing**: pytest (unit tests in tests/unit/, integration in tests/integration/)  
**Target Platform**: macOS / Linux / Windows desktop app  
**Project Type**: Desktop GUI app (single executable via PyInstaller)  
**Performance Goals**: Source dialog opens <500ms for 500KB docs (SC-003); first log line within 2s of Send click (SC-005)  
**Constraints**: Single file `src/editor.py` + `src/editor_assets/editor.html` — no new source files unless unavoidable; existing `_SessionLogDialog` and `_SendDialog` classes extended, not replaced

## Constitution Check

Constitution file contains only template placeholders — no active principles defined. No gate violations possible. Proceeding.

## Project Structure

### Documentation (this feature)

```text
specs/009-editor-ui-fixes-send-flow/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (files changed)

```text
src/
├── editor.py            ← primary changes (4 fixes)
└── editor_assets/
    └── editor.html      ← anchor blot fix + expose handleLinkInsert globally
tests/
└── unit/
    └── test_editor_fixes.py   ← new unit tests for fixes
```

---

## Phase 0: Research

### Fix 1 — Insert Hyperlink menu (FR-001, FR-002)

**Current behaviour**: `_menu_insert_link()` (line 3881) calls Python-side `self._bridge.request_link_insert("")` with empty selected text, then manually runs JS. This duplicates—and diverges from—the toolbar `handleLinkInsert()` JS handler.

**Root cause**: Menu action does not delegate to the existing JS `handleLinkInsert()` function which already gets selected text from Quill and calls `bridge.request_link_insert(selectedText, callback)` asynchronously.

**Decision**: Expose `handleLinkInsert` as `window.handleLinkInsert` in `editor.html` (it is currently a plain `function` declaration, scoped to the IIFE/`window` already since it's in script scope — verify at `editor.html:840`). Replace `_menu_insert_link()` body with `self._run_js("handleLinkInsert()")`.

**Alternatives considered**: Keep Python-side dialog call but pre-fetch selection via JS — rejected because it adds async complexity and duplicates JS logic.

### Fix 2 — Anchor `data-anchor-id` → `id` (FR-003, FR-004)

**Current behaviour**: `AnchorBlot.create()` in `editor.html` lines 444-446 writes `data-anchor-id` attribute; `AnchorBlot.value()` line 452 reads `data-anchor-id`. Python's `_spans_to_anchors()` and `_anchors_to_spans()` use the `id` attribute correctly, so round-trip breaks.

**Decision**: Change both `setAttribute('data-anchor-id', id)` → `setAttribute('id', id)` and `getAttribute('data-anchor-id')` → `getAttribute('id')` in `editor.html`.

**Anchor name sanitization (FR-004)**: `_menu_insert_anchor()` already receives the raw name from `_AnchorDialog`. Add a `_sanitize_anchor_name()` static method: lowercase, replace spaces with hyphens, strip chars not matching `[a-z0-9_-]`, trim leading hyphens.

### Fix 3 — HTML Source View (FR-005 through FR-008)

**Current state**: No source view exists.

**Decision**: Add `_HtmlSourceDialog(QDialog)` class with:
- `QPlainTextEdit` (read-only, monospaced)
- Close button + Copy to Clipboard button
- Content populated from `window.get_current_html()` via `self._bridge.get_current_html()`

Add "View &HTML Source" action to the View/Format menu (or a new View menu). Trigger: `self._run_js` is not needed — just call `self._bridge.get_current_html()` synchronously and open dialog.

**View menu**: Check `_build_format_menu` (line 3531) and `_build_menus` (line 3474) — add under a new "View" top-level menu or append to Format menu after separator.

### Fix 4 — Send Workflow with Live Session Log (FR-009 through FR-014)

**Current behaviour**: `_on_send_dialog_send()` (line 3982) runs `_send_with_sendmail()` synchronously (blocking UI thread), captures log entries into a list during the call, then shows `_SessionLogDialog` AFTER send completes. The test-mode lock/unlock works but no live streaming exists.

**Decision**: Refactor to threaded send with live log streaming:

1. **`_SessionLogDialog` changes**:
   - Add `log_line_received` signal (`pyqtSignal(str)`) → connected to `append_log`
   - Add `_send_complete` flag; override `closeEvent` to block close until `_send_complete` is True
   - Add `set_complete(success: bool, is_test: bool)` method: shows confirmation `QMessageBox` inside dialog (or appended text + unlocks Close button)
   - Remove auto-close; user must click Close after confirming

2. **`_SendWorker(QThread)` inner class** (or `QRunnable`):
   - Signals: `log_line = pyqtSignal(str)`, `finished = pyqtSignal(str)` (result string)
   - Runs `_send_with_sendmail(dialog)` in `run()`; captures log via `_LogCapture` emitting to `log_line` signal
   - On exception: emits `finished("ERROR: ...")`

3. **`_on_send_dialog_send()` refactor**:
   - Disable Send button
   - Create `_SessionLogDialog(self)` — open immediately (no content yet)
   - Create `_SendWorker(dialog)`, connect `worker.log_line → log_dialog.append_log`, `worker.finished → _on_send_finished`
   - Start worker thread
   - `log_dialog.exec()` blocks until user closes (after confirmation)

4. **`_on_send_finished(result, dialog, log_dialog)`**:
   - Calls `log_dialog.set_complete(success, is_test)` which shows confirmation prompt
   - On test success + confirm: calls `dialog._unlock_test_mode()`, unchecks test_check
   - On bulk send success: re-enables Send button but keeps dialog open (FR-013)

**Thread safety**: All UI updates from worker go through Qt signals (queued connection). No direct widget manipulation from thread.

**Interrupt / close mid-send (edge case)**: If user closes log dialog before send finishes → warn via `QMessageBox` "Send still in progress" and re-open or keep open. Implement via `closeEvent` guard.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md).

### Key class/method changes

| Location | Change | FR |
|---|---|---|
| `editor.html:444-452` | `data-anchor-id` → `id` in AnchorBlot | FR-003 |
| `editor.html:840` | Ensure `handleLinkInsert` is `window.handleLinkInsert` | FR-001 |
| `editor.py:_menu_insert_link` | Replace body with `self._run_js("handleLinkInsert()")` | FR-001,002 |
| `editor.py:_menu_insert_anchor` | Add `_sanitize_anchor_name()` call before JS | FR-004 |
| `editor.py:_HtmlSourceDialog` | New class (read-only source viewer) | FR-005–008 |
| `editor.py:_build_menus/_build_format_menu` | Add "View HTML Source" action | FR-005 |
| `editor.py:_SessionLogDialog` | Add signal, `closeEvent` guard, `set_complete()` | FR-010–014 |
| `editor.py:_SendWorker` | New `QThread` subclass for background send | FR-010 |
| `editor.py:_on_send_dialog_send` | Refactor to open log dialog + start worker | FR-009–014 |

### No new external contracts

This is a desktop app with no API or CLI interface exposed by this feature. Contracts section N/A.

### Agent context

Run after plan: `.specify/scripts/bash/update-agent-context.sh claude`
