# Quickstart: Editor UI Fixes & Send Workflow

## What's changing

Four surgical fixes to `src/editor.py` and `src/editor_assets/editor.html`. No new files beyond test file.

## Files to edit

| File | What changes |
|---|---|
| `src/editor_assets/editor.html` | Fix `data-anchor-id` → `id` in `AnchorBlot` |
| `src/editor.py` | Fix `_menu_insert_link`, add `_sanitize_anchor_name`, add `_HtmlSourceDialog`, extend `_SessionLogDialog`, add `_SendWorker`, refactor `_on_send_dialog_send` |

## Fix order (dependency-safe)

1. **editor.html** — AnchorBlot attribute fix (isolated, no Python deps)
2. **_menu_insert_link** — one-liner replace with `_run_js("handleLinkInsert()")`; verify `handleLinkInsert` is in global scope in `editor.html`
3. **_sanitize_anchor_name + _menu_insert_anchor** — static method + one-line call
4. **_HtmlSourceDialog** — new class, add View menu action
5. **_SessionLogDialog** — add signal, `closeEvent` guard, `set_complete()`
6. **_SendWorker** — new `QThread` subclass
7. **_on_send_dialog_send** — refactor to use worker + log dialog

## Running tests

```bash
pytest tests/ -v -k "editor"
```

## Manual verification checklist

- [ ] Insert Hyperlink via Format menu → dialog pre-fills selected text → `<a href>` inserted
- [ ] Insert Anchor "my section" → saved HTML has `<a id="my-section">` (not `data-anchor-id`)
- [ ] View HTML Source → dialog opens, shows full HTML, Copy button works
- [ ] Click Send → Send dialog opens with Test locked → click Send → log dialog opens immediately → log lines appear → completion message → confirm → test unlocked
- [ ] Second send (test unchecked) → log dialog → confirm → dialog stays open
