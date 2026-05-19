# SPEC-001 — WYSIWYG HTML Editor

| Field | Value |
|---|---|
| Spec ID | SPEC-001 |
| Status | Implemented (rev 6) |
| Feature | WYSIWYG Newsletter Editor |
| Module | `editor.py` |
| Author | xmayeur |
| Date | 2026-04-26 |
| Rev 1 | 2026-04-26 — Initial implementation |
| Rev 2 | 2026-04-26 — Added table management, image resizing, CSS stylesheet |
| Rev 3 | 2026-04-27 — Inline local images on open; background CSS fix; HR blot; vertical alignment |
| Rev 4 | 2026-04-27 — Valign as select dropdown; images in table cells; blank paragraph collapse; named anchors |
| Rev 5 | 2026-04-27 — Fix valign dropdown hidden by Quill CSS; fix anchor class (ql- → editor-); wrap td images in p on load |
| Rev 6 | 2026-04-28 — Preserve fragment-only and relative hyperlinks for local anchors; local anchor URLs no longer normalize to about:blank |

---

## 1. Overview

sendMail is a CLI bulk-email tool that consumes `.md` and `.html` files to compose newsletter campaigns. Prior to this feature, users had to write those source files in an external text editor with no WYSIWYG preview.

This spec describes the design, analysis, and implementation of a dedicated WYSIWYG editor that lets users compose or edit newsletters visually, then save them as `.html` ready for immediate use with sendMail.

---

## 2. Requirements

### 2.1 Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | The editor shall open a blank document |
| FR-02 | The editor shall open an existing `.md` file |
| FR-03 | The editor shall open an existing `.html` file |
| FR-04 | The editor shall open the project's default newsletter template (`data/template.md`) |
| FR-05 | The editor shall support character formatting: bold, italic, underline, strikethrough |
| FR-06 | The editor shall support paragraph styles: H1–H6, normal, blockquote, code block |
| FR-07 | The editor shall support paragraph alignment: left, center, right, justify |
| FR-08 | The editor shall support ordered and unordered lists with indent/outdent |
| FR-09 | The editor shall support inserting local images embedded as base64 data URIs |
| FR-10 | The editor shall support inserting hyperlinks with a URL and display text |
| FR-11 | The editor shall support inserting horizontal rules |
| FR-12 | The editor shall save output as `.html` (full HTML document) |
| FR-13 | The saved HTML shall contain the current editor content, embedded styles, and sendMail-ready markup |
| FR-14 | The editor shall clear the dirty state after a successful save |
| FR-15 | The editor shall warn about unsaved changes before closing, opening, or starting a new document |
| FR-16 | The editor shall be launchable as a standalone script with an optional file argument |
| FR-17 | The editor shall support inserting tables via a rows × columns dialog |
| FR-18 | The editor shall support inserting and deleting rows and columns in an existing table |
| FR-19 | The editor shall support deleting an entire table |
| FR-20 | The editor shall allow resizing images via a floating slider toolbar (10–100% of container width, with 25/50/75/100% presets) |
| FR-21 | The editor shall allow selecting a CSS file to apply live styling to the editing canvas |
| FR-22 | The selected CSS file shall be embedded in the saved `.html` output in place of the default stylesheet |
| FR-23 | The applied CSS shall be re-injected after every page reload (open file, new document) |
| FR-24 | On file open, local `<img src="path">` references shall be converted to base64 data URIs so images are visible in the editor canvas |
| FR-25 | The background colour declared in a user-applied CSS stylesheet shall be applied to the editing canvas |
| FR-26 | The editor shall support inserting a horizontal rule via a toolbar button and the Insert menu |
| FR-27 | The editor shall support setting vertical alignment (top / middle / bottom) on the current paragraph or table cell, via toolbar buttons and the Format / Table menus |
| FR-28 | The vertical alignment control shall be a select dropdown positioned adjacent to the horizontal alignment select in the toolbar |
| FR-29 | Images inside table cells shall be displayed correctly in the editor canvas |
| FR-30 | On file open, runs of more than 2 consecutive empty paragraphs shall be collapsed to exactly 2 |
| FR-31 | The editor shall support inserting named anchors (bookmarks) via Insert → Insert Anchor; existing anchors (`<a id="...">`) in opened files shall be preserved and shown as ⚓ markers |
| FR-32 | Links to named anchors (`#anchor-name`) and other local relative targets shall be creatable via the existing hyperlink dialog and preserved in saved HTML |

### 2.2 Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | The editor must **not** be imported by `sendMail.py` — the CLI must remain importable without a display server (for CI and headless environments) |
| NFR-02 | The editor must run on macOS, Windows, and Linux (matching CI matrix) |
| NFR-03 | Unit tests must run headlessly without a Qt display server |
| NFR-04 | Bundled JS/CSS assets must work offline (no CDN dependency at runtime) |
| NFR-05 | The saved HTML must not contain the unfilled `{_CSP_IMG_DOMAIN}` placeholder present in `sendMail.md2html()` |
| NFR-06 | Unicode characters (e.g. `☞`) must be preserved verbatim in saved HTML output |

### 2.3 Out of scope

- Real-time collaboration
- Email preview (email client rendering differences)
- Spell check
- Find & Replace
- Launching the editor from within `sendMail.py` via a `--edit` flag (documented as a future option using `subprocess.run`)

---

## 3. Technology Analysis

### 3.1 GUI framework options considered

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **PyQt6 + QWebEngineView** | Native shell, full Chromium, robust PyInstaller support | Large bundle (~80–150 MB with WebEngine) | **Selected** |
| PyQt6 + QTextEdit (built-in rich text) | No WebEngine dependency | Limited HTML/CSS support; poor for newsletter-quality editing | Rejected |
| tkinter + tkinterweb | Stdlib, lightweight | Very limited HTML rendering; not suitable for WYSIWYG | Rejected |
| pywebview + JS editor | Lightweight, uses OS WebView | No native menus/file dialogs; complex IPC | Rejected |
| wxPython + wx.html2.WebView | Native WebView | Harder to install; less community | Rejected |
| Electron / standalone browser | Full web platform | Requires Node.js; too heavyweight | Rejected |

**Decision rationale**: PyQt6 + QWebEngineView provides native menus, native file dialogs, native status bar, and a full Chromium rendering engine — the only combination that reliably delivers a true WYSIWYG experience for HTML newsletter composition in Python.

### 3.2 WYSIWYG engine options considered

| Option | License | Bundle size | API quality | Verdict |
|---|---|---|---|---|
| **Quill.js v2** | MIT | ~210 KB | Clean, well-documented | **Selected** |
| TinyMCE | GPL/Commercial | ~2.5 MB | Very feature-rich | Rejected (license) |
| CKEditor 5 | GPL v2/Commercial | ~1.5 MB | Excellent | Rejected (license) |
| Summernote | MIT | ~400 KB | Simple, Bootstrap-based | Rejected (Bootstrap dep) |
| ProseMirror | MIT | ~300 KB | Extensible, low-level | Rejected (complex API) |

**Decision rationale**: Quill v2 is MIT-licensed, small (~210 KB), has a clean JS API for setting/getting HTML content (`quill.root.innerHTML`), and supports all required formatting including tables (via optional module). It requires no build toolchain — the distribution bundle is a single JS file.

### 3.3 HTML saving

The editor persists the current HTML body directly as the source of truth for saved newsletters. The save path emits a full HTML document suitable for sendMail, while Markdown conversion remains part of the separate CLI conversion workflow in `sendMail.py`.

### 3.4 Quill table module

Quill v2 ships a built-in `table` module. It is enabled by passing `table: true` in the `modules:` config. The JS API (`quill.getModule('table')`) exposes `insertTable(rows, cols)`, `insertRowAbove/Below()`, `insertColumnLeft/Right()`, `deleteRow()`, `deleteColumn()`, and `deleteTable()`.

The toolbar uses eight plain `<button>` elements (not Quill toolbar buttons) wired to a `tableOp(op, rows, cols)` dispatcher. The "Insert Table" button triggers an async callback to `bridge.request_table_insert()` which opens a Python `_TableDialog`; the remaining seven buttons call `tableOp` directly.

### 3.5 Python ↔ JavaScript bridge

Qt's `QWebChannel` mechanism is used:
- Python registers an `EditorBridge(QObject)` instance with a `QWebChannel`
- The JavaScript side loads `qwebchannel.js` (shipped with Qt) and connects to the bridge
- Quill is initialized **inside** the `QWebChannel` callback to guarantee the bridge is available before any `text-change` event fires
- Content sync from JS to Python is **debounced at 500ms** to avoid calling the bridge on every keystroke
- Python-to-JS calls use `page().runJavaScript(...)` (fire-and-forget for formatting, content injection via `json.dumps()` escaping for safe embedding)

### 3.6 Image insertion

`QWebEngineView` blocks browser-side local file access by default (security sandbox). Quill's built-in image handler (which opens a file input) therefore does not work. The solution:

1. Override Quill's `'image'` toolbar handler with a custom JS function
2. The custom handler calls `bridge.request_image_insert(callback)` — an async Qt slot
3. Python opens a native `QFileDialog.getOpenFileName`
4. The chosen file is read and encoded as a base64 data URI using `sm.file_to_base64()` + `sm.guess_type()` (reused from `sendMail.py`)
5. The data URI is returned to JS as the slot return value, then injected into Quill via `insertEmbed`

---

## 4. Architecture

### 4.1 Component diagram

```
┌──────────────────────────────────────────────────────────┐
│  editor.py                                               │
│                                                          │
│  ┌───────────────────────┐  ┌────────────────────────┐  │
│  │  EditorWindow         │  │  EditorBridge          │  │
│  │  (QMainWindow)        │  │  (QObject)             │  │
│  │                       │  │                        │  │
│  │  • Menus & dialogs    │  │  • on_content_         │  │
│  │  • File open/save     │◄─┤    changed()           │  │
│  │  • Title / dirty      │  │  • request_image_      │  │
│  │    tracking           │  │    insert()            │  │
│  │  • _css_path          │  │  • request_link_       │  │
│  │  • _css_status_label  │  │    insert()            │  │
│  │  • _on_css_changed()  │  │  • request_table_      │  │
│  │  • _menu_table_       │  │    insert()            │  │
│  │    insert()           │  │  • css_changed signal  │  │
│  │  • _menu_apply_css()  │  └────────────────────────┘  │
│  │                       │             ▲                 │
│  │  ┌─────────────────┐  │      QWebChannel             │
│  │  │  QWebEngineView │  │             │                 │
│  │  │                 │  │             │                 │
│  │  │  editor.html    │  │             │                 │
│  │  │  ┌───────────┐  │  │             │                 │
│  │  │  │ Quill.js  │◄─┼──┼─────────────┘                │
│  │  │  │ (+ table  │  │  │                              │
│  │  │  │  module)  │  │  │                              │
│  │  │  └───────────┘  │  │                              │
│  │  └─────────────────┘  │                              │
│  └───────────────────────┘                              │
│                                                          │
│  Dialogs: _LinkDialog, _TableDialog                      │
│                                                          │
│  Uses (no import coupling):                              │
│  • sm.md2html()         sendMail.py                      │
│  • sm.file_to_base64()  sendMail.py                      │
│  • sm.guess_type()      sendMail.py                      │
└──────────────────────────────────────────────────────────┘
```

### 4.2 File structure

```
editor.py                         Main application
editor_assets/
    editor.html                   Quill host page (QWebChannel bootstrap)
    quill.js                      Quill v2 bundled (MIT, ~210 KB)
    quill.snow.css                Quill Snow theme (~24 KB)
    qwebchannel.js                Qt WebChannel client (from Qt install)
editor.spec                       PyInstaller build spec
tests/
    test_editor.py                Unit tests (27 tests, Qt fully mocked)
```

### 4.3 Data flows

#### Opening a `.md` file

```
open_file("data/newsletter.md")
  → sm.md2html(path)                 writes  data/newsletter.html (temp)
  → BeautifulSoup.body.decode_contents()     extract <body> innerHTML
  → os.remove("data/newsletter.html")        delete temp file
  → _load_editor_page(body_html)
      → QWebEngineView.load(editor.html)
      → [loadFinished] → runJavaScript("setContent(<json-escaped-html>)")
                         → quill.root.innerHTML = html
```

#### Saving

```
_save()
  → bridge.get_current_html()               retrieve cached body HTML
  → _write_html_file("{stem}.html", html)   full document + CSS + charset
  → bridge.reset(html)                      clear dirty flag
  → page().runJavaScript("markSaved()")     update JS status indicator
```

#### Inserting an image

```
[Quill toolbar click: image]
  → handleImageInsert() [JS]
      → bridge.request_image_insert(callback) [async Qt slot call]
          → QFileDialog.getOpenFileName()  [Python, native dialog]
          → sm.file_to_base64(path)
          → sm.guess_type(path)
          → return "data:{mime};base64,{b64}"
      → callback(dataUri) [JS]
          → quill.insertEmbed(range.index, 'image', dataUri)
```

#### Resizing an image

```
[Click on image in editor]
  → quill.root 'click' listener  [JS]
      → _showImgToolbar(img)
          → position #img-resize-toolbar above image
          → read img.style.width → set slider value

[Slider input / preset button click]
  → _applyImgWidth(pct) [JS]
      → img.style.width = pct + '%'
      → quill.update(Quill.sources.USER)   → triggers text-change → bridge.on_content_changed
```

#### Inserting a table

```
[Toolbar btn-insert-table click]
  → bridge.request_table_insert(callback) [async Qt slot call]
      → _TableDialog.exec()  [Python, rows/cols spinboxes]
      → return JSON '{"rows":3,"cols":3}'
  → callback(jsonStr) [JS]
      → tableOp('insertTable', rows, cols)
          → quill.getModule('table').insertTable(rows, cols)

[Table menu: Insert Table…]
  → _menu_table_insert() [Python]
      → bridge.request_table_insert()  → same _TableDialog
      → _run_js("tableOp('insertTable', rows, cols)")
```

#### Applying a CSS stylesheet

```
[Format menu: Apply Stylesheet…]
  → _menu_apply_css() [Python]
      → QFileDialog.getOpenFileName()
      → bridge.css_changed.emit(abs_path)

[css_changed signal]
  → _on_css_changed(css_path) [Python]
      → open(css_path).read()
      → _run_js("applyCSS(<json-escaped css>)")
          → document.getElementById('user-css').textContent = cssText  [JS]
      → self._css_path = css_path  (persisted for _write_html_file and page reloads)
      → _css_status_label.setText("CSS: {filename}")
```

---

## 5. Implementation plan

### Phase 1 — Infrastructure
1. Add `PyQt6>=6.7.0`, `PyQt6-WebEngine>=6.7.0`, `html2text>=2024.2.26` to `pyproject.toml` and `requirements.txt`
2. Download Quill v2 JS + CSS from CDN and commit to `editor_assets/`
3. Copy `qwebchannel.js` from Qt install into `editor_assets/`

### Phase 2 — Editor page
1. Write `editor_assets/editor.html` — Quill toolbar, QWebChannel bootstrap, content sync, image/link handlers

### Phase 3 — Python shell
1. Write `EditorBridge` class with all slots
2. Write `EditorWindow.__init__`, `_load_editor_page`, `_inject_initial_content`
3. Implement `_build_menus` (File / Format / Insert)
4. Implement `open_file`, `_md_to_body_html`, `_html_to_body_html`
5. Implement `_save`, `_save_as`, `_write_html_file`, `_write_md_file`
6. Implement `new_document`, `_ask_save_if_dirty`, `closeEvent`

### Phase 4 — Media insertion
1. Implement `request_image_insert` (file dialog → base64 data URI)
2. Implement `_LinkDialog` and `request_link_insert` (URL + text dialog)

### Phase 5 — Testing and packaging
1. Write `tests/test_editor.py` (24 unit tests, all headless)
2. Write `editor.spec` (PyInstaller, separate from sendMail.spec)
3. Update `CLAUDE.md` with editor launch instructions

### Phase 7 — Enhancements (rev 3)
1. Update `_html_to_body_html()` to call `sm.make_html_images_inline()` before extracting body; add `_inline_images_fallback()` for stdlib-only path
2. Register custom `HrBlot` (BlockEmbed) and `VAlignStyle` (Parchment style attributor) before Quill init in `editor.html`
3. Fix `window.applyCSS()` to propagate `body { background-color }` to `#editor-container`
4. Add `window.insertHR()` and `window.setVAlign(align)` global functions in `editor.html`
5. Add HR and vertical-alignment toolbar buttons (with wiring) to `editor.html`
6. Update Insert menu HR action to call `insertHR()`; add Vertical Alignment submenus to Format and Table menus in `editor.py`
7. Add `TestLocalImageInlining`, `TestHrInsertion`, `TestVerticalAlignment` test classes (6 new tests, total 33)

### Phase 6 — Enhancements (rev 2)
1. Add Quill `table: true` module to `editor.html` Quill config
2. Add 8-button table toolbar group and table cell CSS to `editor.html`
3. Add `tableOp` dispatcher and button wiring to `editor.html` JS
4. Add `_TableDialog` class to `editor.py`
5. Add `request_table_insert` slot to `EditorBridge`
6. Add Table menu to `_build_menus` with full row/col/table operations
7. Add floating image resize toolbar HTML + CSS + JS to `editor.html`
8. Add `_css_path`, `css_changed` signal, `_on_css_changed`, `_menu_apply_css` to `editor.py`
9. Update `_inject_initial_content` to re-apply CSS on every page load
10. Update `_write_html_file` to use `self._css_path` when set
11. Add "Apply Stylesheet…" item to Format menu
12. Update `tests/test_editor.py`: `QSpinBox` mock, `_TableDialog` import, `_FakeWindow` fix, new test classes (27 tests total)

---

## 6. Key design decisions and rationale

| Decision | Rationale |
|---|---|
| Editor is **standalone only** (not imported by sendMail.py) | Importing PyQt6 in the CLI process breaks headless CI runners and bloats the PyInstaller CLI binary |
| Both `.md` **and** `.html` saved on every Save | sendMail accepts either format; having both avoids a separate conversion step |
| Images embedded as **base64 data URIs** | Consistent with how `make_html_images_inline()` works; avoids broken image paths when files are moved |
| Quill content read/written via `quill.root.innerHTML` | Quill's Delta format is internal; `innerHTML` gives clean semantic HTML for round-tripping |
| Content synced on **500ms debounce** (not on every keystroke) | Avoids saturating the QWebChannel IPC on fast typists |
| `json.dumps()` used to escape HTML for `runJavaScript` injection | Safer than manual backtick/backslash escaping; handles all Unicode and HTML characters correctly |
| Saved HTML **omits CSP meta tag** | `sendMail.py` line 59: `_CSP_IMG_DOMAIN = "{_CSP_IMG_DOMAIN}"` is an unfilled placeholder; including it would produce an invalid CSP header and block data URI images |
| `html2text` configured with `body_width=0` | The default wraps at 78 chars, breaking Markdown tables and long URLs in the newsletters |
| Table toolbar uses **plain `<button>` elements**, not Quill toolbar buttons | Quill's toolbar system has no built-in table support; plain buttons call `tableOp()` directly and avoid conflicts with Quill's format handlers |
| Image resize is **pure JS** (no Python slots) | Resize is a DOM mutation on the already-embedded `<img>` element; no Python round-trip needed; `quill.update(USER)` triggers the existing debounced content sync |
| **`css_changed` is a Qt signal** on `EditorBridge` | Decouples the file-picker (on `EditorWindow`) from the apply logic; allows future programmatic CSS changes (e.g. from a template picker) without calling UI code |
| **`_css_path` persisted on `EditorWindow`** | Required to re-inject CSS after every `loadFinished` page reload (Quill reinitializes the iframe DOM on each load, wiping any previously applied styles) |
| User CSS **replaces** default `css/styles.css` in saved HTML | Prevents style conflicts; the user's intent is to style the newsletter with their own CSS, not layer it on top of defaults |
| **Local images inlined as base64 on open** | `sm.make_html_images_inline()` is called in `_html_to_body_html()` before content is pushed into Quill. QWebEngineView's sandbox blocks `file://` src access from `innerHTML`, so all local images must become data URIs. A stdlib fallback (`base64` + `mimetypes`) is used when `sendMail` is unavailable. |
| **Background CSS propagated explicitly** | `applyCSS()` parses the user CSS for a `body { background[-color] }` rule with a regex and sets `#editor-container.style.background` directly. Injecting the CSS into `<style id="user-css">` alone cannot override the container's hardcoded `background: white` because inline styles always win. |
| **Custom HR blot registered before Quill init** | Quill v2 has no built-in `'hr'` blot. A `BlockEmbed` subclass named `'hr'` with `tagName = 'hr'` is registered so `insertEmbed('hr', true)` produces a real `<hr>` element. The matching CSS (`.ql-editor hr`) gives it visible styling inside the canvas. |
| **Vertical alignment via direct DOM mutation** | `setVAlign(align)` walks from the cursor leaf to the nearest block element (`TD`, `TH`, `P`, `LI`, headings, `BLOCKQUOTE`) and sets `style.verticalAlign` directly, then calls `quill.update(USER)`. No Parchment registration needed; avoids the Parchment API variability across Quill v2 builds. |
| **Vertical alignment select next to horizontal** | The valign control is a plain `<select id="sel-valign">` placed inside the same `ql-formats` span as `ql-align`. After applying, the select resets to the placeholder so the same value can be re-applied. |
| **Named anchors stored as `<span class="editor-anchor">` in the editor** | Quill's link blot already owns `<a>`. A second blot for `<a>` would override it and break links. The anchor blot uses `<span class="editor-anchor" data-anchor-id="name">⚓</span>` using the `editor-anchor` class (not `ql-anchor` — Quill owns the `ql-*` namespace and may strip those classes). Python converts `<a id="name">` → anchor spans on load and back on save. |
| **Valign select must be outside `ql-formats`** | Quill's Snow toolbar init hides ALL `<select>` elements inside `.ql-formats` (replacing them with custom pickers). `#sel-valign` is in its own plain `<span id="valign-group">` immediately after the alignment span to avoid being hidden. |
| **Images in `<td>` wrapped in `<p>` before sending to Quill** | Quill's table module expects block-level content (paragraphs) inside cells. A bare `<img>` directly in `<td>` is dropped during Quill's DOM normalisation. `_wrap_td_images()` pre-processes the body HTML to wrap such images in `<p>` tags. |
| **Blank paragraph collapse on open** | `_collapse_blank_paragraphs()` uses a regex to reduce runs of 3+ consecutive empty `<p>` tags to exactly 2, preventing oversized gaps from pasted or generated content. |

---

## 7. PyInstaller packaging notes

`editor.spec` (separate from `sendMail.spec`) handles:

- **`editor_assets/`** bundled as `datas`
- **Chromium resources** bundled via `collect_data_files('PyQt6.QtWebEngineCore')` — mandatory; omitting these causes silent QWebEngine failures at runtime
- **`hiddenimports`**: `PyQt6.QtWebEngineWidgets`, `PyQt6.QtWebEngineCore`, `PyQt6.QtWebChannel`, `PyQt6.sip`
- **macOS**: `BUNDLE` target produces `.app` (required by Chromium's helper process architecture)
- **PyInstaller path resolution**: `editor.py` uses `sys._MEIPASS` when `sys.frozen` is set

Expected bundle size: **80–150 MB** (dominated by Chromium engine).

---

## 8. Testing strategy

All 47 unit tests in `tests/test_editor.py` run headlessly. Qt is fully mocked before the `editor` module is imported:

```python
for mod in ["PyQt6", "PyQt6.QtCore", "PyQt6.QtWidgets",
            "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebChannel"]:
    sys.modules[mod] = MagicMock()
```

**Critical mock details:**
- `@pyqtSlot` mock uses `inspect.isfunction()` to distinguish `@pyqtSlot(str)` (type arg) from `@pyqtSlot` (bare decorator). Using `callable()` incorrectly matches Python built-in types like `str`.
- `QObject`, `QMainWindow`, `QDialog` must be **real Python classes** (not `MagicMock()` instances). Mock instances cannot be subclassed reliably; `_`-prefixed attribute access on Mock raises `AttributeError`.
- `QSpinBox` is mocked as `MagicMock()` (no subclassing needed — `_TableDialog` instantiates it, never subclasses it).
- `TestHtmlFileWriter._write` uses a `_FakeWindow` stub object (with `_css_path = None`) instead of `None` as `self`, because `_write_html_file` now accesses `self._css_path`.

**Test classes:**

| Class | Tests | Coverage |
|---|---|---|
| `TestEditorBridgeContentTracking` | 8 | dirty flag, HTML caching, signal emission, reset |
| `TestEditorBridgeImageInsert` | 4 | data URI generation, cancel, exception fallback, SM-unavailable fallback |
| `TestEditorBridgeLinkInsert` | 3 | JSON output, cancel, blank URL |
| `TestHtmlToMarkdown` | 5 | headings, bold, links, Unicode, no line-wrap |
| `TestHtmlFileWriter` | 5 | charset, body HTML, no CSP placeholder, valid HTML structure, user CSS override |
| `TestEditorBridgeTableInsert` | 2 | JSON output on confirm, empty on cancel |
| `TestLocalImageInlining` | 2 | Local img inlined via sm; fallback when sm unavailable |
| `TestHrInsertion` | 1 | HR menu item fires `insertHR()` via `_run_js` |
| `TestVerticalAlignment` | 3 | `setVAlign('top'/'middle'/'bottom')` fired via `_run_js` |
| `TestBlankParagraphCollapse` | 5 | 3/5 empty paragraphs collapsed; 2 preserved; content paragraphs unaffected; mixed content |
| `TestAnchorHandling` | 5 | `<a id>` → span on load; href links not affected; span → `<a id>` on save; multiple anchors; round-trip |
| `TestTdImageWrapping` | 4 | bare img in td wrapped; already-wrapped not doubled; text unaffected; multiple cells |

GUI integration tests (requiring a real display) are excluded from CI via `@pytest.mark.gui` and `pytest -m "not gui"`.

---

## 9. Usage

```bash
# Launch editor
python editor.py                      # blank document
python editor.py data/template.md     # open newsletter template
python editor.py data/20260420.md     # edit existing newsletter

# Then send with sendMail
python sendMail.py --profile cambristi data/20260420.html
```

---

## 10. Future extensions

| Extension | Notes |
|---|---|
| `--edit` flag in sendMail | Safe pattern: `subprocess.run([sys.executable, "editor.py", args.file[0]])` — keeps Qt out of the CLI process |
| Font family / font size toolbar | Add `<select class="ql-font">` and `<select class="ql-size">` to `editor.html` toolbar |
| Spell check | QWebEngineView supports `page().settings().setAttribute(QWebEngineSettings.WebAttribute.SpellCheckEnabled, True)` |
| Template picker dialog | List all `data/*.md` files in a dialog instead of always defaulting to `template.md` |
| Find & Replace | QWebEnginePage provides `findText()` for forward/backward search; replace requires JS DOM manipulation |
| Table cell merge | Quill v2's table module does not yet support `colspan`/`rowspan`; requires a custom blot or upgrade |
| CSS preset dropdown | Status-bar button cycling through `css/*.css` files as quick presets, instead of a file picker each time |
