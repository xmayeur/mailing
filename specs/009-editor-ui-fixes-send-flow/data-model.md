# Data Model: Editor UI Fixes & Send Workflow

## Entities

### `_HtmlSourceDialog` (new class)

| Field | Type | Description |
|---|---|---|
| `_text_view` | `QPlainTextEdit` | Read-only HTML content display |
| `_copy_button` | `QPushButton` | Copies full HTML to clipboard |
| `_close_button` | `QPushButton` | Closes dialog |

**Constructor**: `__init__(parent, html_content: str)`  
**Validation**: `html_content` may be empty string (show empty dialog, not an error)

---

### `_SessionLogDialog` (extended)

New fields added to existing class:

| Field | Type | Description |
|---|---|---|
| `log_line_received` | `pyqtSignal(str)` | Signal for appending a log line from worker thread |
| `_send_complete` | `bool` | Guards `closeEvent` — False until `set_complete()` called |
| `_close_button` | `QPushButton` | Replaces or supplements existing Close button |

New methods:

| Method | Signature | Purpose |
|---|---|---|
| `set_complete` | `(success: bool, is_test: bool) -> None` | Shows confirmation prompt; sets `_send_complete = True`; enables close |
| `closeEvent` | override | Prevents close while `_send_complete` is False; warns user |

**State transitions**:
```
OPEN (send running)  →  set_complete() called  →  CONFIRMABLE  →  user confirms  →  CLOSEABLE
```

---

### `_SendWorker` (new class, `QThread` subclass)

| Field/Signal | Type | Description |
|---|---|---|
| `log_line` | `pyqtSignal(str)` | Emitted for each captured log line |
| `finished` | `pyqtSignal(str)` | Emitted with result string on completion |
| `_dialog` | `_SendDialog` | Reference for building args |
| `_send_fn` | `Callable` | Bound method `editor._send_with_sendmail` |

**run()**: Installs `_LogCapture` handler that emits `log_line` signal per record; calls `_send_fn(_dialog)`; emits `finished(result)`. On exception: emits `finished(f"ERROR: {exc}")`.

**Thread safety**: All UI updates via Qt signal queued connections only. No direct widget access from `run()`.

---

### AnchorBlot (JS, `editor.html`)

| Attribute | Before | After |
|---|---|---|
| DOM attribute written | `data-anchor-id` | `id` |
| DOM attribute read | `data-anchor-id` | `id` |

No Python entity change — Python `_spans_to_anchors` / `_anchors_to_spans` already use `id`.

---

### Anchor name sanitization

Function: `EditorWindow._sanitize_anchor_name(name: str) -> str`

Rules:
1. Lowercase
2. Strip leading/trailing whitespace
3. Replace internal spaces with `-`
4. Remove chars not in `[a-z0-9_-]`
5. Strip leading hyphens/underscores
6. Return empty string if result is empty (caller skips insert)

---

## State Diagram: Send Workflow

```
[Editor: user clicks Send]
        ↓
[_menu_send: save if dirty, create _SendDialog(test=True, locked)]
        ↓
[_SendDialog.show()]  ← test checkbox checked + disabled
        ↓ user clicks Send
[_on_send_dialog_send]
        ↓
[_SessionLogDialog opens immediately (empty)]
[_SendWorker starts in background]
        ↓ log lines stream via signal
[append_log() called on each line]
        ↓ worker.finished signal
[_on_send_finished(result)]
        ↓
    is_test=True?
    ├─ Yes → _SessionLogDialog.set_complete(True, True)
    │         → QMessageBox "Test received?" 
    │         ├─ Yes → _unlock_test_mode(), uncheck test_check
    │         └─ No  → do nothing (test mode stays)
    │         → enable Close
    └─ No  → _SessionLogDialog.set_complete(success, False)
              → QMessageBox "Send complete. OK?"
              → enable Close; Send button re-enabled; dialog stays open
```
