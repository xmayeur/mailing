#!/usr/bin/env python
# coding: utf-8
"""
WYSIWYG HTML editor for composing sendMail newsletters.

Usage:
    python editor.py                       # blank editor
    python editor.py data/template.md      # open existing markdown file
    python editor.py data/newsletter.html  # open existing HTML file

The editor saves output as .html, ready for sendMail:
    python sendMail.py --profile cambristi data/newsletter.html
"""

import json
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

# ---------------------------------------------------------------------------
# PyInstaller-safe asset path resolution
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _BASE = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BASE = Path(__file__).parent

ASSETS_DIR = _BASE / "editor_assets"

FONT_CHOICES = [
    "Arial",
    "Courier New",
    "Georgia",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("editor")

# ---------------------------------------------------------------------------
# Qt imports
# ---------------------------------------------------------------------------
from PyQt6.QtCore import QByteArray, QObject, QUrl, QSize, pyqtSignal, pyqtSlot  # noqa: E402
from PyQt6.QtGui import QIcon, QPixmap  # noqa: E402
from PyQt6.QtWebChannel import QWebChannel  # noqa: E402
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QCheckBox,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QComboBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QToolBar,
    QSpinBox,
    QStatusBar,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
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

_SVG_SEND = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    '<path d="M1.5 8l12-5-3.2 5 3.2 5-12-5z" fill="#1565C0"/>'
    '<path d="M1.8 8h7.2" stroke="#fff" stroke-width="1" stroke-linecap="round"/>'
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
# Send dialog
# ---------------------------------------------------------------------------
class _SendDialog(QDialog):
    """Dialog for selecting sendMail options before sending the edited file."""

    def __init__(
        self,
        parent=None,
        *,
        attachment_path: str,
        config_path: str,
        config_data: dict[str, dict] | None = None,
        initial_profile: str = "default",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Send Newsletter")
        self.setMinimumWidth(720)

        self._config_data: dict[str, dict] = config_data or {}
        self._attachment_path = attachment_path

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        root.addLayout(form)

        self.config_input = QLineEdit(config_path, self)
        self.config_input.setReadOnly(True)
        config_row = QWidget(self)
        config_row_layout = QHBoxLayout(config_row)
        config_row_layout.setContentsMargins(0, 0, 0, 0)
        config_row_layout.addWidget(self.config_input, 1)
        config_browse = QPushButton("Browse", config_row)
        config_browse.clicked.connect(self._browse_config)
        config_row_layout.addWidget(config_browse)
        form.addRow("Config", config_row)

        self.profile_combo = QComboBox(self)
        self.profile_combo.currentTextChanged.connect(self._load_profile_defaults)
        form.addRow("Profile", self.profile_combo)

        attachment_label = QLabel(Path(attachment_path).name, self)
        attachment_label.setToolTip(attachment_path)
        form.addRow("Attachment", attachment_label)

        self.subject_input = QLineEdit(self)
        form.addRow("Subject", self.subject_input)

        self.message_input = QPlainTextEdit(self)
        self.message_input.setPlaceholderText("Mail body / template text")
        self.message_input.setMinimumHeight(110)
        form.addRow("Message", self.message_input)

        self.body_input = QLineEdit(self)
        self.body_input.setPlaceholderText("Optional ${body} replacement text")
        form.addRow("Body", self.body_input)

        self.database_input = QLineEdit(self)
        database_row = QWidget(self)
        database_row_layout = QHBoxLayout(database_row)
        database_row_layout.setContentsMargins(0, 0, 0, 0)
        database_row_layout.addWidget(self.database_input, 1)
        database_browse = QPushButton("Browse", database_row)
        database_browse.clicked.connect(self._browse_database)
        database_row_layout.addWidget(database_browse)
        form.addRow("Database", database_row)

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password", self.password_input)

        self.from_index_input = QSpinBox(self)
        self.from_index_input.setRange(0, 1_000_000)
        form.addRow("From index", self.from_index_input)

        self.to_index_input = QSpinBox(self)
        self.to_index_input.setRange(0, 1_000_000)
        form.addRow("To index", self.to_index_input)

        self.wait_input = QSpinBox(self)
        self.wait_input.setRange(0, 1_000_000)
        form.addRow("Wait (min)", self.wait_input)

        self.max_mails_input = QSpinBox(self)
        self.max_mails_input.setRange(1, 1_000_000)
        form.addRow("Max mails/hour", self.max_mails_input)

        self.max_addr_input = QSpinBox(self)
        self.max_addr_input.setRange(1, 1_000_000)
        form.addRow("Max addr/mail", self.max_addr_input)

        self.pause_input = QSpinBox(self)
        self.pause_input.setRange(0, 3600)
        form.addRow("Pause (sec)", self.pause_input)

        flag_row = QWidget(self)
        flag_layout = QHBoxLayout(flag_row)
        flag_layout.setContentsMargins(0, 0, 0, 0)
        flag_layout.setSpacing(10)
        self.test_check = QCheckBox("Test", flag_row)
        self.verbose_check = QCheckBox("Verbose", flag_row)
        self.do_not_send_check = QCheckBox("Do not send", flag_row)
        self.selected_check = QCheckBox("Selected only", flag_row)
        for widget in (self.test_check, self.verbose_check, self.do_not_send_check, self.selected_check):
            flag_layout.addWidget(widget)
        flag_layout.addStretch(1)
        form.addRow("Flags", flag_row)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Send")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        self._reload_profiles()
        if self.profile_combo.count():
            idx = self.profile_combo.findText(initial_profile)
            self.profile_combo.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self._load_profile_defaults("")

    def _browse_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select sendMail config",
            str(Path(self.config_input.text()).parent) if self.config_input.text() else str(Path.home()),
            "YAML Files (*.yml *.yaml);;All Files (*)",
        )
        if path:
            self.config_input.setText(path)
            self._reload_profiles()

    def _browse_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select database",
            str(Path(self.database_input.text()).parent) if self.database_input.text() else str(Path.home()),
            "Data Files (*.csv *.xlsx *.xlsm *.xls *.ods);;All Files (*)",
        )
        if path:
            self.database_input.setText(path)

    def _reload_profiles(self) -> None:
        path = self.config_input.text().strip()
        self._config_data = {}
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        try:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if isinstance(data, dict):
                    self._config_data = data
                    self.profile_combo.addItems(sorted(data.keys()))
        except Exception as exc:
            QMessageBox.warning(self, "Config Error", f"Could not load config:\n{exc}")
        finally:
            self.profile_combo.blockSignals(False)
        if self.profile_combo.count() == 0:
            self.profile_combo.addItem("default")
        self._load_profile_defaults(self.profile_combo.currentText())

    def _load_profile_defaults(self, profile: str) -> None:
        profile_cfg = self._config_data.get(profile, {}) if isinstance(self._config_data, dict) else {}
        if not isinstance(profile_cfg, dict):
            profile_cfg = {}

        def _int_or_zero(value: object) -> int:
            try:
                return int(value)
            except Exception:
                return 0

        self.subject_input.setText(Path(self._attachment_path).stem)
        self.message_input.setPlainText(str(profile_cfg.get("default_message", "")))
        self.body_input.setText("")
        self.database_input.setText(str(profile_cfg.get("database", "")))
        self.password_input.setText(str(profile_cfg.get("password", "")))

        self.from_index_input.setValue(_int_or_zero(profile_cfg.get("from_index")))
        self.to_index_input.setValue(_int_or_zero(profile_cfg.get("to_index")))
        self.wait_input.setValue(_int_or_zero(profile_cfg.get("wait")))
        self.max_mails_input.setValue(max(1, _int_or_zero(profile_cfg.get("max_mails_per_hour", 1000)) or 1000))
        self.max_addr_input.setValue(max(1, _int_or_zero(profile_cfg.get("max_addr_per_mail", 50)) or 50))
        self.pause_input.setValue(max(0, _int_or_zero(profile_cfg.get("pause", 3))))
        self.test_check.setChecked(bool(profile_cfg.get("test", False)))
        self.verbose_check.setChecked(bool(profile_cfg.get("verbose", False)))
        self.do_not_send_check.setChecked(bool(profile_cfg.get("doNotSend", False)))
        self.selected_check.setChecked(bool(profile_cfg.get("selected", False)))

    def build_args(self, config_data: dict[str, dict]) -> SimpleNamespace:
        profile = self.profile_combo.currentText().strip() or "default"
        namespace = SimpleNamespace()
        namespace.config = self.config_input.text().strip() or None
        namespace.conf = config_data
        namespace.profile = profile
        namespace.subject = self.subject_input.text().strip() or None
        namespace.message = self.message_input.toPlainText().strip()
        namespace.body = self.body_input.text().strip() or None
        namespace.file = [self._attachment_path]
        namespace.test = self.test_check.isChecked()
        namespace.verbose = self.verbose_check.isChecked()
        namespace.doNotSend = self.do_not_send_check.isChecked()
        namespace.database = self.database_input.text().strip() or None
        namespace.from_index = str(self.from_index_input.value()) if self.from_index_input.value() else None
        namespace.to_index = str(self.to_index_input.value()) if self.to_index_input.value() else None
        namespace.wait = self.wait_input.value() or None
        namespace.selected = self.selected_check.isChecked()
        namespace.max_mails_per_hour = self.max_mails_input.value()
        namespace.max_addr_per_mail = self.max_addr_input.value()
        namespace.pause = self.pause_input.value()
        return namespace


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
        self._send_in_progress = False

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
        self._build_toolbars()
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
            result = self._normalize_table_cells(result)
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
        """Convert bare <a id="name"> tags (no href) to editor-anchor spans for Quill.

        Uses "editor-anchor" (not "ql-anchor") to avoid Quill stripping the ql-* namespace.
        """
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
                **{"class": "editor-anchor", "data-anchor-id": anchor_id,
                   "title": f"Anchor: {anchor_id}"},
            )
            span.string = "⚓"  # ⚓
            a.replace_with(span)
        # If html.parser wrapped the fragment in html/body, extract body content only
        body = soup.find("body")
        return body.decode_contents() if body else str(soup)

    @staticmethod
    def _spans_to_anchors(html: str) -> str:
        """Convert editor-anchor spans back to <a id> tags before saving."""
        import re
        def _replace(m: re.Match) -> str:
            aid = m.group(1)
            return f'<a id="{aid}" name="{aid}"></a>'
        return re.sub(
            r'<span[^>]+class="editor-anchor"[^>]+data-anchor-id="([^"]+)"[^>]*>⚓</span>',
            _replace,
            html,
        )

    @staticmethod
    def _normalize_table_cells(html: str) -> str:
        """Normalize <table> structure for Quill v2's native table format.

        Quill v2 represents each <td>/<th> as a Block-scope blot identified by a
        ``data-row`` attribute (same value for every cell on the same row). Cells
        contain INLINE content directly — any <p> or other block element inside
        a cell is hoisted out during normalisation, breaking the table.

        This method:
          - Assigns a row id ("row-XXXX") to every <td>/<th>, shared per row.
          - Unwraps every block-level descendant of each cell, inserting a <br>
            between successive blocks so multi-paragraph cells keep their line
            separation.
        """
        from bs4 import BeautifulSoup
        import secrets

        soup = BeautifulSoup(html, "html.parser")
        block_tags = ("p", "h1", "h2", "h3", "h4", "h5", "h6",
                      "div", "blockquote", "pre")

        for tr in soup.find_all("tr"):
            row_id = "row-" + secrets.token_hex(2)  # matches Quill's nt() format
            for cell in tr.find_all(["td", "th"], recursive=False):
                cell["data-row"] = row_id
                # Iteratively unwrap block-level children, keeping line breaks.
                # Repeats until the cell holds only inline content.
                while True:
                    direct_blocks = [
                        c for c in list(cell.children)
                        if getattr(c, "name", None) in block_tags
                    ]
                    if not direct_blocks:
                        break
                    for i, block in enumerate(direct_blocks):
                        if i > 0:
                            block.insert_before(soup.new_tag("br"))
                        block.unwrap()

        body = soup.find("body")
        return body.decode_contents() if body else str(soup)

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
        """Save current content as HTML. Returns True on success."""
        if not self._file_path:
            return self._save_as()

        body_html = self._spans_to_anchors(self._bridge.get_current_html())
        stem = Path(self._file_path).with_suffix("")
        html_path = str(stem) + ".html"

        try:
            self._write_html_file(html_path, body_html)
            self._file_path = html_path
            self._bridge.reset(body_html)
            self._update_title()
            self._view.page().runJavaScript("markSaved()")
            self.statusBar().showMessage(f"Saved: {html_path}", 4000)
            log.info("Saved HTML: %s", html_path)
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{exc}")
            log.error("Save failed: %s", exc)
            return False

    def _save_as(self) -> bool:
        """Prompt for an HTML filename then save. Returns True on success."""
        initial_dir = str(Path(self._file_path).parent) if self._file_path else "data"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            initial_dir,
            "HTML (*.html);;All Files (*)",
        )
        if not path:
            return False
        self._file_path = str(Path(path).with_suffix(".html"))
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

        send_action = file_menu.addAction("&Send...")
        send_action.setShortcut("Ctrl+Enter")
        send_action.triggered.connect(self._menu_send)

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

        font_menu = fmt_menu.addMenu("&Font Family")
        font_menu.addAction("&Default").triggered.connect(
            lambda checked=False: self._set_font_family(None)
        )
        for font_name in FONT_CHOICES:
            font_menu.addAction(font_name).triggered.connect(
                lambda checked=False, family=font_name: self._set_font_family(family)
            )

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

    def _build_toolbars(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        save_action = toolbar.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            "Save",
        )
        save_action.setToolTip("Save the current HTML")
        save_action.triggered.connect(self._save)

        send_action = toolbar.addAction(_svg_icon(_SVG_SEND), "Send")
        send_action.setToolTip("Save and send the edited file")
        send_action.triggered.connect(self._menu_send)

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

    def _resolve_send_config_path(self) -> str:
        """Return the default sendMail config path, falling back to ~/.config/sendMail.yml."""
        if _SM_AVAILABLE and hasattr(sm, "get_default_config_path"):
            try:
                cfg = sm.get_default_config_path()
                if cfg == -1:
                    cfg = sm.get_default_config_path()
                if cfg != -1:
                    return str(cfg)
            except Exception as exc:
                log.debug("Could not resolve sendMail config path: %s", exc)
        return str(Path.home() / ".config" / "sendMail.yml")

    def _load_send_config(self, config_path: str) -> dict[str, dict]:
        """Load the sendMail YAML config file."""
        if not config_path or not os.path.exists(config_path):
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            QMessageBox.warning(self, "Config Error", f"Could not load config:\n{exc}")
            return {}

    def _send_with_sendmail(self, dialog: _SendDialog) -> str:
        """Run sendMail with the options selected in the dialog."""
        args = dialog.build_args(dialog._config_data)
        if args.profile not in args.conf:
            raise ValueError(f"Profile '{args.profile}' not found in config")

        dialog_password = dialog.password_input.text().strip()
        if dialog_password:
            args.conf[args.profile]["password"] = dialog_password

        sendmail_dir = Path(sm.__file__).resolve().parent if hasattr(sm, "__file__") else Path.cwd()
        old_cwd = os.getcwd()
        try:
            os.chdir(sendmail_dir)
            return sm.process_profile(args)
        finally:
            os.chdir(old_cwd)

    @staticmethod
    def _send_result_is_success(result: object) -> bool:
        """Interpret sendMail results without depending on one exact return spelling."""
        if result is None:
            return False
        if isinstance(result, str):
            status = result.strip()
            if status.upper() in {"OK", "OK_TEST"}:
                return True
            lowered = status.lower()
            if "error" in lowered or "fail" in lowered:
                return False
            return True
        return bool(result)

    def _menu_send(self) -> None:
        """Open the send dialog and send the current HTML file if confirmed."""
        if self._send_in_progress:
            return
        if not _SM_AVAILABLE:
            QMessageBox.warning(self, "sendMail Not Available", "Cannot import sendMail module — sending is disabled.")
            return
        if not self._ask_save_if_dirty():
            return
        if not self._file_path or not os.path.exists(self._file_path):
            if not self._save():
                return

        config_path = self._resolve_send_config_path()
        config_data = self._load_send_config(config_path)
        dialog = _SendDialog(
            self,
            attachment_path=str(self._file_path),
            config_path=config_path,
            config_data=config_data,
            initial_profile="default",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._send_in_progress = True
        try:
            result = self._send_with_sendmail(dialog)
        except Exception as exc:
            QMessageBox.critical(self, "Send Error", f"Failed to send:\n{exc}")
            log.error("Send failed: %s", exc)
            return
        finally:
            self._send_in_progress = False

        if self._send_result_is_success(result):
            if isinstance(result, str) and result.strip().upper() == "OK_TEST":
                QMessageBox.information(self, "Send", "Message sent successfully in test mode.")
            else:
                QMessageBox.information(self, "Send", "Message sent successfully.")
        else:
            log.warning("sendMail returned non-success status after send attempt: %r", result)
            QMessageBox.warning(self, "Send", "Sending failed. Check the log for details.")

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

    def _set_font_family(self, family: str | None) -> None:
        """Apply a font family to the current selection."""
        if family:
            self._run_js(f"quill.format('font', {json.dumps(family)})")
        else:
            self._run_js("quill.format('font', false)")

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
