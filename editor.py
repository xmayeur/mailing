#!/usr/bin/env python
# coding: utf-8
"""
WYSIWYG HTML editor for composing sendMail newsletters.

Usage:
    python editor.py                       # blank editor
    python editor.py data/template.md      # open existing markdown file
    python editor.py data/newsletter.html  # open existing HTML file

The editor saves output as both .md and .html, ready for sendMail:
    python sendMail.py --profile cambristi data/newsletter.html
"""

import json
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# PyInstaller-safe asset path resolution
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _BASE = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BASE = Path(__file__).parent

ASSETS_DIR = _BASE / "editor_assets"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("editor")

# ---------------------------------------------------------------------------
# Qt imports
# ---------------------------------------------------------------------------
from PyQt6.QtCore import QByteArray, QObject, QUrl, pyqtSignal, pyqtSlot  # noqa: E402
from PyQt6.QtGui import QIcon, QPixmap  # noqa: E402
from PyQt6.QtWebChannel import QWebChannel  # noqa: E402
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QStatusBar,
)

# ---------------------------------------------------------------------------
# sendMail utility imports (reuse existing functions)
# ---------------------------------------------------------------------------
try:
    import sendMail as sm  # noqa: E402  (import after path setup)

    _SM_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    log.warning("sendMail module not importable: %s — MD import disabled", exc)
    _SM_AVAILABLE = False


# ---------------------------------------------------------------------------
# Table-operation SVG icons (16×16, Excel / LibreOffice style)
# ---------------------------------------------------------------------------
_SVG_INSERT_TABLE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    '<rect x="1" y="3" width="14" height="12" fill="#E3F2FD" stroke="#1565C0" stroke-width="1.2"/>'
    '<rect x="1" y="3" width="14" height="3.5" fill="#1565C0"/>'
    '<line x1="5.7" y1="3" x2="5.7" y2="15" stroke="#1565C0" stroke-width="0.9"/>'
    '<line x1="10.3" y1="3" x2="10.3" y2="15" stroke="#1565C0" stroke-width="0.9"/>'
    '<line x1="1" y1="10.5" x2="15" y2="10.5" stroke="#1565C0" stroke-width="0.9"/>'
    '</svg>'
)
def _svg_icon(svg: str) -> QIcon:
    """Create a QIcon from an SVG string; returns an empty icon if the SVG plugin is unavailable."""
    pix = QPixmap()
    pix.loadFromData(QByteArray(svg.encode()), "SVG")
    return QIcon(pix)


# ---------------------------------------------------------------------------
# Link insertion dialog
# ---------------------------------------------------------------------------
class _LinkDialog(QDialog):
    """Small dialog asking for a URL and optional display text."""

    def __init__(self, parent=None, selected_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Hyperlink")
        self.setMinimumWidth(360)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("https://example.com")
        layout.addRow("URL:", self.url_input)

        self.text_input = QLineEdit(self)
        self.text_input.setPlaceholderText("Display text (optional)")
        if selected_text:
            self.text_input.setText(selected_text)
        layout.addRow("Text:", self.text_input)

        hint = QLabel("Leave Text blank to use the URL as display text.", self)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow("", hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.url_input.returnPressed.connect(self.text_input.setFocus)
        self.text_input.returnPressed.connect(self.accept)

    def get_url(self) -> str:
        return self.url_input.text().strip()

    def get_text(self) -> str:
        return self.text_input.text().strip()


# ---------------------------------------------------------------------------
# Anchor insertion dialog
# ---------------------------------------------------------------------------
class _AnchorDialog(QDialog):
    """Small dialog asking for a named anchor / bookmark identifier."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Anchor")
        self.setMinimumWidth(300)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("e.g. section1, top, intro")
        layout.addRow("Anchor name:", self.name_input)

        hint = QLabel("Use this name as #anchor-name in hyperlinks to jump here.", self)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow("", hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.name_input.returnPressed.connect(self.accept)

    def get_name(self) -> str:
        return self.name_input.text().strip().replace(" ", "-")


# ---------------------------------------------------------------------------
# Table insertion dialog
# ---------------------------------------------------------------------------
class _TableDialog(QDialog):
    """Dialog asking for table dimensions (rows × columns)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Table")
        self.setMinimumWidth(260)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)

        self.rows_spin = QSpinBox(self)
        self.rows_spin.setRange(1, 20)
        self.rows_spin.setValue(3)
        layout.addRow("Rows:", self.rows_spin)

        self.cols_spin = QSpinBox(self)
        self.cols_spin.setRange(1, 20)
        self.cols_spin.setValue(3)
        layout.addRow("Columns:", self.cols_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_rows(self) -> int:
        return self.rows_spin.value()

    def get_cols(self) -> int:
        return self.cols_spin.value()


# ---------------------------------------------------------------------------
# JS ↔ Python bridge
# ---------------------------------------------------------------------------
class EditorBridge(QObject):
    """
    Registered with QWebChannel as "bridge".
    Provides slots callable from Quill's JavaScript context.
    """

    dirty_changed = pyqtSignal(bool)
    css_changed = pyqtSignal(str)   # emits absolute CSS file path when user selects a stylesheet

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_html: str = ""
        self._dirty: bool = False

    # ------------------------------------------------------------------
    # Slots called from JavaScript
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def on_content_changed(self, html: str) -> None:
        """Receives the editor's current HTML after every edit (debounced 500ms)."""
        self._current_html = html
        if not self._dirty:
            self._dirty = True
            self.dirty_changed.emit(True)

    @pyqtSlot(result=str)
    def request_image_insert(self) -> str:
        """
        Opens a file dialog and returns a base64 data URI for the chosen image.
        Returns "" if the user cancels.
        """
        parent_widget = self.parent()
        path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Insert Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.svg *.bmp *.tiff)",
        )
        if not path:
            return ""
        try:
            if _SM_AVAILABLE:
                b64 = sm.file_to_base64(path)
                mimetype = sm.guess_type(path) or "image/png"
            else:
                import base64
                import mimetypes

                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                mimetype = mimetypes.guess_type(path)[0] or "image/png"
            return f"data:{mimetype};base64,{b64}"
        except Exception as exc:
            log.error("Image insert failed: %s", exc)
            return ""

    @pyqtSlot(str, result=str)
    def request_link_insert(self, selected_text: str) -> str:
        """
        Opens a link dialog pre-filled with *selected_text*.
        Returns a JSON string {"url": "...", "text": "..."} on confirm,
        or "" on cancel.
        """
        parent_widget = self.parent()
        dialog = _LinkDialog(parent_widget, selected_text=selected_text)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return ""
        url = dialog.get_url()
        if not url:
            return ""
        return json.dumps({"url": url, "text": dialog.get_text()})

    @pyqtSlot(result=str)
    def request_table_insert(self) -> str:
        """
        Opens a dialog asking for table dimensions.
        Returns JSON string {"rows": n, "cols": m} on confirm, or "" on cancel.
        """
        parent_widget = self.parent()
        dialog = _TableDialog(parent_widget)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return ""
        return json.dumps({"rows": dialog.get_rows(), "cols": dialog.get_cols()})

    @pyqtSlot(str)
    def log_js_error(self, msg: str) -> None:
        """Receives JS-side errors forwarded via window.onerror."""
        log.warning("JS: %s", msg)

    # ------------------------------------------------------------------
    # Python-side accessors
    # ------------------------------------------------------------------

    def get_current_html(self) -> str:
        """Returns the last HTML content received from the editor."""
        return self._current_html

    def reset(self, html: str = "") -> None:
        """Clears the dirty flag and updates cached HTML (called after save)."""
        self._current_html = html
        self._dirty = False
        self.dirty_changed.emit(False)

    @property
    def is_dirty(self) -> bool:
        return self._dirty


# ---------------------------------------------------------------------------
# Main editor window
# ---------------------------------------------------------------------------
class EditorWindow(QMainWindow):
    """Main WYSIWYG editor window."""

    def __init__(self, file_path: str | None = None) -> None:
        super().__init__()
        self._file_path: str | None = None
        self._css_path: str | None = None   # user-selected CSS stylesheet
        self._load_finished_connected = False

        # Web engine view
        self._view = QWebEngineView(self)
        self.setCentralWidget(self._view)

        # Web channel + bridge
        self._channel = QWebChannel(self)
        self._bridge = EditorBridge(parent=self)
        self._channel.registerObject("bridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        # Connect signals
        self._bridge.dirty_changed.connect(self._on_dirty_changed)
        self._bridge.css_changed.connect(self._on_css_changed)

        # Build menus and status bar
        self._build_menus()
        self.setStatusBar(QStatusBar(self))
        self._css_status_label = QLabel("")
        self.statusBar().addPermanentWidget(self._css_status_label)

        # Window setup
        self.setMinimumSize(960, 720)
        self._update_title()

        # Open file or blank editor
        if file_path:
            self.open_file(file_path)
        else:
            self._load_editor_page("")

    # ------------------------------------------------------------------
    # Page loading
    # ------------------------------------------------------------------

    def _load_editor_page(self, initial_html: str) -> None:
        """Load editor.html into the WebEngineView, then inject initial content."""
        editor_url = QUrl.fromLocalFile(str(ASSETS_DIR / "editor.html"))

        # Disconnect any previously connected loadFinished handler
        if self._load_finished_connected:
            try:
                self._view.loadFinished.disconnect()
            except Exception:
                pass
            self._load_finished_connected = False

        def _on_load_finished(ok: bool) -> None:
            # Disconnect self to ensure it fires only once
            try:
                self._view.loadFinished.disconnect(_on_load_finished)
            except Exception:
                pass
            if ok:
                self._inject_initial_content(initial_html)
            else:
                log.error("Failed to load editor page")

        self._view.loadFinished.connect(_on_load_finished)
        self._load_finished_connected = True
        self._view.load(editor_url)

    def _inject_initial_content(self, html: str) -> None:
        """Push HTML into the Quill editor via runJavaScript."""
        # json.dumps produces a valid JS string literal (handles all escaping)
        safe_js_string = json.dumps(html)
        self._view.page().runJavaScript(f"setContent({safe_js_string})")
        # Re-apply user CSS after each page load (page reload clears injected styles)
        if self._css_path:
            try:
                with open(self._css_path, "r", encoding="utf-8") as f:
                    css_text = f.read()
                self._run_js(f"applyCSS({json.dumps(css_text)})")
            except Exception:
                pass  # non-fatal; CSS will not be shown but content is safe

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def open_file(self, path: str) -> None:
        """Open a .md or .html file into the editor."""
        path = os.path.abspath(path)
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{path}")
            return

        ext = Path(path).suffix.lower()
        if ext == ".md":
            body_html = self._md_to_body_html(path)
        elif ext in (".html", ".htm"):
            body_html = self._html_to_body_html(path)
        else:
            QMessageBox.warning(
                self, "Unsupported File", f"Unsupported file type: {ext}\nOpen .md or .html files."
            )
            return

        self._file_path = path
        self._bridge.reset(body_html)
        self._update_title()
        self._load_editor_page(body_html)

    def _md_to_body_html(self, md_path: str) -> str:
        """Convert a .md file to an HTML body string (uses sm.md2html)."""
        if not _SM_AVAILABLE:
            QMessageBox.warning(
                self, "sendMail Not Available", "Cannot import sendMail module — MD conversion disabled."
            )
            return ""

        html_path = None
        try:
            # md2html writes {stem}.html next to the .md file
            html_path = sm.md2html(md_path, styles=None, embed_styles=False)
            if not html_path or not os.path.exists(html_path):
                log.error("md2html produced no output for: %s", md_path)
                return ""
            return self._html_to_body_html(html_path)
        except Exception as exc:
            log.error("MD conversion failed: %s", exc)
            return ""
        finally:
            # Delete the transient .html file; .md is the canonical source
            if html_path and os.path.exists(html_path) and html_path != md_path:
                try:
                    os.remove(html_path)
                except OSError:
                    pass

    def _html_to_body_html(self, html_path: str) -> str:
        """Extract the <body> inner HTML, inlining images and normalising anchors/blank lines."""
        try:
            from bs4 import BeautifulSoup

            if _SM_AVAILABLE:
                content = sm.make_html_images_inline(html_path)
            else:
                content = self._inline_images_fallback(html_path)
            soup = BeautifulSoup(content, "html.parser")
            body = soup.find("body")
            result = body.decode_contents() if body else content
            result = self._collapse_blank_paragraphs(result)
            result = self._anchors_to_spans(result)
            return result
        except Exception as exc:
            log.error("HTML read failed: %s", exc)
            return ""

    @staticmethod
    def _collapse_blank_paragraphs(html: str) -> str:
        """Collapse runs of 3+ consecutive empty paragraphs to exactly 2."""
        import re
        _EMPTY_P = r'<p(?:[^>]*)?>(?:\s*<br\s*/?>)?\s*</p>'
        return re.sub(
            rf'({_EMPTY_P})\s*(?:{_EMPTY_P}\s*){{2,}}',
            r'\1\1',
            html,
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _anchors_to_spans(html: str) -> str:
        """Convert bare <a id="name"> tags (no href) to ql-anchor spans for Quill."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            if a.get("href"):
                continue
            anchor_id = a.get("id") or a.get("name")
            if not anchor_id:
                continue
            span = soup.new_tag(
                "span",
                **{"class": "ql-anchor", "data-anchor-id": anchor_id,
                   "title": f"Anchor: {anchor_id}"},
            )
            span.string = "⚓"  # ⚓
            a.replace_with(span)
        # If html.parser wrapped the fragment in html/body, extract body content only
        body = soup.find("body")
        return body.decode_contents() if body else str(soup)

    @staticmethod
    def _spans_to_anchors(html: str) -> str:
        """Convert ql-anchor spans back to <a id> tags before saving."""
        import re
        def _replace(m: re.Match) -> str:
            aid = m.group(1)
            return f'<a id="{aid}" name="{aid}"></a>'
        return re.sub(
            r'<span[^>]+class="ql-anchor"[^>]+data-anchor-id="([^"]+)"[^>]*>⚓</span>',
            _replace,
            html,
        )

    def _inline_images_fallback(self, html_path: str) -> str:
        """Inline local <img src> as base64 data URIs without the sendMail module."""
        import base64
        import mimetypes
        import re

        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        base_dir = os.path.dirname(os.path.abspath(html_path))

        def _replace(m: re.Match) -> str:
            src = m.group(1)
            if src.startswith("data:") or src.startswith("http"):
                return m.group(0)
            img_path = os.path.join(base_dir, src) if not os.path.isabs(src) else src
            try:
                mime = mimetypes.guess_type(img_path)[0] or "image/png"
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                return f'src="data:{mime};base64,{b64}"'
            except OSError:
                return m.group(0)

        return re.sub(r'src="([^"]*)"', _replace, content)

    def new_document(self) -> None:
        """Clear the editor and start a new blank document."""
        if not self._ask_save_if_dirty():
            return
        self._file_path = None
        self._bridge.reset("")
        self._update_title()
        self._load_editor_page("")

    def _save(self) -> bool:
        """Save current content as both .md and .html. Returns True on success."""
        if not self._file_path:
            return self._save_as()

        body_html = self._spans_to_anchors(self._bridge.get_current_html())
        stem = Path(self._file_path).with_suffix("")
        html_path = str(stem) + ".html"
        md_path = str(stem) + ".md"

        try:
            self._write_html_file(html_path, body_html)
            self._write_md_file(md_path, body_html)
            self._bridge.reset(body_html)
            self._update_title()
            self._view.page().runJavaScript("markSaved()")
            self.statusBar().showMessage(f"Saved: {html_path}  +  {md_path}", 4000)
            log.info("Saved HTML: %s  MD: %s", html_path, md_path)
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{exc}")
            log.error("Save failed: %s", exc)
            return False

    def _save_as(self) -> bool:
        """Prompt for a filename then save. Returns True on success."""
        initial_dir = str(Path(self._file_path).parent) if self._file_path else "data"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            initial_dir,
            "Markdown (*.md);;HTML (*.html);;All Files (*)",
        )
        if not path:
            return False
        # Normalize to .md stem — we always save both formats
        self._file_path = str(Path(path).with_suffix(".md"))
        return self._save()

    def _write_html_file(self, path: str, body_html: str) -> None:
        """Write a complete HTML document file from body HTML."""
        # Use user-selected CSS if set; otherwise fall back to project default
        css_source = Path(self._css_path) if self._css_path else (_BASE / "css" / "styles.css")
        if css_source.exists():
            with open(css_source, "r", encoding="utf-8") as f:
                css_content = f.read()
            style_block = f"<style>\n{css_content}\n</style>"
        else:
            style_block = """<style>
  body { background-color: PapayaWhip; font-family: Georgia, serif; }
  h1   { color: red; text-align: center; }
  h2   { color: darkred; padding-left: 20px; }
  h3, h4, h5 { padding-left: 20px; }
  p, b { color: DarkSlateGray; padding-left: 50px; }
  ul   { color: DarkSlateGray; padding-left: 80px; }
  img  { max-width: 860px; height: auto; display: block; margin: 0 auto; }
</style>"""

        html_document = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  {style_block}
</head>
<body>
{body_html}
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_document)

    def _write_md_file(self, path: str, body_html: str) -> None:
        """Convert body HTML to Markdown and write to file."""
        import html2text

        h = html2text.HTML2Text()
        h.body_width = 0          # no line-wrapping (breaks tables and long URLs)
        h.protect_links = True
        h.wrap_links = False
        h.unicode_snob = True     # keep Unicode chars like ☞ verbatim
        h.images_as_html = False  # use Markdown image syntax ![alt](src)
        markdown_str = h.handle(body_html)
        with open(path, "w", encoding="utf-8") as f:
            f.write(markdown_str)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def _build_menus(self) -> None:
        menubar = self.menuBar()
        assert menubar is not None

        # --- File menu ---
        file_menu = menubar.addMenu("&File")
        assert file_menu is not None

        new_action = file_menu.addAction("&New")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_document)

        open_action = file_menu.addAction("&Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._menu_open)

        file_menu.addSeparator()

        save_action = file_menu.addAction("&Save")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save)
        self._save_action = save_action

        save_as_action = file_menu.addAction("Save &As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_as)

        file_menu.addSeparator()

        template_action = file_menu.addAction("Open &Template")
        template_action.setToolTip("Open data/template.md")
        template_action.triggered.connect(self._open_template)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # --- Format menu ---
        fmt_menu = menubar.addMenu("F&ormat")
        assert fmt_menu is not None

        bold_action = fmt_menu.addAction("&Bold")
        bold_action.setShortcut("Ctrl+B")
        bold_action.triggered.connect(lambda: self._run_js("quill.format('bold', !quill.getFormat().bold)"))

        italic_action = fmt_menu.addAction("&Italic")
        italic_action.setShortcut("Ctrl+I")
        italic_action.triggered.connect(lambda: self._run_js("quill.format('italic', !quill.getFormat().italic)"))

        underline_action = fmt_menu.addAction("&Underline")
        underline_action.setShortcut("Ctrl+U")
        underline_action.triggered.connect(lambda: self._run_js("quill.format('underline', !quill.getFormat().underline)"))

        strike_action = fmt_menu.addAction("&Strikethrough")
        strike_action.setShortcut("Ctrl+Shift+X")
        strike_action.triggered.connect(lambda: self._run_js("quill.format('strike', !quill.getFormat().strike)"))

        fmt_menu.addSeparator()

        for level in (1, 2, 3):
            h_action = fmt_menu.addAction(f"Heading &{level}")
            h_action.triggered.connect(
                lambda checked=False, lvl=level: self._run_js(f"quill.format('header', {lvl})")
            )

        normal_action = fmt_menu.addAction("&Normal Paragraph")
        normal_action.triggered.connect(lambda: self._run_js("quill.format('header', false)"))

        fmt_menu.addSeparator()

        clean_action = fmt_menu.addAction("&Clear Formatting")
        clean_action.triggered.connect(lambda: self._run_js("quill.format('clean')"))

        fmt_menu.addSeparator()

        valign_menu = fmt_menu.addMenu("&Vertical Alignment")
        valign_menu.addAction("Align &Top").triggered.connect(
            lambda: self._run_js("setVAlign('top')")
        )
        valign_menu.addAction("Align &Middle").triggered.connect(
            lambda: self._run_js("setVAlign('middle')")
        )
        valign_menu.addAction("Align &Bottom").triggered.connect(
            lambda: self._run_js("setVAlign('bottom')")
        )

        fmt_menu.addSeparator()

        apply_css_action = fmt_menu.addAction("Apply &Stylesheet...")
        apply_css_action.setToolTip("Choose a CSS file to style the editor and saved HTML")
        apply_css_action.triggered.connect(self._menu_apply_css)

        # --- Table menu ---
        tbl_menu = menubar.addMenu("&Table")
        assert tbl_menu is not None

        insert_tbl_action = tbl_menu.addAction(_svg_icon(_SVG_INSERT_TABLE), "&Insert Table...")
        insert_tbl_action.setShortcut("Ctrl+Shift+T")
        insert_tbl_action.triggered.connect(self._menu_table_insert)

        tbl_menu.addSeparator()

        rows_menu = tbl_menu.addMenu("&Rows")
        rows_menu.addAction("Insert Row &Above").triggered.connect(
            lambda: self._run_js("tableOp('insertRowAbove')")
        )
        rows_menu.addAction("Insert Row &Below").triggered.connect(
            lambda: self._run_js("tableOp('insertRowBelow')")
        )
        rows_menu.addSeparator()
        rows_menu.addAction("&Delete Row").triggered.connect(
            lambda: self._run_js("tableOp('deleteRow')")
        )

        cols_menu = tbl_menu.addMenu("&Columns")
        cols_menu.addAction("Insert Column &Left").triggered.connect(
            lambda: self._run_js("tableOp('insertColLeft')")
        )
        cols_menu.addAction("Insert Column &Right").triggered.connect(
            lambda: self._run_js("tableOp('insertColRight')")
        )
        cols_menu.addSeparator()
        cols_menu.addAction("Delete &Column").triggered.connect(
            lambda: self._run_js("tableOp('deleteColumn')")
        )

        tbl_menu.addSeparator()

        cell_valign_menu = tbl_menu.addMenu("Cell &Vertical Alignment")
        cell_valign_menu.addAction("Align &Top").triggered.connect(
            lambda: self._run_js("setVAlign('top')")
        )
        cell_valign_menu.addAction("Align &Middle").triggered.connect(
            lambda: self._run_js("setVAlign('middle')")
        )
        cell_valign_menu.addAction("Align &Bottom").triggered.connect(
            lambda: self._run_js("setVAlign('bottom')")
        )

        tbl_menu.addSeparator()

        tbl_menu.addAction("Delete &Table").triggered.connect(
            lambda: self._run_js("tableOp('deleteTable')")
        )

        # --- Insert menu ---
        ins_menu = menubar.addMenu("&Insert")
        assert ins_menu is not None

        img_action = ins_menu.addAction("&Image...")
        img_action.setShortcut("Ctrl+Shift+I")
        img_action.triggered.connect(self._menu_insert_image)

        link_action = ins_menu.addAction("&Hyperlink...")
        link_action.setShortcut("Ctrl+K")
        link_action.triggered.connect(self._menu_insert_link)

        ins_menu.addSeparator()

        hr_action = ins_menu.addAction("Horizontal &Rule")
        hr_action.triggered.connect(lambda: self._run_js("insertHR()"))

        anchor_action = ins_menu.addAction("Insert &Anchor...")
        anchor_action.setShortcut("Ctrl+Shift+A")
        anchor_action.setToolTip("Insert a named bookmark (link target)")
        anchor_action.triggered.connect(self._menu_insert_anchor)

        ins_menu.addSeparator()

        quote_action = ins_menu.addAction("Block&quote")
        quote_action.triggered.connect(lambda: self._run_js("quill.format('blockquote', true)"))

        code_action = ins_menu.addAction("&Code Block")
        code_action.triggered.connect(lambda: self._run_js("quill.format('code-block', true)"))

    # ------------------------------------------------------------------
    # Menu action handlers
    # ------------------------------------------------------------------

    def _menu_open(self) -> None:
        if not self._ask_save_if_dirty():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "data",
            "Supported files (*.md *.html *.htm);;Markdown (*.md);;HTML (*.html *.htm);;All Files (*)",
        )
        if path:
            self.open_file(path)

    def _open_template(self) -> None:
        """Open data/template.md if it exists."""
        if not self._ask_save_if_dirty():
            return
        template_path = _BASE / "data" / "template.md"
        if template_path.exists():
            self.open_file(str(template_path))
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Template", "data", "Markdown (*.md);;HTML (*.html)"
            )
            if path:
                self.open_file(path)

    def _menu_insert_image(self) -> None:
        """Insert image via bridge (same as toolbar button)."""
        data_uri = self._bridge.request_image_insert()
        if data_uri:
            self._run_js(
                f"{{ const r=quill.getSelection(true); "
                f"quill.insertEmbed(r.index,'image',{json.dumps(data_uri)},Quill.sources.USER); }}"
            )

    def _menu_insert_link(self) -> None:
        """Insert link via bridge (same as toolbar button)."""
        json_str = self._bridge.request_link_insert("")
        if not json_str:
            return
        data = json.loads(json_str)
        url = json.dumps(data.get("url", ""))
        text = json.dumps(data.get("text", "") or data.get("url", ""))
        self._run_js(
            f"{{ const r=quill.getSelection(true); "
            f"if (r && r.length>0) {{ quill.format('link',{url},Quill.sources.USER); }}"
            f"else {{ quill.insertText(r.index,{text},'link',{url},Quill.sources.USER); }} }}"
        )

    def _menu_insert_anchor(self) -> None:
        """Open anchor name dialog and insert a bookmark at the cursor."""
        dialog = _AnchorDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = dialog.get_name()
        if name:
            self._run_js(f"insertAnchor({json.dumps(name)})")

    def _menu_table_insert(self) -> None:
        """Open the table dimensions dialog and insert a table."""
        json_str = self._bridge.request_table_insert()
        if json_str:
            d = json.loads(json_str)
            self._run_js(f"tableOp('insertTable', {d['rows']}, {d['cols']})")

    def _menu_apply_css(self) -> None:
        """Open a CSS file picker and apply the stylesheet to the editor canvas."""
        initial = str(Path(self._css_path).parent) if self._css_path else str(_BASE / "css")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Apply Stylesheet",
            initial,
            "CSS Files (*.css);;All Files (*)",
        )
        if path:
            self._bridge.css_changed.emit(os.path.abspath(path))

    def _on_css_changed(self, css_path: str) -> None:
        """Apply a new CSS file to the editor canvas and store for save-time use."""
        self._css_path = css_path
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                css_text = f.read()
            self._run_js(f"applyCSS({json.dumps(css_text)})")
            self._css_status_label.setText(f"CSS: {Path(css_path).name}")
            log.info("Applied CSS: %s", css_path)
        except Exception as exc:
            log.error("CSS apply failed: %s", exc)
            QMessageBox.warning(self, "CSS Error", f"Could not read CSS file:\n{exc}")

    def _run_js(self, script: str) -> None:
        """Fire-and-forget JavaScript execution (wraps runJavaScript)."""
        self._view.page().runJavaScript(script)

    # ------------------------------------------------------------------
    # Dirty / title management
    # ------------------------------------------------------------------

    def _on_dirty_changed(self, dirty: bool) -> None:
        self._update_title()

    def _update_title(self) -> None:
        dirty_marker = " *" if self._bridge.is_dirty else ""
        if self._file_path:
            filename = Path(self._file_path).name
            self.setWindowTitle(f"sendMail Editor — {filename}{dirty_marker}")
        else:
            self.setWindowTitle(f"sendMail Editor — New Document{dirty_marker}")

    def _ask_save_if_dirty(self) -> bool:
        """
        If the document has unsaved changes, ask the user whether to save.
        Returns True if safe to proceed (saved or discarded), False if cancelled.
        """
        if not self._bridge.is_dirty:
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "The document has unsaved changes.\nDo you want to save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self._save()
        if reply == QMessageBox.StandardButton.Discard:
            return True
        return False  # Cancel

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._ask_save_if_dirty():
            event.accept()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("sendMail Editor")
    app.setOrganizationName("sendMail")

    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    window = EditorWindow(file_path=file_arg)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
