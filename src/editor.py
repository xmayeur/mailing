#!/usr/bin/env python
"""
WYSIWYG HTML editor for composing sendMail newsletters.

Usage:
    python src/editor.py                       # blank editor
    python src/editor.py data/template.md      # open existing markdown file
    python src/editor.py data/newsletter.html  # open existing HTML file

The editor saves output as .html, ready for sendMail:
    python src/sendMail.py --profile cambristi data/newsletter.html
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, TypeAlias, cast

import yaml

# Type aliases for complex config structures
# Using TypeAlias for Python 3.10/3.11 compatibility (PEP 695 'type' requires 3.12+)
ConfigValue: TypeAlias = str | int | list[str] | dict[str, str]  # noqa: UP040
ConfigData: TypeAlias = dict[str, ConfigValue]  # noqa: UP040
ConfigProfile: TypeAlias = dict[str, ConfigData]  # noqa: UP040

# ---------------------------------------------------------------------------
# PyInstaller-safe asset & module path resolution
# ---------------------------------------------------------------------------
_IS_FROZEN = getattr(sys, "frozen", False)

if _IS_FROZEN:
    _MEIPASS = Path(sys._MEIPASS)  # type: ignore
    # For macOS BUNDLE, sys._MEIPASS is Contents/Frameworks/
    # Correct to Contents/ for asset/module resolution
    if _MEIPASS.name == "Frameworks" and _MEIPASS.parent.name == "Contents":
        _BASE = _MEIPASS.parent  # Contents/
    else:
        _BASE = _MEIPASS

    # In bundled macOS app, modules/assets are in Contents/Resources/ and Contents/Frameworks/
    _MODULES_PATH = [
        _BASE / "Resources",
        _BASE / "Frameworks",
    ]
else:
    _BASE = Path(__file__).parent
    _MODULES_PATH = [_BASE]

# Add module paths so local modules (sendMail, googleDriveLib, etc.) can be imported
for mod_path in _MODULES_PATH:
    if str(mod_path) not in sys.path:
        sys.path.insert(0, str(mod_path))

ASSETS_DIR = (
    _BASE / "Resources" / "editor_assets" if _IS_FROZEN else _BASE / "editor_assets"
)

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


class _LogCapture(logging.Handler):
    """Capture log records for display in session log dialog.

    Appends formatted log messages to a list as they occur.

    Args:
        log_list: List to append log messages to
    """

    def __init__(self, log_list: list[str]) -> None:
        super().__init__()
        self.log_list = log_list
        self.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.log_list.append(msg)
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# Qt imports
# ---------------------------------------------------------------------------
from PyQt6.QtCore import (  # noqa: E402
    QByteArray,
    QObject,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QIcon, QPixmap  # noqa: E402
from PyQt6.QtWebChannel import QWebChannel  # noqa: E402
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# sendMail utility imports (reuse existing functions)
# ---------------------------------------------------------------------------
_SM_AVAILABLE = False
try:
    import sendMail as sm  # noqa: E402,N813  (import after path setup, camelCase module name)

    _SM_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    log.warning("sendMail module not importable: %s", exc)
    import traceback

    log.warning("sendMail import traceback:\n%s", traceback.format_exc())

try:
    from filter_validator import FilterValidator  # noqa: E402

    _VALIDATOR_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    log.warning("FilterValidator not importable: %s", exc)
    _VALIDATOR_AVAILABLE = False

try:
    from visual_filter_builder import DatabaseSchemaInfo, FilterBuilder  # noqa: E402

    _FILTER_BUILDER_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    log.warning("FilterBuilder not importable: %s", exc)
    _FILTER_BUILDER_AVAILABLE = False

# Fallback markdown support
try:
    import markdown2  # noqa: E402

    _MD2_AVAILABLE = True
except Exception:  # pragma: no cover
    _MD2_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CONFIG_ERROR = "Config Error"
_DEFAULT_MIME_TYPE = "image/png"
_HTML_EXT = ".html"
_HTML_PARSER = "html.parser"

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
    "</svg>"
)

_SVG_SEND = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="2 2 14 14">'
    '<path d="M1.5 8l16-5-3.2 5 3.2 5-16-5z" fill="#1565C0"/>'
    '<path d="M1.8 8h7.2" stroke="#fff" stroke-width="1" stroke-linecap="round"/>'
    "</svg>"
)


def _svg_icon(svg: str) -> QIcon:
    """Create a QIcon from an SVG string; returns an empty icon if the SVG plugin is unavailable."""
    pix = QPixmap()
    pix.loadFromData(QByteArray(svg.encode()), "SVG")
    return QIcon(pix)


# ---------------------------------------------------------------------------
# Link insertion dialog
# ---------------------------------------------------------------------------
class _LinkDialog(QDialog):  # pragma: no cover  # type: ignore[misc]
    """Small dialog asking for a URL and optional display text."""

    def __init__(self, parent: QWidget | None = None, selected_text: str = "") -> None:
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
# Session log viewer dialog
# ---------------------------------------------------------------------------
class _SessionLogDialog(QDialog):  # pragma: no cover  # type: ignore[misc]
    """Dialog displaying the session log from a send operation."""

    def __init__(
        self, parent: QWidget | None = None, log_entries: list[str] | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Send Session Log")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.log_view = QPlainTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setFont(self.log_view.font())
        if log_entries:
            self.log_view.setPlainText("\n".join(log_entries))
        layout.addWidget(self.log_view, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def append_log(self, text: str) -> None:
        """Append text to the log view."""
        cursor = self.log_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_view.setTextCursor(cursor)
        self.log_view.insertPlainText(text + "\n")


# ---------------------------------------------------------------------------
# Anchor insertion dialog
# ---------------------------------------------------------------------------
class _AnchorDialog(QDialog):  # pragma: no cover  # type: ignore[misc]
    """Small dialog asking for a named anchor / bookmark identifier."""

    def __init__(self, parent: QWidget | None = None) -> None:
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
class _TableDialog(QDialog):  # pragma: no cover  # type: ignore[misc]
    """Dialog asking for table dimensions (rows × columns)."""

    def __init__(self, parent: QWidget | None = None) -> None:
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
class _SendDialog(QDialog):  # pragma: no cover  # type: ignore[misc]
    """Dialog for selecting sendMail options before sending the edited file."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        attachment_path: str,
        config_path: str,
        config_data: dict[str, dict[str, str | int]] | None = None,
        initial_profile: str = "default",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Send Mailing")
        # Keep dialog on top of main window (non-blocking show)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        # B040: Dialog width extends beyond filter widget right edge
        # Filter widget 900px + scroll area margins/scrollbar + dialog margins = 1150px
        self.setMinimumWidth(1150)

        self._config_data: dict[str, dict[str, str | int]] = config_data or {}
        self._current_profile = ""
        self._attachment_path = attachment_path
        self._initial_config_data = config_data or {}
        self._session_filter: dict[str, str] | None = None
        self._original_filter_text = ""
        self._test_sent: bool = False
        self.attachments: list[str] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # B036: Make dialog vertically scrollable for many form fields
        from PyQt6.QtWidgets import QScrollArea

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(16, 16, 16, 12)
        scroll_layout.setSpacing(10)
        scroll.setWidget(scroll_content)

        root.addWidget(scroll)

        # Form layout inside scrollable area
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        scroll_layout.addLayout(form)

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
        attachment_widget = QWidget(self)
        attachment_layout = QVBoxLayout(attachment_widget)
        attachment_layout.setContentsMargins(0, 0, 0, 0)
        attachment_layout.setSpacing(4)
        attachment_layout.addWidget(attachment_label)
        self.attachment_list = QListWidget(self)
        self.attachment_list.setMinimumHeight(80)
        self.attachment_list.setMaximumHeight(120)
        self.attachment_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.attachment_list.customContextMenuRequested.connect(
            self._on_attachment_context_menu
        )
        add_attachment_btn = QPushButton("Add File(s)", attachment_widget)
        add_attachment_btn.clicked.connect(self._on_add_attachment)
        attachment_layout.addWidget(add_attachment_btn)
        attachment_layout.addWidget(self.attachment_list)
        help_label = QLabel("(Right-click on file to remove)", attachment_widget)
        help_label.setStyleSheet("color: #999; font-size: 10px;")
        attachment_layout.addWidget(help_label)
        form.addRow("Attachments", attachment_widget)

        self.subject_input = QLineEdit(self)
        extracted_subject = self._extract_subject_from_html(attachment_path)
        self.subject_input.setText(extracted_subject)
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
        # B015: Clear schema cache when database input changes (retry mechanism)
        self.database_input.textChanged.connect(self._on_database_input_changed)

        # Filter editor (T035: FilterBuilder with visual table + YAML tabs)
        if _FILTER_BUILDER_AVAILABLE:
            initial_filter_dict: dict[str, str] = {}
            try:
                if config_data and initial_profile in cast(Any, config_data):
                    profile_cfg = cast(Any, config_data)[initial_profile]
                    filter_obj = (
                        cast(Any, profile_cfg).get("filter")
                        if isinstance(profile_cfg, dict)
                        else None
                    )
                    if isinstance(filter_obj, dict):
                        initial_filter_dict = cast(dict[str, str], filter_obj)
            except (KeyError, TypeError, AttributeError) as e:
                log.debug("Could not extract initial filter from config: %s", e)
            self._schema_info = DatabaseSchemaInfo([])
            self._filter_builder = FilterBuilder(
                self._schema_info,
                initial_filter=initial_filter_dict,
                parent=self,
            )
            self._filter_builder.filter_changed.connect(self._on_filter_changed)
            self.filter_status_label = QLabel("", self)
            self.filter_status_label.setStyleSheet("color: #666; font-size: 11px;")
            filter_widget = QWidget(self)
            filter_layout = QVBoxLayout(filter_widget)
            filter_layout.setContentsMargins(0, 0, 0, 0)
            filter_layout.setSpacing(4)
            # B007: Wrap FilterBuilder in scroll area to prevent it from expanding
            # and hiding elements below (buttons, preview pane)
            from PyQt6.QtWidgets import QScrollArea

            scroll = QScrollArea()
            scroll.setWidget(self._filter_builder)
            scroll.setWidgetResizable(True)
            # B026-B027 & B031 & B043: Set explicit height/width for filter widget
            # Height: Allow 5 rows (30px each) + button (30px) = 300px + scrollbar = 320px
            # Width: minWidth 900px ensures dropdowns, operators, values all visible
            scroll.setMinimumHeight(320)
            scroll.setMaximumHeight(340)
            scroll.setMinimumWidth(900)
            scroll.setWidgetResizable(True)
            filter_layout.addWidget(scroll)
            filter_layout.addWidget(self.filter_status_label)
            form.addRow("Filter", filter_widget)
            # Keep filter_text_edit as reference to YAML tab for backward compat (used in _run_filter_validation)
            self.filter_text_edit = self._filter_builder._yaml_edit
        else:
            self.filter_text_edit = QPlainTextEdit(self)
            self.filter_text_edit.setPlaceholderText(
                "YAML filter (optional)\nExample: status: is active"
            )
            self.filter_text_edit.setMinimumHeight(60)
            self.filter_status_label = QLabel("", self)
            self.filter_status_label.setStyleSheet("color: #666; font-size: 11px;")
            filter_widget = QWidget(self)
            filter_layout = QVBoxLayout(filter_widget)
            filter_layout.setContentsMargins(0, 0, 0, 0)
            filter_layout.setSpacing(4)
            filter_layout.addWidget(self.filter_text_edit)
            filter_layout.addWidget(self.filter_status_label)
            form.addRow("Filter (YAML)", filter_widget)
            self._filter_builder = None  # type: ignore

        # Validation setup (T016, T017)
        self._filter_validator = FilterValidator() if _VALIDATOR_AVAILABLE else None
        self._schema_cache: Any = None  # Initialized lazily in _get_schema_cache()
        # B053: Cache database records to avoid repeated Google Sheets API calls
        self._cached_records: list[list[str]] | None = None  # Records cache
        self._cached_headers: list[str] | None = None  # Headers cache
        self._cached_for_profile: str | None = None  # Profile these records are for
        self._cached_for_db: str | None = None  # Database path these records are for
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self._run_filter_validation)
        if self._filter_builder:
            # Connect to FilterBuilder filter_changed signal for debounced validation
            pass  # FilterBuilder already emits on change, validation triggered via _on_filter_changed
        else:
            self.filter_text_edit.textChanged.connect(self._on_filter_text_changed)

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
        self.test_check.blockSignals(True)
        self.test_check.setChecked(True)
        self.test_check.toggled.connect(self._on_test_mode_toggled)
        self.test_check.blockSignals(False)
        self._update_test_mode_lock()
        self.verbose_check = QCheckBox("Verbose", flag_row)
        self.do_not_send_check = QCheckBox("Do not send", flag_row)
        for widget in (self.test_check, self.verbose_check, self.do_not_send_check):
            flag_layout.addWidget(widget)
        flag_layout.addStretch(1)
        form.addRow("Flags", flag_row)

        # Record preview (T024, T025, T040: retry button for errors)
        root.addSpacing(10)
        record_header_layout = QHBoxLayout()
        self.record_count_label = QLabel("Matching Records: 0", self)
        self.record_count_label.setStyleSheet("font-weight: bold;")
        record_header_layout.addWidget(self.record_count_label)

        # T040: Retry button for database connection failures
        self.retry_load_btn = QPushButton("Retry", self)
        self.retry_load_btn.setMaximumWidth(80)
        self.retry_load_btn.clicked.connect(self.filter_and_display_records)
        self.retry_load_btn.hide()  # Hidden by default, shown on error
        record_header_layout.addWidget(self.retry_load_btn)
        record_header_layout.addStretch()

        record_header_widget = QWidget(self)
        record_header_widget.setLayout(record_header_layout)
        root.addWidget(record_header_widget)

        self.records_table = QTableWidget(self)
        self.records_table.setMinimumHeight(120)
        self.records_table.setMaximumHeight(250)
        self.records_table.setColumnCount(0)
        self.records_table.setRowCount(0)
        root.addWidget(self.records_table)

        # Filter action buttons (T033)
        filter_buttons = QWidget(self)
        filter_buttons_layout = QHBoxLayout(filter_buttons)
        filter_buttons_layout.setContentsMargins(0, 0, 0, 0)
        filter_buttons_layout.setSpacing(10)

        apply_filter_btn = QPushButton("Apply Filter", filter_buttons)
        apply_filter_btn.clicked.connect(self._apply_filter)
        filter_buttons_layout.addWidget(apply_filter_btn)

        reset_filter_btn = QPushButton("Reset Filter", filter_buttons)
        reset_filter_btn.clicked.connect(self._reset_filter)
        filter_buttons_layout.addWidget(reset_filter_btn)

        filter_buttons_layout.addStretch(1)
        root.addWidget(filter_buttons)

        # Spinner label (shown during send)
        self.spinner_label = QLabel("Sending...", self)
        self.spinner_label.setStyleSheet("color: #666; font-style: italic;")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.hide()
        root.addWidget(self.spinner_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.rejected.connect(self.reject)
        # Add custom Send button (don't auto-close dialog on click)
        self.send_button = QPushButton("Send", self)
        buttons.addButton(self.send_button, QDialogButtonBox.ButtonRole.AcceptRole)
        root.addWidget(buttons)

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
            (
                str(Path(self.config_input.text()).parent)
                if self.config_input.text()
                else str(Path.home())
            ),
            "YAML Files (*.yml *.yaml);;All Files (*)",
        )
        if path:
            self.config_input.setText(path)
            self._reload_profiles()

    def _browse_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select database",
            (
                str(Path(self.database_input.text()).parent)
                if self.database_input.text()
                else str(Path.home())
            ),
            "Data Files (*.csv *.xlsx *.xlsm *.xls *.ods);;All Files (*)",
        )
        if path:
            self.database_input.setText(path)

    def _reload_profiles(self) -> None:
        path = self.config_input.text().strip()
        self._config_data = self._initial_config_data.copy()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        try:
            if path and os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if isinstance(data, dict):
                    self._config_data = data
                    self.profile_combo.addItems(sorted(data.keys()))
            elif self._config_data:
                self.profile_combo.addItems(sorted(self._config_data.keys()))
        except Exception as exc:
            QMessageBox.warning(self, _CONFIG_ERROR, f"Could not load config:\n{exc}")
        finally:
            self.profile_combo.blockSignals(False)
        if self.profile_combo.count() == 0:
            self.profile_combo.addItem("default")
        self._load_profile_defaults(self.profile_combo.currentText())

    def _load_profile_defaults(self, profile: str) -> None:
        import time

        self._current_profile = profile
        profile_cfg = self._config_data.get(profile, {})
        log.debug(
            "DEBUG: _load_profile_defaults: profile=%s, config_data keys=%s, profile_cfg keys=%s",
            profile,
            list(self._config_data.keys()),
            list(profile_cfg.keys()),
        )

        # B024-B025: Clear schema cache for new profile to force fresh load
        # Ensures Google Sheets and CSV profiles refresh when switching
        cache = self._get_schema_cache()
        # Clear all cache entries for this profile
        for key in list(cache._cache.keys()):
            if key.startswith(f"{profile}_"):
                cache.invalidate(key)

        # B053: Also invalidate record cache when profile changes
        # Records from previous profile must not be reused
        self._cached_records = None
        self._cached_headers = None
        self._cached_for_profile = None
        self._cached_for_db = None

        def _int_or_zero(value: object) -> int:
            try:
                if isinstance(value, int):
                    return value
                if isinstance(value, str):
                    return int(value)
                return int(str(value))
            except (ValueError, TypeError):
                return 0

        self.database_input.setText(str(profile_cfg.get("database", "")))
        # Process any pending Qt events to ensure database path is set before validation
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

        # T035: Update FilterBuilder schema when database changes
        # B008: Ensure schema is refreshed for both CSV and Google Sheets databases
        if self._filter_builder:
            t1 = time.time()
            schema_fields = self._get_database_schema()
            t2 = time.time()
            log.info("TIMING: _get_database_schema took %.2fs", t2 - t1)
            log.debug(
                "DEBUG: _load_profile_defaults profile=%s db_path=%s schema_fields=%s",
                profile,
                self.database_input.text(),
                schema_fields,
            )
            self._schema_info = DatabaseSchemaInfo(schema_fields)
            self._filter_builder.schema_info = self._schema_info
            log.debug("DEBUG: FilterBuilder schema_info set, calling refresh_schema")
            # Call refresh_schema on table_widget to update all row dropdowns
            t3 = time.time()
            self._filter_builder._table_widget.refresh_schema(self._schema_info)
            t4 = time.time()
            log.info("TIMING: refresh_schema took %.2fs", t4 - t3)
            log.debug(
                "DEBUG: refresh_schema called, row_widgets=%d",
                len(self._filter_builder._table_widget._row_widgets),
            )

        self.message_input.setPlainText(str(profile_cfg.get("default_message", "")))
        self.body_input.setText("")
        self.password_input.setText(str(profile_cfg.get("password", "")))

        self.from_index_input.setValue(_int_or_zero(profile_cfg.get("from_index")))
        self.to_index_input.setValue(_int_or_zero(profile_cfg.get("to_index")))
        self.wait_input.setValue(_int_or_zero(profile_cfg.get("wait")))
        self.max_mails_input.setValue(
            max(1, _int_or_zero(profile_cfg.get("max_mails_per_hour", 1000)) or 1000)
        )
        self.max_addr_input.setValue(
            max(1, _int_or_zero(profile_cfg.get("max_addr_per_mail", 50)) or 50)
        )
        self.pause_input.setValue(max(0, _int_or_zero(profile_cfg.get("pause", 3))))
        self.verbose_check.setChecked(bool(profile_cfg.get("verbose", False)))
        self.do_not_send_check.setChecked(bool(profile_cfg.get("doNotSend", False)))

        self.load_current_filter(profile)
        self.filter_and_display_records()

        # Reload stylesheet when profile changes (EditorWindow only)
        if hasattr(self, "_load_default_stylesheet"):
            self._load_default_stylesheet()

    def load_current_filter(self, profile: str) -> None:
        """Load filter from profile config and display in filter field (T036)."""
        profile_cfg = self._config_data.get(profile, {})
        # Use filter_test if test mode enabled, otherwise use filter
        filter_key = "filter_test" if self.test_check.isChecked() else "filter"
        filter_obj: Any = profile_cfg.get(filter_key)

        if not filter_obj:
            if self._filter_builder:
                self._filter_builder.set_filter_from_yaml({})
            else:
                self.filter_text_edit.setPlainText("")
            self.filter_status_label.setText("")
            self._original_filter_text = ""
            self._session_filter = None
            return

        # Format filter dict for display
        filter_dict: dict[str, str] = {}
        filter_str = ""
        try:
            if isinstance(filter_obj, dict):
                for key, value in filter_obj.items():
                    filter_dict[key] = str(value)
                    filter_str += f"{key}: {value}\n"
                filter_str = filter_str.rstrip()
            else:
                filter_str = str(filter_obj)
        except (TypeError, AttributeError):
            filter_str = str(filter_obj)

        if self._filter_builder:
            # T036: Load filter into visual editor (T035)
            self._filter_builder.set_filter_from_yaml(filter_dict)
        else:
            self.filter_text_edit.setPlainText(filter_str)
        self.filter_status_label.setText("")
        self._original_filter_text = filter_str
        self._session_filter = None

    def _extract_subject_from_html(self, html_path: str) -> str:
        """Extract subject from <h1> heading or filename (T005-T008).

        Returns: Subject text (up to 50 characters)
        """
        try:
            from bs4 import BeautifulSoup

            with open(html_path, encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                h1 = soup.find("h1")
                if h1:
                    text = h1.get_text(strip=True)
                    log.info("Extracted h1 from HTML: %s", text[:50])
                    return text[:50]
                else:
                    log.info("No h1 found in HTML file")
        except Exception as e:
            log.warning("Could not extract h1 from HTML: %s", e)
        filename = Path(html_path).stem
        log.info("Using filename fallback: %s", filename[:50])
        return filename[:50]

    def _on_add_attachment(self) -> None:
        """Open file picker and add selected files to attachment list (T012-T013)."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to attach",
            str(Path.home()),
            "All Files (*)",
        )
        for file_path in files:
            self.attachments.append(file_path)
            item = QListWidgetItem(Path(file_path).name)
            self.attachment_list.addItem(item)

    def _on_remove_attachment(self, row: int) -> None:
        """Remove file from attachment list (T014)."""
        if 0 <= row < len(self.attachments):
            self.attachments.pop(row)
            self.attachment_list.takeItem(row)

    def _on_attachment_context_menu(self, pos: Any) -> None:
        """Show context menu for attachment list (T014)."""
        item = self.attachment_list.itemAt(pos)
        if not item:
            return
        row = self.attachment_list.row(item)
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        if delete_action:
            delete_action.triggered.connect(lambda: self._on_remove_attachment(row))
        menu.exec(self.attachment_list.mapToGlobal(pos))

    def _update_test_mode_lock(self) -> None:
        """Update test checkbox lock state based on _test_sent (T020)."""
        if not self._test_sent:
            self.test_check.setChecked(True)
            self.test_check.setEnabled(False)
        else:
            self.test_check.setEnabled(True)

    def _unlock_test_mode(self) -> None:
        """Unlock test checkbox after successful test send (T022)."""
        self._test_sent = True
        self._update_test_mode_lock()

    def _on_test_mode_toggled(self, _checked: bool) -> None:
        """Update filter when test mode is toggled (T041)."""
        # Reload filter to show filter_test when in test mode, filter otherwise
        self.load_current_filter(self._current_profile)
        # Clear session filter since we're switching filter mode
        self._session_filter = None

    def _on_filter_changed(self, filter_dict: dict[str, str]) -> None:
        """Handle FilterBuilder filter_changed signal (T035, T041-T042).

        Updates _session_filter and triggers validation.
        Highlights invalid rows in visual table.

        Args:
            filter_dict: Updated filter dict from FilterBuilder
        """
        self._session_filter = filter_dict if filter_dict else None
        # T041-T042: Validate rows and highlight errors in visual table
        if self._filter_builder:
            self._filter_builder.validate_and_highlight_errors()
        # Trigger validation with debounced timer
        self._validation_timer.stop()
        self._validation_timer.start(50)
        # B053: Do NOT call filter_and_display_records here - it blocks UI during editing
        # User can apply filter via Apply button or trigger with debounce timer
        # Each call hits Google Sheets API (1+ sec), blocking user input
        # Only load records on explicit apply or after user stops editing (5+ sec debounce)
        if not hasattr(self, "_filter_apply_timer"):
            from PyQt6.QtCore import QTimer

            self._filter_apply_timer = QTimer()
            self._filter_apply_timer.setSingleShot(True)
            self._filter_apply_timer.timeout.connect(self._deferred_filter_display)
        self._filter_apply_timer.stop()
        self._filter_apply_timer.start(5000)  # 5 second debounce before auto-loading

    def _on_filter_text_changed(self) -> None:
        """Handle filter text change with debounced validation (T016, T017)."""
        self._validation_timer.stop()
        self._validation_timer.start(50)

    def _on_database_input_changed(self, _text: str) -> None:
        """Clear schema cache when database input changes (B015 retry mechanism).

        Allows user to fix database issues (e.g., move file to correct location)
        and have schema reload on next use without restarting dialog.

        B053: Also invalidate record cache since database changed.
        """
        cache = self._get_schema_cache()
        profile = self._current_profile or "default"
        # Clear all cache entries for this profile to force fresh schema load
        db_path = self.database_input.text().strip()
        if db_path:
            cache.invalidate(f"{profile}_csv_{db_path}")
        # Also clear Google Sheets cache entry if it exists
        cache.invalidate(f"{profile}_gsheet")
        # B053: Invalidate record cache since database path changed
        self._cached_records = None
        self._cached_headers = None
        self._cached_for_profile = None
        self._cached_for_db = None

    def _run_filter_validation(self) -> None:
        """Run filter validation and update UI (T018-T021)."""
        if not self._filter_validator:
            return

        filter_text = self.filter_text_edit.toPlainText()
        schema = self._get_database_schema()

        # T018: Get validation status
        status = self._filter_validator.get_validation_status(filter_text, schema)

        # T019, T021: Update status indicator and visual
        self._update_validation_ui(status)

    def _get_schema_cache(self) -> Any:
        """Get or create schema cache instance."""
        if self._schema_cache is None:
            from schema_cache import SchemaCacheProvider

            self._schema_cache = SchemaCacheProvider()
        return self._schema_cache

    def _get_database_schema(self) -> list[str]:
        """Get database schema (field names) from active database or Google Sheets."""
        cache = self._get_schema_cache()
        profile_name = self._current_profile or "default"
        db_path = self.database_input.text().strip()

        # Check if current profile uses Google Sheets (has SHEETID, no CSV database)
        profile_cfg = self._config_data.get(self._current_profile, {})
        # B047: Handle both uppercase and lowercase config keys
        sheet_id_val = profile_cfg.get("SHEETID") or profile_cfg.get("sheetid")
        sa_val = profile_cfg.get("SA") or profile_cfg.get("sa")
        log.debug(
            "DEBUG: _get_database_schema: profile=%s, db_path=%s, profile_cfg keys=%s, SHEETID=%s, SA=%s",
            self._current_profile,
            db_path,
            list(profile_cfg.keys()),
            sheet_id_val,
            sa_val,
        )
        if not db_path and sheet_id_val:
            # Google Sheets profile - try to load schema from Google Sheets
            sa = sa_val
            sheet_id = sheet_id_val
            log.debug(
                "DEBUG: Google Sheets profile detected: SA=%s, SHEETID=%s", sa, sheet_id
            )
            if sa and sheet_id:

                def _load_gsheet_schema() -> list[str]:
                    try:
                        from sendMail import get_google_sheets_schema  # Import directly

                        log.debug(
                            "DEBUG: Calling get_google_sheets_schema(%s, %s)",
                            str(sa),
                            str(sheet_id),
                        )
                        result = get_google_sheets_schema(str(sa), str(sheet_id))
                        log.debug(
                            "DEBUG: get_google_sheets_schema returned: %s", result
                        )
                        if isinstance(result, list):
                            return result
                    except Exception as e:
                        log.error(
                            "ERROR: Could not load Google Sheets schema: %s",
                            e,
                            exc_info=True,
                        )
                    return []

                schema = cast(
                    list[str], cache.get(f"{profile_name}_gsheet", _load_gsheet_schema)
                )
                log.debug("DEBUG: Final schema from cache: %s", schema)
                return schema
            return []

        if not db_path:
            return []

        def _load_csv_schema() -> list[str]:
            try:
                from schema_provider import DatabaseSchemaProvider

                return DatabaseSchemaProvider.detect_and_extract(db_path)
            except Exception as e:
                log.debug("Could not extract database schema: %s", e)
                return []

        return cast(
            list[str], cache.get(f"{profile_name}_csv_{db_path}", _load_csv_schema)
        )

    def _update_validation_ui(self, status: dict[str, Any]) -> None:
        """Update filter field UI based on validation status (T019, T020, T021, T041)."""
        is_valid = status.get("is_valid", True)
        syntax_errors = status.get("syntax_errors", [])
        missing_fields = status.get("missing_fields", [])

        # T021: Visual distinction (green/red border)
        if is_valid:
            self.filter_text_edit.setStyleSheet(
                "QPlainTextEdit { border: 1px solid #4CAF50; background: #f1f8f6; }"
            )
        else:
            self.filter_text_edit.setStyleSheet(
                "QPlainTextEdit { border: 1px solid #f44336; background: #ffebee; }"
            )

        # T020, T041: Error message display with count
        error_msg = ""
        error_count = len(syntax_errors) + len(missing_fields)
        if error_count > 0:
            error_msg = (
                f"✗ {error_count} validation error{'s' if error_count != 1 else ''} "
            )
        if syntax_errors:
            error_msg += "| Syntax: " + "; ".join(syntax_errors)
        if missing_fields:
            if syntax_errors:
                error_msg += " | "
            error_msg += f"Fields not found: {', '.join(missing_fields)}"

        self.filter_status_label.setText(error_msg)
        if is_valid:
            self.filter_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")

        # T027, T028: Update record preview on validation change
        if is_valid:
            self.filter_and_display_records()

    def load_database_records(self) -> tuple[list[list[str]], list[str]]:
        """Load database records from CSV or Google Sheets (T026).

        B053: Use cache to avoid repeated Google Sheets API calls during filter editing.
        Records are cached per (profile, database_path) pair and only loaded once.
        """
        db_path = self.database_input.text().strip()
        # B053: Check cache first - avoid Google Sheets API call if we have cached records
        if (
            self._cached_records is not None
            and self._cached_for_profile == self._current_profile
            and self._cached_for_db == db_path
        ):
            log.debug(
                f"Using cached records: {len(self._cached_records)} rows, {len(self._cached_headers or [])} headers"
            )
            return self._cached_records, self._cached_headers or []

        # Check if current profile uses Google Sheets (has SHEETID, no CSV database)
        profile_cfg = self._config_data.get(self._current_profile, {})
        # B047: Handle both uppercase and lowercase config keys
        sheet_id_val = profile_cfg.get("SHEETID") or profile_cfg.get("sheetid")
        sa_val = profile_cfg.get("SA") or profile_cfg.get("sa")
        if not db_path and sheet_id_val:
            # Google Sheets profile - try to load records from Google Sheets
            sa = sa_val
            sheet_id = sheet_id_val
            if sa and sheet_id:
                try:
                    import sendMail as sm  # noqa: N813

                    if hasattr(sm, "open_google_db_members_sheet") and hasattr(
                        sm, "read_all_sheet"
                    ):
                        wb = sm.open_google_db_members_sheet(str(sa), str(sheet_id))
                        data = sm.read_all_sheet(wb)
                        if data and len(data) > 0:
                            headers = [h.strip() for h in data[0] if h.strip()]
                            rows = data[1:]  # Skip header row
                            log.debug(
                                f"Loaded {len(rows)} records from Google Sheet {sheet_id}"
                            )
                            # B053: Cache the loaded records
                            self._cached_records = rows
                            self._cached_headers = headers
                            self._cached_for_profile = self._current_profile
                            self._cached_for_db = db_path
                            return rows, headers
                except Exception as e:
                    log.debug("Could not load Google Sheets records: %s", e)
            # B053: Cache empty result too, so we don't retry failed loads
            self._cached_records = []
            self._cached_headers = []
            self._cached_for_profile = self._current_profile
            self._cached_for_db = db_path
            return [], []

        if not db_path:
            log.debug("No database path set")
            return [], []

        try:
            import csv

            # Try CSV with robust encoding handling (T043: Unicode support)
            if db_path.endswith(".csv"):
                # Try UTF-8 first, fall back to latin-1 if needed
                encodings = ["utf-8", "latin-1", "utf-8-sig"]
                for encoding in encodings:
                    try:
                        with open(db_path, encoding=encoding) as f:
                            reader = csv.reader(f)
                            headers = next(reader, [])
                            rows = list(reader)
                            log.debug(
                                f"Loaded {len(rows)} records from {db_path} (encoding: {encoding})"
                            )
                            # B053: Cache the loaded records
                            self._cached_records = rows
                            self._cached_headers = headers
                            self._cached_for_profile = self._current_profile
                            self._cached_for_db = db_path
                            return rows, headers
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                # If all encodings fail, raise error
                raise ValueError(
                    f"Could not decode {db_path} with any supported encoding"
                )

            # Handle Excel files (XLSX, XLS) using same approach as sendMail.py
            if db_path.endswith((".xlsx", ".xls")):
                from python_calamine import CalamineWorkbook

                wb = CalamineWorkbook.from_path(db_path)
                ws = wb.get_sheet_by_index(0)
                data = ws.to_python()
                if data and len(data) > 0:
                    headers = [str(h).strip() for h in data[0] if h]
                    rows = [
                        [str(cell) if cell is not None else "" for cell in row]
                        for row in data[1:]
                    ]
                    log.debug(f"Loaded {len(rows)} records from {db_path}")
                    # B053: Cache the loaded records
                    self._cached_records = rows
                    self._cached_headers = headers
                    self._cached_for_profile = self._current_profile
                    self._cached_for_db = db_path
                    return rows, headers
                else:
                    log.debug(f"No data found in {db_path}")
                    raise ValueError(f"No data in {db_path}")
        except Exception as e:
            log.debug("Could not load database: %s", e)

        # B053: Cache empty result
        self._cached_records = []
        self._cached_headers = []
        self._cached_for_profile = self._current_profile
        self._cached_for_db = db_path
        return [], []

    def filter_and_display_records(self) -> None:
        """Load, filter, and display database records (T027, T028, T040, T041, T042)."""
        import time

        # T041: Handle profile switching by tracking current profile
        if not hasattr(self, "_last_profile"):
            self._last_profile = self._current_profile

        t1 = time.time()
        rows, headers = self.load_database_records()
        t2 = time.time()
        log.info(
            "TIMING: load_database_records took %.2fs, %d rows, %d headers",
            t2 - t1,
            len(rows),
            len(headers),
        )

        # T040, T042: Better error and zero-record handling
        if not headers:
            # Database load failed - show error message with retry button
            self.record_count_label.setText("Matching Records: Error loading database")
            self.record_count_label.setStyleSheet("color: #f44336; font-weight: bold;")
            self.retry_load_btn.show()  # T040: Show retry button on error
            self.records_table.setColumnCount(0)
            self.records_table.setRowCount(0)
            return

        if not rows:
            # T042: Zero records - show clear message
            self.record_count_label.setText("Matching Records: 0 records in database")
            self.record_count_label.setStyleSheet("color: #666; font-weight: bold;")
            self.retry_load_btn.hide()  # No retry needed for zero records
            self.records_table.setColumnCount(len(headers))
            self.records_table.setHorizontalHeaderLabels(headers)
            self.records_table.setRowCount(0)
            return

        # T028: Apply filter using FilterMatcher
        try:
            from filter_matcher import FilterMatcher

            matcher = FilterMatcher()
            # Use _session_filter if set (from FilterBuilder), otherwise read from YAML editor
            filter_dict: dict[str, str] = {}
            if self._session_filter:
                filter_dict = self._session_filter
                filtered_rows = matcher.filter_rows(rows, filter_dict, headers)
                log.debug(
                    f"Filter applied (from session): {filter_dict}, matched {len(filtered_rows)}/{len(rows)} records"
                )
            else:
                filter_text = self.filter_text_edit.toPlainText()
                if filter_text and filter_text.strip():
                    import yaml

                    filter_dict = yaml.safe_load(filter_text) or {}
                    filtered_rows = matcher.filter_rows(rows, filter_dict, headers)
                    log.debug(
                        f"Filter applied (from YAML): {filter_dict}, matched {len(filtered_rows)}/{len(rows)} records"
                    )
                else:
                    filtered_rows = rows
                    log.debug(f"No filter, showing all {len(rows)} records")

            self._update_record_display(filtered_rows, headers, len(rows))
            # Reset error state on success
            self.record_count_label.setStyleSheet("font-weight: bold;")
            self.retry_load_btn.hide()  # T040: Hide retry button when successful
        except Exception as e:
            log.debug("Could not filter records: %s", e)
            self._update_record_display(rows, headers, len(rows))

    def _update_record_display(
        self, rows: list[list[str]], headers: list[str], total: int
    ) -> None:
        """Update record table display (T025)."""
        self.records_table.setColumnCount(len(headers))
        self.records_table.setHorizontalHeaderLabels(headers)
        self.records_table.setRowCount(len(rows))

        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value else "")
                self.records_table.setItem(row_idx, col_idx, item)

        # T029: Update count label
        self.record_count_label.setText(f"Matching Records: {len(rows)} / {total}")

    def _deferred_filter_display(self) -> None:
        """Deferred filter display after user stops editing (B053).

        Called by _filter_apply_timer after 5 seconds of no filter changes.
        Displays filtered records using cached data (no Google Sheets API call if cache valid).
        """
        log.debug("Deferred filter display triggered after 5 second debounce")
        self.filter_and_display_records()

    def _apply_filter(self) -> None:
        """Apply edited filter as session-active filter (T034)."""
        if self._filter_builder:
            # T037: Get filter from FilterBuilder (visual or YAML)
            filter_dict = self._filter_builder.get_filter_as_yaml()
        else:
            filter_text = self.filter_text_edit.toPlainText().strip()
            if not filter_text:
                filter_dict = {}
            else:
                import yaml

                try:
                    filter_dict = yaml.safe_load(filter_text) or {}
                except Exception as e:
                    self.filter_status_label.setText(f"Parse error: {e}")
                    self.filter_status_label.setStyleSheet(
                        "color: #f44336; font-size: 11px;"
                    )
                    return

        if not filter_dict:
            self._session_filter = None
            self.filter_status_label.setText(
                "(Filter cleared - will use profile default)"
            )
            self.filter_status_label.setStyleSheet("color: #666; font-size: 11px;")
            self.filter_and_display_records()
            return

        if not self._filter_validator:
            self.filter_status_label.setText("Filter validator not available")
            self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")
            return

        # Reconstruct YAML string for validator (expects text format)
        import yaml

        filter_text = yaml.dump(filter_dict, default_flow_style=False, sort_keys=False)
        schema = self._get_database_schema()
        status = self._filter_validator.get_validation_status(filter_text, schema)

        if not status.get("is_valid"):
            errors = status.get("syntax_errors", []) + status.get("missing_fields", [])
            self.filter_status_label.setText(f"Cannot apply: {', '.join(errors)}")
            self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")
            return

        try:
            self._session_filter = filter_dict
            self.filter_status_label.setText("✓ Session filter applied")
            self.filter_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.filter_and_display_records()
        except Exception as e:
            self.filter_status_label.setText(f"Error: {e}")
            self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")

    def _reset_filter(self) -> None:
        """Reset filter to original from profile config."""
        if self._filter_builder:
            # Parse original filter text back to dict for FilterBuilder
            if self._original_filter_text:
                try:
                    import yaml

                    filter_dict = yaml.safe_load(self._original_filter_text) or {}
                    if isinstance(filter_dict, dict):
                        self._filter_builder.set_filter_from_yaml(filter_dict)
                except Exception:
                    self._filter_builder.set_filter_from_yaml({})
            else:
                self._filter_builder.set_filter_from_yaml({})
        else:
            if self._original_filter_text:
                self.filter_text_edit.setPlainText(self._original_filter_text)
            else:
                self.filter_text_edit.setPlainText("")
        # B013: Set _session_filter to None AFTER loading filter (filter_changed signal already fired)
        self._session_filter = None
        self.filter_status_label.setText("(Filter reset to profile default)")
        self.filter_status_label.setStyleSheet("color: #666; font-size: 11px;")

    def build_args(
        self, config_data: dict[str, dict[str, str | int]]
    ) -> SimpleNamespace:
        profile = self.profile_combo.currentText().strip() or "default"
        namespace = SimpleNamespace()
        namespace.config = self.config_input.text().strip() or None
        namespace.conf = config_data
        namespace.profile = profile
        namespace.subject = self.subject_input.text().strip() or None
        namespace.message = self.message_input.toPlainText().strip()
        namespace.body = self.body_input.text().strip() or None
        namespace.file = [self._attachment_path]
        namespace.attachment = self.attachments if self.attachments else None
        namespace.test = self.test_check.isChecked()
        namespace.verbose = self.verbose_check.isChecked()
        namespace.doNotSend = self.do_not_send_check.isChecked()
        namespace.database = self.database_input.text().strip() or None
        namespace.from_index = (
            str(self.from_index_input.value())
            if self.from_index_input.value()
            else None
        )
        namespace.to_index = (
            str(self.to_index_input.value()) if self.to_index_input.value() else None
        )
        namespace.wait = self.wait_input.value() or None
        namespace.max_mails_per_hour = self.max_mails_input.value()
        namespace.max_addr_per_mail = self.max_addr_input.value()
        namespace.pause = self.pause_input.value()
        namespace.session_filter = (
            self._session_filter
        )  # T036: Pass session-active filter if set
        return namespace


@dataclass(frozen=True)
class _LineFieldSpec:
    key: str
    label: str
    tooltip: str = ""
    placeholder: str = ""
    password: bool = False
    browse_caption: str | None = None
    browse_filter: str = "All Files (*)"
    browse_type: str = "file"  # "file" or "directory"


# ---------------------------------------------------------------------------
# Settings / config editor
# ---------------------------------------------------------------------------
class _ConfigDialog(QDialog):  # pragma: no cover  # type: ignore[misc]
    """Dialog for editing sendMail YAML configuration by profile.

    Provides tabbed interface for editing:
    - Identity (sender, credentials)
    - Delivery (SMTP/IMAP settings)
    - Sources (subscriber database location)
    - Templates (message templates, rate limits)
    - Filters (filter_test and filter rules with validation)
    """

    _TAB_HELP: dict[str, str] = {
        "Identity": (
            "<h3>Identity</h3>"
            "<p>Profile identity and sender credentials.</p>"
            "<ul>"
            "<li><b>MAILCONFIG</b> can point at a secrets entry used by sendMail.</li>"
            "<li><b>sender</b> and <b>sendername</b> are required.</li>"
            "<li><b>username</b> and <b>password</b> are used by SMTP/IMAP mode.</li>"
            "</ul>"
        ),
        "Delivery": (
            "<h3>Delivery</h3>"
            "<p>SMTP/IMAP settings used when the profile sends mail directly through a mail server.</p>"
            "<ul>"
            "<li><b>smtp_host</b> and <b>smtp_port</b> configure SMTP.</li>"
            "<li><b>imap_host</b>, <b>imap_port</b>, and <b>sent_folder</b> configure sent-mail archival.</li>"
            "</ul>"
        ),
        "Sources": (
            "<h3>Sources</h3>"
            "<p>Choose either a local subscriber file or the Google Sheets secret references.</p>"
            "<ul>"
            "<li><b>database</b> can be CSV, XLSX, XLSM, XLS, or ODS.</li>"
            "<li><b>sa</b> and <b>sheetid</b> identify the Google Sheets service-account secrets.</li>"
            "<li><b>token_file</b>, <b>scopes</b>, and <b>credentials_id</b> are used for Gmail API mode.</li>"
            "</ul>"
        ),
        "Templates": (
            "<h3>Templates</h3>"
            "<p>Message defaults and mail-generation defaults.</p>"
            "<ul>"
            "<li><b>message</b> is the body template used by sendMail.</li>"
            "<li><b>default_message</b> is used when no message is provided.</li>"
            "<li><b>body</b> can be injected into templates via <code>${body}</code>.</li>"
            "<li><b>styles</b> points at the CSS file used when HTML is generated from Markdown.</li>"
            "<li><b>pause</b>, <b>from_index</b>, <b>to_index</b>, <b>wait</b>, "
            "<b>max_mails_per_hour</b>, and <b>max_addr_per_mail</b> control batch delivery.</li>"
            "</ul>"
        ),
        "Filters": (
            "<h3>Filters</h3>"
            "<p><b>filter</b> and <b>filter_test</b> are YAML mappings.</p>"
            "<p>Example:</p>"
            '<pre>filter:\n  email: is not empty\n  country: one of "BE", "FR"</pre>'
        ),
        "Flags": (
            "<h3>Flags</h3>"
            "<p>These booleans mirror the runtime CLI switches.</p>"
            "<ul>"
            "<li><b>test</b> enables test mode.</li>"
            "<li><b>verbose</b> increases logging.</li>"
            "<li><b>doNotSend</b> suppresses actual delivery.</li>"
            "<li><b>selected</b> limits processing to selected rows.</li>"
            "<li><b>md2html</b> and <b>keep-html</b> are preserved for compatibility.</li>"
            "</ul>"
        ),
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config_path: str,
        config_data: (
            dict[str, dict[str, str | int | list[str] | dict[str, str]]] | None
        ) = None,
        initial_profile: str = "default",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(1080)
        self.setMinimumHeight(780)

        self._config_data: ConfigProfile = self._normalize_config_data(
            config_data or {}
        )
        self._current_profile = ""
        self._widgets: dict[str, QWidget] = {}
        self._yaml_keys = {"filter", "filter_test"}
        self._list_keys = {"scopes"}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        path_row = QWidget(self)
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)
        self.config_input = QLineEdit(config_path, self)
        self.config_input.setReadOnly(True)
        self.config_input.setToolTip("Path to the sendMail YAML configuration file")
        path_layout.addWidget(self.config_input, 1)
        browse_button = QPushButton("Browse", path_row)
        browse_button.setToolTip("Choose a different config file")
        browse_button.clicked.connect(self._browse_config)
        path_layout.addWidget(browse_button)
        reload_button = QPushButton("Reload", path_row)
        reload_button.setToolTip("Reload the configuration from disk")
        reload_button.clicked.connect(self._reload_from_disk)
        path_layout.addWidget(reload_button)
        root.addWidget(path_row)

        profile_row = QWidget(self)
        profile_layout = QHBoxLayout(profile_row)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(8)
        self.profile_combo = QComboBox(self)
        self.profile_combo.setToolTip("Select a profile to edit")
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_layout.addWidget(self.profile_combo, 1)

        add_button = QPushButton("Add", profile_row)
        add_button.setToolTip("Create a new profile")
        add_button.clicked.connect(self._add_profile)
        profile_layout.addWidget(add_button)

        dup_button = QPushButton("Duplicate", profile_row)
        dup_button.setToolTip("Duplicate the current profile")
        dup_button.clicked.connect(self._duplicate_profile)
        profile_layout.addWidget(dup_button)

        del_button = QPushButton("Delete", profile_row)
        del_button.setToolTip("Delete the current profile")
        del_button.clicked.connect(self._delete_profile)
        profile_layout.addWidget(del_button)
        root.addWidget(profile_row)

        self.tabs = QTabWidget(self)
        self.tabs.currentChanged.connect(self._update_help)
        root.addWidget(self.tabs, 1)

        self.help_view = QTextBrowser(self)
        self.help_view.setMinimumHeight(150)
        self.help_view.setOpenExternalLinks(True)
        self.help_view.setReadOnly(True)
        root.addWidget(self.help_view)

        self._build_identity_tab()
        self._build_delivery_tab()
        self._build_sources_tab()
        self._build_templates_tab()
        self._build_filters_tab()
        self._build_flags_tab()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Help,
            parent=self,
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button:
            save_button.setText("Save")
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        buttons.helpRequested.connect(self._show_help)
        root.addWidget(buttons)

        self._reload_profiles(initial_profile)

    def _normalize_config_data(self, data: ConfigProfile) -> ConfigProfile:
        normalized: ConfigProfile = {}
        for name, profile in data.items():
            if isinstance(profile, dict):
                normalized[str(name)] = dict(profile)
        return normalized

    def _default_profile_data(
        self,
    ) -> dict[str, str | int | list[str] | dict[str, str]]:
        return {
            "MAILCONFIG": "",
            "username": "jdoe",
            "password": "",
            "sender": "john.doe@example.com",
            "sendername": "John Doe",
            "subject": "",
            "message": "",
            "body": "",
            "database": "subscribers.csv",
            "default_documents_path": "",
            "sa": "",
            "sheetid": "",
            "domain": "example.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "imap_host": "imap.example.com",
            "imap_port": 993,
            "sent_folder": "Sent",
            "token_file": "",
            "scopes": [],
            "credentials_id": "",
            "pause": 1,
            "default_message": "Hello",
            "styles": "./css/styles.css",
            "filter": {
                "email": "is not empty",
                "bounced": "is not bounced",
                "cotisation": "greater than 0",
                "first_name": 'one of "Jean", "Xavier"',
            },
            "filter_test": {"email": "is john.doe@example.com"},
            "from_index": 0,
            "to_index": 0,
            "wait": 0,
            "max_mails_per_hour": 1000,
            "max_addr_per_mail": 50,
            "test": False,
            "verbose": False,
            "doNotSend": False,
            "selected": False,
            "md2html": False,
            "keep-html": False,
        }

    def _ensure_profiles(self) -> None:
        if not self._config_data:
            self._config_data = {"default": self._default_profile_data()}
        elif "default" not in self._config_data:
            self._config_data["default"] = self._default_profile_data()

    def _reload_profiles(self, preferred_profile: str | None = None) -> None:
        self._config_data = self._read_config_file(self.config_input.text().strip())
        self._ensure_profiles()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(list(self._config_data.keys()))
        self.profile_combo.blockSignals(False)

        target = preferred_profile or self._current_profile or "default"
        idx = self.profile_combo.findText(target)
        self.profile_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._load_profile(self.profile_combo.currentText())

    def _reload_from_disk(self) -> None:
        self._reload_profiles(self.profile_combo.currentText() or "default")

    def _read_config_file(
        self, path: str
    ) -> dict[str, dict[str, str | int | list[str] | dict[str, str]]]:
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return self._normalize_config_data(data if isinstance(data, dict) else {})
        except Exception as exc:
            try:
                QMessageBox.warning(
                    self, _CONFIG_ERROR, f"Could not load config:\n{exc}"
                )
            except Exception as e:
                log.debug("Could not show warning dialog: %s", e)
            return {}

    def _browse_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select sendMail config",
            (
                str(Path(self.config_input.text()).parent)
                if self.config_input.text()
                else str(Path.home())
            ),
            "YAML Files (*.yml *.yaml);;All Files (*)",
        )
        if path:
            self.config_input.setText(path)
            self._reload_profiles("default")

    def _build_tab(self, title: str) -> tuple[QWidget, QFormLayout]:
        tab = QWidget(self)
        layout = QFormLayout(tab)
        layout.setLabelAlignment(layout.labelAlignment())
        self.tabs.addTab(tab, title)
        return tab, layout

    def _configure_line_edit(self, edit: QLineEdit, spec: _LineFieldSpec) -> None:
        if spec.password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        if spec.placeholder:
            edit.setPlaceholderText(spec.placeholder)
        if spec.tooltip:
            edit.setToolTip(spec.tooltip)

    def _add_browse_button_to_row(
        self,
        row_layout: QHBoxLayout,
        edit: QLineEdit,
        row: QWidget,
        spec: _LineFieldSpec,
    ) -> None:
        browse_button = QPushButton("Browse", row)
        browse_button.setToolTip(spec.tooltip or spec.browse_caption or "Browse")

        def _pick_path() -> None:
            start_dir = (
                str(Path(edit.text()).parent) if edit.text() else str(Path.home())
            )
            if spec.browse_type == "directory":
                path = QFileDialog.getExistingDirectory(
                    self, spec.browse_caption, start_dir
                )
            else:
                path, _ = QFileDialog.getOpenFileName(
                    self, spec.browse_caption, start_dir, spec.browse_filter
                )
            if path:
                edit.setText(path)

        browse_button.clicked.connect(_pick_path)
        row_layout.addWidget(browse_button)

    def _add_line_field(
        self,
        layout: QFormLayout,
        spec: _LineFieldSpec,
    ) -> QLineEdit:
        edit = QLineEdit(self)
        edit.setMinimumWidth(300)
        self._configure_line_edit(edit, spec)

        if spec.browse_caption:
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            row_layout.addWidget(edit, 1)
            self._add_browse_button_to_row(row_layout, edit, row, spec)
            layout.addRow(spec.label, row)
        else:
            layout.addRow(spec.label, edit)

        self._widgets[spec.key] = edit
        return edit

    def _add_spin_field(
        self,
        layout: QFormLayout,
        key: str,
        label: str,
        *,
        tooltip: str = "",
        minimum: int = 0,
        maximum: int = 1_000_000,
    ) -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(minimum, maximum)
        if tooltip:
            spin.setToolTip(tooltip)
        layout.addRow(label, spin)
        self._widgets[key] = spin
        return spin

    def _add_check_field(
        self,
        layout: QFormLayout,
        key: str,
        label: str,
        *,
        tooltip: str = "",
    ) -> QCheckBox:
        check = QCheckBox(label, self)
        if tooltip:
            check.setToolTip(tooltip)
        layout.addRow("", check)
        self._widgets[key] = check
        return check

    def _add_text_field(
        self,
        layout: QFormLayout,
        key: str,
        label: str,
        *,
        tooltip: str = "",
        placeholder: str = "",
        minimum_height: int = 120,
    ) -> QPlainTextEdit:
        edit = QPlainTextEdit(self)
        if tooltip:
            edit.setToolTip(tooltip)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(minimum_height)
        layout.addRow(label, edit)
        self._widgets[key] = edit
        return edit

    def _build_identity_tab(self) -> None:
        _, layout = self._build_tab("Identity")
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "MAILCONFIG", "MAILCONFIG", tooltip="Secret name used by getSecrets()."
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "sender", "Sender", tooltip="Email address used in the From header."
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "sendername", "Sender name", tooltip="Display name for the sender."
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec("username", "Username", tooltip="SMTP or IMAP login user."),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "password", "Password", tooltip="SMTP or IMAP password.", password=True
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "domain", "Domain", tooltip="Message-ID domain for generated emails."
            ),
        )

    def _build_delivery_tab(self) -> None:
        _, layout = self._build_tab("Delivery")
        self._add_line_field(
            layout,
            _LineFieldSpec("smtp_host", "SMTP host", tooltip="SMTP server hostname."),
        )
        self._add_spin_field(
            layout,
            "smtp_port",
            "SMTP port",
            tooltip="SMTP server port.",
            minimum=0,
            maximum=65535,
        )
        self._add_line_field(
            layout,
            _LineFieldSpec("imap_host", "IMAP host", tooltip="IMAP server hostname."),
        )
        self._add_spin_field(
            layout,
            "imap_port",
            "IMAP port",
            tooltip="IMAP server port.",
            minimum=0,
            maximum=65535,
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "sent_folder",
                "Sent folder",
                tooltip="Remote IMAP folder used to archive sent mail.",
            ),
        )

    def _build_sources_tab(self) -> None:
        _, layout = self._build_tab("Sources")
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "database",
                "Database",
                tooltip="Local subscriber file path (CSV/XLSX/XLSM/XLS/ODS).",
                browse_caption="Select database",
                browse_filter="Data Files (*.csv *.xlsx *.xlsm *.xls *.ods);;All Files (*)",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "default_documents_path",
                "Default Documents Path",
                tooltip="Default folder for Save As dialogs in the editor (per-profile). Defaults to Documents folder (Windows) or home directory (macOS/Linux).",
                browse_caption="Select default folder",
                browse_filter="",
                browse_type="directory",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "sa",
                "Service account (SA)",
                tooltip="Secret key name for Google service account JSON.",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "sheetid",
                "Sheet ID",
                tooltip="Secret key name for the Google Sheet identifier.",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "mail",
                "Email",
                tooltip="Gmail account email address for sending via Gmail API.",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "folder",
                "Gmail Folder",
                tooltip="Gmail folder name for storing messages to send.",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "members",
                "Members Endpoint",
                tooltip="URL endpoint for retrieving member data.",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "token_file",
                "Token file",
                tooltip="Path to the Gmail OAuth token file.",
                browse_caption="Select token file",
                browse_filter="JSON/YAML Files (*.json *.yml *.yaml);;All Files (*)",
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "token_id", "Token ID", tooltip="Secret key name for Gmail OAuth token."
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "credentials_id",
                "Credentials ID",
                tooltip="Secret key name for Gmail OAuth client config.",
            ),
        )
        self._add_text_field(
            layout,
            "scopes",
            "Scopes",
            tooltip="One OAuth scope per line. Commas are also accepted.",
            placeholder="https://www.googleapis.com/auth/gmail.send",
            minimum_height=100,
        )

    def _build_templates_tab(self) -> None:
        _, layout = self._build_tab("Templates")
        self._add_line_field(
            layout,
            _LineFieldSpec("subject", "Subject", tooltip="Optional default subject."),
        )
        self._add_text_field(
            layout,
            "message",
            "Message",
            tooltip="Primary message template used by sendMail.",
            placeholder="Mail body / template text",
            minimum_height=120,
        )
        self._add_text_field(
            layout,
            "default_message",
            "Default message",
            tooltip="Fallback template used when message is empty.",
            placeholder="Hello",
            minimum_height=120,
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "body", "Body", tooltip="Optional body replacement text for ${body}."
            ),
        )
        self._add_line_field(
            layout,
            _LineFieldSpec(
                "styles",
                "Stylesheet",
                tooltip="Path to the CSS stylesheet used for HTML conversion.",
                browse_caption="Select stylesheet",
                browse_filter="CSS Files (*.css);;All Files (*)",
            ),
        )
        self._add_spin_field(
            layout,
            "pause",
            "Pause (sec)",
            tooltip="Pause between batches, in seconds.",
            minimum=0,
            maximum=3600,
        )
        self._add_spin_field(
            layout,
            "from_index",
            "From index",
            tooltip="Starting subscriber row.",
            minimum=0,
        )
        self._add_spin_field(
            layout,
            "to_index",
            "To index",
            tooltip="Stopping subscriber row.",
            minimum=0,
        )
        self._add_spin_field(
            layout,
            "wait",
            "Wait (min)",
            tooltip="Wait before restarting, in minutes.",
            minimum=0,
        )
        self._add_spin_field(
            layout,
            "max_mails_per_hour",
            "Max mails/hour",
            tooltip="Hourly sending limit.",
            minimum=1,
        )
        self._add_spin_field(
            layout,
            "max_addr_per_mail",
            "Max addr/mail",
            tooltip="Maximum recipient addresses per email.",
            minimum=1,
        )

    def _build_filters_tab(self) -> None:
        _, layout = self._build_tab("Filters")
        self._add_text_field(
            layout,
            "filter",
            "filter",
            tooltip="YAML mapping used as the active filter set.",
            placeholder="email: is not empty",
            minimum_height=150,
        )
        self._add_text_field(
            layout,
            "filter_test",
            "filter_test",
            tooltip="YAML mapping used when test mode is enabled.",
            placeholder="email: is john.doe@example.com",
            minimum_height=120,
        )

    def _build_flags_tab(self) -> None:
        _, layout = self._build_tab("Flags")
        self._add_check_field(layout, "test", "Test", tooltip="Enable test mode.")
        self._add_check_field(
            layout, "verbose", "Verbose", tooltip="Increase logging verbosity."
        )
        self._add_check_field(
            layout, "doNotSend", "Do not send", tooltip="Suppress actual sending."
        )
        self._add_check_field(
            layout,
            "md2html",
            "md2html",
            tooltip="Keep the Markdown-to-HTML compatibility flag.",
        )
        self._add_check_field(
            layout, "keep-html", "keep-html", tooltip="Preserve generated HTML output."
        )

    def _profile_names(self) -> list[str]:
        return list(self._config_data.keys())

    def _profile_value(self, profile: str) -> dict[str, object]:
        value = self._config_data.get(profile, {})
        normalized: dict[str, object] = {}
        for k, v in value.items():
            normalized[str(k).lower()] = v
        return normalized

    def _dump_yaml_block(self, value: object) -> str:
        if value in (None, ""):
            return ""
        try:
            result: str = yaml.safe_dump(
                value, sort_keys=False, allow_unicode=True
            ).strip()
            return result
        except Exception:
            return str(value)

    def _load_yaml_block(self, text: str, field_name: str) -> object:
        raw = text.strip()
        if not raw:
            return {} if field_name in self._yaml_keys else []
        try:
            data = yaml.safe_load(raw)
        except Exception as exc:
            raise ValueError(f"Invalid YAML in {field_name}: {exc}") from exc
        if field_name in self._yaml_keys:
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise ValueError(f"{field_name} must be a YAML mapping")
            return data
        if field_name in self._list_keys:
            if data is None:
                return []
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
            return [part.strip() for part in re.split(r"[\n,]+", raw) if part.strip()]
        return data

    def _load_widget_line_edit(self, widget: QLineEdit, value: object) -> None:
        widget.setText("" if value is None else str(value))

    def _load_widget_spin_box(
        self, widget: QSpinBox, value: object, default: int
    ) -> None:
        try:
            if isinstance(value, int):
                widget.setValue(value)
            elif isinstance(value, str):
                widget.setValue(int(value))
            else:
                widget.setValue(int(str(value)))
        except (ValueError, TypeError):
            widget.setValue(default)

    def _load_widget_check_box(self, widget: QCheckBox, value: object) -> None:
        widget.setChecked(bool(value))

    def _load_widget_plain_text(
        self, widget: QPlainTextEdit, value: object, key: str
    ) -> None:
        if key in self._yaml_keys:
            widget.setPlainText(self._dump_yaml_block(value))
        elif key in self._list_keys:
            self._load_widget_plain_text_list(widget, value)
        else:
            widget.setPlainText("" if value is None else str(value))

    def _load_widget_plain_text_list(
        self, widget: QPlainTextEdit, value: object
    ) -> None:
        if isinstance(value, list):
            widget.setPlainText(
                "\n".join(str(item) for item in value if str(item).strip())
            )
        elif value:
            widget.setPlainText(str(value))
        else:
            widget.setPlainText("")

    def _get_config_value_for_widget(
        self, key: str, widget: QWidget, cfg: ConfigData, defaults: ConfigData
    ) -> object:
        if key in cfg:
            return cfg[key]
        if isinstance(widget, QSpinBox):
            return defaults.get(key, "")
        return None

    def _get_spinbox_default_value(
        self, key: str, cfg: ConfigData, defaults: ConfigData
    ) -> int:
        val = defaults.get(key, 0) if key in cfg else 0
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            try:
                return int(val)
            except ValueError:
                return 0
        return 0

    def _load_widget_by_type(
        self,
        widget: QWidget,
        key: str,
        value: object,
        cfg: ConfigData,
        defaults: ConfigData,
    ) -> None:
        if isinstance(widget, QLineEdit):
            self._load_widget_line_edit(widget, value)
        elif isinstance(widget, QSpinBox):
            default_val = self._get_spinbox_default_value(key, cfg, defaults)
            self._load_widget_spin_box(widget, value, default_val)
        elif isinstance(widget, QCheckBox):
            self._load_widget_check_box(widget, value)
        elif isinstance(widget, QPlainTextEdit):
            self._load_widget_plain_text(widget, value, key)

    def _load_profile(self, profile: str) -> None:
        if not profile:
            return
        self._current_profile = profile
        cfg = self._profile_value(profile)
        defaults = self._default_profile_data()

        for key, widget in self._widgets.items():
            value = self._get_config_value_for_widget(key, widget, cfg, defaults)  # type: ignore
            self._load_widget_by_type(widget, key, value, cfg, defaults)  # type: ignore

        current_index = self.tabs.currentIndex()
        if current_index >= 0:
            self._update_help(current_index)

    def _collect_profile_data(self) -> dict[str, object]:
        original_profile = self._config_data.get(self._current_profile, {})
        original_case_map = (
            {str(k).lower(): k for k in original_profile.keys()}
            if isinstance(original_profile, dict)
            else {}
        )

        base: dict[str, object] = {}
        for key, widget in self._widgets.items():
            original_key = original_case_map.get(key.lower(), key)
            if isinstance(widget, QLineEdit):
                value: object = widget.text().strip()
            elif isinstance(widget, QSpinBox):
                value = widget.value()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QPlainTextEdit):
                value = self._load_yaml_block(widget.toPlainText(), key)
            else:
                continue
            if value or value == 0 or value is False:
                base[original_key] = value
        return base

    def _persist_current_profile(self) -> None:
        if not self._current_profile:
            return
        self._config_data[self._current_profile] = self._collect_profile_data()  # type: ignore

    def _on_profile_changed(self, profile: str) -> None:
        if not profile:
            return
        if self._current_profile and profile != self._current_profile:
            self._persist_current_profile()
        self._load_profile(profile)

    def _new_profile_name(self, title: str, default: str) -> str | None:
        name, ok = QInputDialog.getText(self, title, "Profile name:", text=default)
        if not ok:
            return None
        name = name.strip()
        if not name:
            return None
        return name

    def _add_profile(self) -> None:
        name = self._new_profile_name("Add Profile", "new-profile")
        if not name:
            return
        self._persist_current_profile()
        if name in self._config_data:
            QMessageBox.warning(
                self, "Profile Exists", f"Profile '{name}' already exists."
            )
            return
        self._config_data[name] = self._default_profile_data()
        self._reload_profiles(name)

    def _duplicate_profile(self) -> None:
        if not self._current_profile:
            return
        name = self._new_profile_name(
            "Duplicate Profile", f"{self._current_profile}-copy"
        )
        if not name:
            return
        self._persist_current_profile()
        if name in self._config_data:
            QMessageBox.warning(
                self, "Profile Exists", f"Profile '{name}' already exists."
            )
            return
        self._config_data[name] = self._collect_profile_data()  # type: ignore
        self._reload_profiles(name)

    def _delete_profile(self) -> None:
        if not self._current_profile:
            return
        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete profile '{self._current_profile}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._config_data.pop(self._current_profile, None)
        if not self._config_data:
            self._config_data = {"default": self._default_profile_data()}
        self._reload_profiles(next(iter(self._config_data.keys())))

    def _update_help(self, index: int) -> None:
        title = self.tabs.tabText(index) if index >= 0 else "Identity"
        self.help_view.setHtml(self._TAB_HELP.get(title, ""))

    def _show_help(self) -> None:
        message = (
            "<h3>Config editor help</h3>"
            "<p>This dialog edits the YAML profiles used by sendMail.</p>"
            "<ul>"
            "<li>Each top-level YAML key is a profile name.</li>"
            "<li>Unknown keys are preserved when saving.</li>"
            "<li>Use <b>Scopes</b> one per line.</li>"
            "<li><b>filter</b> and <b>filter_test</b> must be YAML mappings.</li>"
            "<li>The config file path can be changed with <b>Browse</b>.</li>"
            "</ul>"
        )
        QMessageBox.information(self, "Settings Help", message)

    def _save_config(self) -> None:
        self._persist_current_profile()
        path = self.config_input.text().strip()
        if not path:
            raise ValueError("No config file path selected")
        output = {}
        for profile in self._profile_names():
            output[profile] = self._profile_value(profile)
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(path_obj, "w", encoding="utf-8") as f:
            yaml.safe_dump(output, f, sort_keys=False, allow_unicode=True)

    def _save_and_accept(self) -> None:
        try:
            self._save_config()
        except Exception as exc:
            QMessageBox.critical(
                self, "Save Error", f"Could not save configuration:\n{exc}"
            )
            return
        self.accept()


# ---------------------------------------------------------------------------
# Profile, Clipboard, and Session Management
# ---------------------------------------------------------------------------


class ConfigLoader:
    """Load email profiles from config.yml."""

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.profiles: dict[str, dict[str, Any]] = {}
        self.load_profiles_from_config()

    def load_profiles_from_config(self) -> None:
        """Load profiles from config.yml and parse default_documents_path field."""
        try:
            if not os.path.exists(self.config_path):
                log.warning("Config file not found: %s", self.config_path)
                return
            with open(self.config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            for profile_name, profile_config in config.items():
                if isinstance(profile_config, dict):
                    self.profiles[profile_name] = {
                        "name": profile_name,
                        "default_documents_path": profile_config.get(
                            "default_documents_path"
                        ),
                        "config": profile_config,
                    }
        except Exception as exc:
            log.warning("Failed to load profiles from config: %s", exc)

    def get_profiles(self) -> dict[str, dict[str, Any]]:
        """Return loaded profiles."""
        return self.profiles


@dataclass
class ClipboardOperation:
    """Represents clipboard paste operation with content analysis."""

    content_type: str  # "html_rich", "plain_text", "markdown"
    has_urls: bool
    detected_urls: list[str]
    has_existing_links: bool
    raw_html: str | None
    raw_text: str


class ClipboardProcessor:
    """Analyze clipboard content for content type and URL detection."""

    URL_PATTERN = r"https?://[^\s<>\"{}|\\^`\[\]]+|ftp://[^\s<>\"{}|\\^`\[\]]+"

    def analyze_paste(
        self, raw_text: str, raw_html: str | None = None
    ) -> ClipboardOperation:
        """Determine clipboard content type and detect URLs."""
        has_existing_links = self._check_existing_links(raw_html) if raw_html else False
        detected_urls: list[str] = []

        if raw_html and "<a" in raw_html:
            content_type = "html_rich"
        elif raw_html:
            content_type = "html_rich"
        elif self._is_markdown_link(raw_text):
            content_type = "markdown"
        else:
            content_type = "plain_text"
            detected_urls = self.detect_urls_in_text(raw_text)

        return ClipboardOperation(
            content_type=content_type,
            has_urls=len(detected_urls) > 0,
            detected_urls=detected_urls,
            has_existing_links=has_existing_links,
            raw_html=raw_html,
            raw_text=raw_text,
        )

    def detect_urls_in_text(self, text: str) -> list[str]:
        """Find http(s)/ftp URLs in plain text."""
        return re.findall(self.URL_PATTERN, text)

    def _check_existing_links(self, html: str) -> bool:
        """Check if HTML contains link markup."""
        return bool(re.search(r"<a\s+[^>]*href\s*=", html))

    def _is_markdown_link(self, text: str) -> bool:
        """Check if text is already in markdown link format [text](url)."""
        return bool(re.search(r"\[.+\]\(.+\)", text))

    def detect_html_links(self, html: str) -> list[str]:
        """Extract URLs from HTML link attributes."""
        return re.findall(r'href\s*=\s*["\']([^"\']+)["\']', html)


@dataclass
class EditorSession:
    """Track editor runtime state."""

    active_profile_name: str | None = None
    active_document_path: str | None = None
    active_profile_default_path: str | None = None
    unsaved_changes: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "active_profile_name": self.active_profile_name,
            "active_document_path": self.active_document_path,
            "active_profile_default_path": self.active_profile_default_path,
            "unsaved_changes": self.unsaved_changes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EditorSession:
        """Create from dict loaded from JSON."""
        return cls(
            active_profile_name=data.get("active_profile_name"),
            active_document_path=data.get("active_document_path"),
            active_profile_default_path=data.get("active_profile_default_path"),
            unsaved_changes=data.get("unsaved_changes", False),
        )


class EditorPasteHandler:
    """Handle paste operations with link preservation and URL linkification."""

    def __init__(self, clipboard_processor: ClipboardProcessor) -> None:
        self.processor = clipboard_processor

    def handle_paste(self, clipboard_op: ClipboardOperation) -> dict[str, Any]:
        """Process paste operation and return instructions for Quill."""
        if clipboard_op.content_type == "html_rich":
            return {"action": "paste_html", "html": clipboard_op.raw_html}
        elif clipboard_op.content_type == "plain_text" and clipboard_op.has_urls:
            linkified_html = self.linkify_urls(
                clipboard_op.raw_text, clipboard_op.detected_urls
            )
            return {
                "action": "linkify_urls",
                "text": clipboard_op.raw_text,
                "urls": clipboard_op.detected_urls,
                "html": linkified_html,
            }
        else:
            return {"action": "paste_text", "text": clipboard_op.raw_text}

    def linkify_urls(self, text: str, urls: list[str]) -> str:
        """Convert plain-text URLs to HTML links, return linkified HTML."""
        if not urls:
            return text
        html = text
        for url in urls:
            html = html.replace(url, f'<a href="{url}" target="_blank">{url}</a>')
        return html


# ---------------------------------------------------------------------------
# JS ↔ Python bridge
# ---------------------------------------------------------------------------
class EditorBridge(QObject):
    """QWebChannel bridge for communication with Quill.js editor.

    Registered with QWebChannel as "bridge". Provides slots callable from
    JavaScript for image insertion, file operations, and content changes.

    Signals:
        dirty_changed: Emitted when content modification state changes
        css_changed: Emitted when user selects custom CSS stylesheet
        clipboard_analyzed: Emitted when JS detects clipboard content on paste
    """

    dirty_changed = pyqtSignal(bool)
    css_changed = pyqtSignal(
        str
    )  # emits absolute CSS file path when user selects a stylesheet
    clipboard_analyzed = pyqtSignal(
        str, bool, list
    )  # content_type, has_html_links, detected_urls

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

    @pyqtSlot(result=str)  # type: ignore
    def request_image_insert(self) -> str:
        """
        Opens a file dialog and returns a base64 data URI for the chosen image.
        Returns "" if the user cancels.
        """
        parent_obj = self.parent()
        try:
            parent_widget: QWidget | None = (
                parent_obj if isinstance(parent_obj, QWidget) else None
            )
        except TypeError:
            parent_widget = None
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
                mimetype = sm.guess_type(path) or _DEFAULT_MIME_TYPE
            else:
                import base64
                import mimetypes

                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                mimetype = mimetypes.guess_type(path)[0] or _DEFAULT_MIME_TYPE
            return f"data:{mimetype};base64,{b64}"
        except Exception as exc:
            log.error("Image insert failed: %s", exc)
            return ""

    @pyqtSlot(str, result=str)  # type: ignore
    def request_link_insert(self, selected_text: str) -> str:
        """
        Opens a link dialog pre-filled with *selected_text*.
        Returns a JSON string {"url": "...", "text": "..."} on confirm,
        or "" on cancel.
        """
        parent_obj = self.parent()
        try:
            parent_widget: QWidget | None = (
                parent_obj if isinstance(parent_obj, QWidget) else None
            )
        except TypeError:
            parent_widget = None
        dialog = _LinkDialog(parent_widget, selected_text=selected_text)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return ""
        url = dialog.get_url()
        if not url:
            return ""
        return json.dumps({"url": url, "text": dialog.get_text()})

    @pyqtSlot(result=str)  # type: ignore
    def request_table_insert(self) -> str:
        """
        Opens a dialog asking for table dimensions.
        Returns JSON string {"rows": n, "cols": m} on confirm, or "" on cancel.
        """
        parent_obj = self.parent()
        try:
            parent_widget: QWidget | None = (
                parent_obj if isinstance(parent_obj, QWidget) else None
            )
        except TypeError:
            parent_widget = None
        dialog = _TableDialog(parent_widget)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return ""
        return json.dumps({"rows": dialog.get_rows(), "cols": dialog.get_cols()})

    @pyqtSlot(str)
    def log_js_error(self, msg: str) -> None:
        """Receives JS-side errors forwarded via window.onerror."""
        log.warning("JS: %s", msg)

    @pyqtSlot(str, bool, list)
    def on_clipboard_analyzed(
        self, content_type: str, has_html_links: bool, detected_urls: list[str]
    ) -> None:
        """Receives clipboard analysis result from JavaScript paste handler."""
        self.clipboard_analyzed.emit(content_type, has_html_links, detected_urls)

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
class EditorWindow(QMainWindow):  # pragma: no cover  # type: ignore[misc]
    """Main WYSIWYG newsletter editor window.

    Desktop application for composing and editing HTML newsletters.
    Uses Quill.js for rich text editing in QWebEngineView.
    Supports inline images, attachments, CSS customization, and sendMail output.

    Args:
        file_path: Optional markdown or HTML file to open on startup
    """

    def __init__(
        self, file_path: str | None = None, profile: str | None = None
    ) -> None:
        super().__init__()
        self._file_path: str | None = None
        self._css_path: str | None = None  # user-selected CSS stylesheet
        self._load_finished_connected = False
        self._send_in_progress = False
        self._is_template = False
        # Use same config path as Send mailing dialog (not hardcoded src/config.yml)
        self._config_path = self._resolve_send_config_path()
        self._config_data: dict[
            str, dict[str, str | int | list[str] | dict[str, str]]
        ] = {}
        self._current_profile = profile or "default"
        self._default_documents_path = self._get_default_documents_path()
        self._load_config()

        # Profile loader and session management (new for 005-editor-profile-clipboard)
        self._config_loader = ConfigLoader(self._config_path)
        self._clipboard_processor = ClipboardProcessor()
        self._paste_handler = EditorPasteHandler(self._clipboard_processor)
        self._editor_session = EditorSession()
        self._profile_selector: QComboBox | None = None
        self._load_editor_session()

        # Web engine view
        self._view = QWebEngineView(self)
        self.setCentralWidget(self._view)

        # Web channel + bridge
        self._channel = QWebChannel(self)
        self._bridge = EditorBridge(parent=self)
        self._channel.registerObject("bridge", self._bridge)
        page = self._view.page()
        if page:
            page.setWebChannel(self._channel)

        # Connect signals
        self._bridge.dirty_changed.connect(self._on_dirty_changed)
        self._bridge.css_changed.connect(self._on_css_changed)
        self._bridge.clipboard_analyzed.connect(self._on_clipboard_analyzed)

        # Build menus and status bar
        self._build_menus()
        self._build_toolbars()
        self.setStatusBar(QStatusBar(self))
        self._css_status_label = QLabel("")
        statusbar = self.statusBar()
        if statusbar:
            statusbar.addPermanentWidget(self._css_status_label)

        # Window setup
        self.setMinimumSize(960, 720)
        self._update_title()

        # Open file or blank editor
        if file_path:
            self.open_file(file_path)
        else:
            self._load_editor_page("")

    # ------------------------------------------------------------------
    # Configuration & Path Handling
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load sendMail YAML config and extract default documents path for current profile."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, encoding="utf-8") as f:
                    self._config_data = yaml.safe_load(f) or {}
                profile_cfg = self._config_data.get(self._current_profile, {})
                stored_path_raw = profile_cfg.get("default_documents_path", "")
                if isinstance(stored_path_raw, str) and stored_path_raw:
                    if self._validate_documents_path(stored_path_raw):
                        self._default_documents_path = stored_path_raw
                    else:
                        log.warning(
                            "Invalid stored documents path: %s, using OS default",
                            stored_path_raw,
                        )
        except Exception as exc:
            log.warning("Failed to load config: %s", exc)

    def _get_default_documents_path(self) -> str:
        """Get OS-specific default documents folder (Windows: Documents, macOS/Linux: home)."""
        if sys.platform == "win32":
            return os.path.expandvars(r"%USERPROFILE%\Documents")
        return os.path.expanduser("~")

    def _validate_documents_path(self, path: str) -> bool:
        """Check if path exists and is readable/writable."""
        try:
            return os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK)
        except Exception:
            return False

    def _get_stylesheet_path(self) -> Path:
        """Get stylesheet path: profile's styles → HOME/css/styles.css → project default."""
        # Try to get from current profile config
        if hasattr(self, "_current_profile") and hasattr(self, "_config_data"):
            profile_cfg = self._config_data.get(self._current_profile, {})
            profile_styles = profile_cfg.get("styles")
            if profile_styles and isinstance(profile_styles, str):
                styles_path = Path(profile_styles).expanduser().absolute()
                if styles_path.exists():
                    return styles_path

        # Try HOME/css/styles.css
        home_css = Path.home() / "css" / "styles.css"
        if home_css.exists():
            return home_css

        # Fall back to project default
        default_css = (
            (_BASE / "Resources" / "css" / "styles.css")
            if _IS_FROZEN
            else (_BASE / "css" / "styles.css")
        )
        return default_css

    def _get_css_directory(self) -> Path:
        """Get CSS directory: profile's styles dir → HOME/css → project default."""
        # Try to get directory from profile config
        if hasattr(self, "_current_profile") and hasattr(self, "_config_data"):
            profile_cfg = self._config_data.get(self._current_profile, {})
            profile_styles = profile_cfg.get("styles")
            if profile_styles and isinstance(profile_styles, str):
                styles_dir = Path(profile_styles).expanduser().absolute().parent
                if styles_dir.exists():
                    return styles_dir

        # Try HOME/css
        home_css_dir = Path.home() / "css"
        if home_css_dir.exists():
            return home_css_dir

        # Fall back to project default
        default_css_dir = (
            (_BASE / "Resources" / "css") if _IS_FROZEN else (_BASE / "css")
        )
        return default_css_dir

    def _resolve_stylesheet_path(self, styles_value: str) -> Path | None:
        """Resolve stylesheet path from config value, expanding user home and making absolute."""
        if not styles_value:
            return None
        try:
            path = Path(styles_value).expanduser().absolute()
            return path if path.exists() else None
        except Exception as exc:
            log.warning("Failed to resolve stylesheet path %r: %s", styles_value, exc)
            return None

    def _clear_profile_stylesheet(self) -> None:
        """Clear previously applied profile stylesheet."""
        if hasattr(self, "_view") and self._view:
            # Clear the user-css element by applying empty CSS (must happen BEFORE new stylesheet)
            self._run_js("""
            setTimeout(function() {
              if (typeof applyCSS === 'function') {
                applyCSS('');
              }
            }, 10);
            """)
        log.debug("Cleared profile stylesheet")

    def _apply_profile_stylesheet(self, css_path: Path) -> None:
        """Load and apply CSS stylesheet to editor canvas.

        Clears any previously applied stylesheet and applies the new one.
        Defers JS execution until page is ready.
        """
        try:
            with open(css_path, encoding="utf-8") as f:
                css_text = f.read()
            self._css_path = str(css_path)
            css_hash = hash(css_text) % 10000  # For debug logging
            log.info("Loading CSS (hash=%d): %s", css_hash, css_path)

            # Update status label if it exists (might not during initialization)
            if hasattr(self, "_css_status_label"):
                self._css_status_label.setText(f"CSS: {css_path.name}")
            # Defer JS call until page is ready (setTimeout ensures applyCSS is defined)
            if hasattr(self, "_view") and self._view:
                # Defer until after clear completes (clear uses 10ms, so apply at 200ms to be safe)
                script = f"""
                setTimeout(function() {{
                  if (typeof applyCSS === 'function') {{
                    applyCSS({json.dumps(css_text)});
                  }}
                }}, 200);
                """
                self._run_js(script)
                log.info(
                    "Queued stylesheet application (hash=%d): %s", css_hash, css_path
                )
            else:
                log.info(
                    "Deferred stylesheet application (UI not ready yet): %s", css_path
                )
        except Exception as exc:
            log.error("Failed to apply profile stylesheet %s: %s", css_path, exc)

    def _save_documents_path(self, path: str) -> None:
        """Save documents folder path to config for current profile (atomic write)."""
        try:
            if not hasattr(self, "_config_path") or not hasattr(self, "_config_data"):
                return
            if not os.path.isdir(path):
                log.warning("Documents path does not exist, not saving: %s", path)
                return
            if not self._config_data:
                self._load_config()
            if self._current_profile not in self._config_data:
                self._config_data[self._current_profile] = {}
            self._config_data[self._current_profile]["default_documents_path"] = path
            tmp_path = self._config_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config_data, f, default_flow_style=False, sort_keys=False
                )
            os.replace(tmp_path, self._config_path)
            if hasattr(self, "_default_documents_path"):
                self._default_documents_path = path
        except Exception as exc:
            log.error("Failed to save documents path: %s", exc)

    def _is_template_file(self, file_path: str) -> bool:
        """Check if file is a template (contains .template or matches template.* pattern)."""
        name_lower = Path(file_path).name.lower()
        return ".template" in name_lower or name_lower.startswith("template.")

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
            except Exception:  # noqa: S110
                pass
            self._load_finished_connected = False

        def _on_load_finished(ok: bool) -> None:
            # Disconnect self to ensure it fires only once
            try:
                self._view.loadFinished.disconnect(_on_load_finished)
            except Exception:  # noqa: S110
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
        page = self._view.page()
        if page:
            page.runJavaScript(f"setContent({safe_js_string})")
        # Re-apply user CSS after each page load (page reload clears injected styles)
        if self._css_path:
            try:
                with open(self._css_path, encoding="utf-8") as f:
                    css_text = f.read()
                self._run_js(f"applyCSS({json.dumps(css_text)})")
            except Exception:  # noqa: S110
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
        elif ext in (_HTML_EXT, ".htm"):
            body_html = self._html_to_body_html(path)
        else:
            QMessageBox.warning(
                self,
                "Unsupported File",
                f"Unsupported file type: {ext}\nOpen .md or .html files.",
            )
            return

        self._file_path = path
        self._is_template = self._is_template_file(path)
        self._bridge.reset(body_html)
        self._update_title()

        # Load default profile stylesheet if available
        self._load_default_stylesheet()

        self._load_editor_page(body_html)

        # Persist the opened file's directory to config
        self._save_documents_path(str(Path(path).parent))

    def _md_to_body_html(self, md_path: str) -> str:
        """Convert a .md file to an HTML body string."""
        if _SM_AVAILABLE:
            return self._md_to_body_html_sendmail(md_path)
        if _MD2_AVAILABLE:
            return self._md_to_body_html_markdown2(md_path)
        QMessageBox.warning(
            self,
            "Markdown Not Available",
            "Cannot import markdown — MD conversion disabled. Install 'markdown2' package.",
        )
        return ""

    def _md_to_body_html_sendmail(self, md_path: str) -> str:
        """Convert .md using sendMail.md2html."""
        html_path = None
        try:
            html_path = sm.md2html(md_path, styles=None, embed_styles=False)
            if not html_path or not os.path.exists(html_path):
                log.error("md2html produced no output for: %s", md_path)
                return ""
            return self._html_to_body_html(html_path)
        except Exception as exc:
            log.error("sendMail MD conversion failed: %s", exc)
            return ""
        finally:
            if html_path and os.path.exists(html_path) and html_path != md_path:
                try:
                    os.remove(html_path)
                except OSError:  # noqa: S110
                    pass

    def _md_to_body_html_markdown2(self, md_path: str) -> str:
        """Convert .md using markdown2 library, with image inlining."""
        try:
            with open(md_path, encoding="utf-8") as f:
                md_content = f.read()
            html_body = markdown2.markdown(md_content)
            if not isinstance(html_body, str):
                return ""

            base_dir = os.path.dirname(os.path.abspath(md_path))

            def _inline_images(m: re.Match[str]) -> str:
                src = m.group(1)
                if src.startswith("data:") or src.startswith("http"):
                    return m.group(0)
                img_path = (
                    os.path.join(base_dir, src) if not os.path.isabs(src) else src
                )
                try:
                    import base64
                    import mimetypes

                    mime = mimetypes.guess_type(img_path)[0] or _DEFAULT_MIME_TYPE
                    with open(img_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    return f'src="data:{mime};base64,{b64}"'
                except OSError:
                    return m.group(0)

            result: str = re.sub(r'src="([^"]*)"', _inline_images, html_body)
            result = self._normalize_table_cells(result)
            result = self._collapse_blank_paragraphs(result)
            result = self._anchors_to_spans(result)
            return result
        except Exception as exc:
            log.error("markdown2 conversion failed: %s", exc)
            return ""

    def _html_to_body_html(self, html_path: str) -> str:
        """Extract the <body> inner HTML, inlining images and normalising anchors/blank lines."""
        try:
            from bs4 import BeautifulSoup

            if _SM_AVAILABLE:
                content = sm.make_html_images_inline(html_path)
            else:
                content = self._inline_images_fallback(html_path)
            soup = BeautifulSoup(content, _HTML_PARSER)
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

        _empty_p = r"<p(?:[^>]*)?>(?:\s*<br\s*/?>)?\s*</p>"
        return re.sub(
            rf"({_empty_p})\s*(?:{_empty_p}\s*){{2,}}",
            r"\1\1",
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
                **{
                    "class": "editor-anchor",
                    "data-anchor-id": anchor_id,  # type: ignore[arg-type]
                    "title": f"Anchor: {anchor_id}",
                },
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

        def _replace(m: re.Match[str]) -> str:
            aid = m.group(1)
            return f'<a id="{aid}" name="{aid}"></a>'

        return re.sub(
            r'<span(?:(?!class="editor-anchor")[^>])*class="editor-anchor"(?:(?!data-anchor-id=)[^>])*data-anchor-id="([^"]+)"[^>]*>⚓</span>',
            _replace,
            html,
        )

    @staticmethod
    def _unwrap_cell_blocks(cell: Any, soup: Any, block_tags: tuple[str, ...]) -> None:
        """Unwrap block-level children in a table cell, inserting <br> between them."""
        while True:
            direct_blocks = [
                c for c in cell.children if getattr(c, "name", None) in block_tags
            ]
            if not direct_blocks:
                break
            for i, block in enumerate(direct_blocks):
                if i > 0:
                    block.insert_before(soup.new_tag("br"))
                block.unwrap()

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
        import secrets

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, _HTML_PARSER)
        block_tags = (
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "div",
            "blockquote",
            "pre",
        )

        for tr in soup.find_all("tr"):
            row_id = "row-" + secrets.token_hex(2)
            for cell in tr.find_all(["td", "th"], recursive=False):
                cell["data-row"] = row_id
                EditorWindow._unwrap_cell_blocks(cell, soup, block_tags)

        body = soup.find("body")
        return body.decode_contents() if body else str(soup)

    def _inline_images_fallback(self, html_path: str) -> str:
        """Inline local <img src> as base64 data URIs without the sendMail module."""
        import base64
        import mimetypes
        import re

        with open(html_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        base_dir = os.path.dirname(os.path.abspath(html_path))

        def _replace(m: re.Match[str]) -> str:
            src = m.group(1)
            if src.startswith("data:") or src.startswith("http"):
                return m.group(0)
            img_path = os.path.join(base_dir, src) if not os.path.isabs(src) else src
            try:
                mime = mimetypes.guess_type(img_path)[0] or _DEFAULT_MIME_TYPE
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                return f'src="data:{mime};base64,{b64}"'
            except OSError:
                return m.group(0)

        result: str = re.sub(r'src="([^"]*)"', _replace, content)
        return result

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
        if getattr(self, "_is_template", False):
            QMessageBox.information(
                self,
                "Read-Only Template",
                "Templates are read-only. Use Save As to create a new file from this template.",
            )
            return self._save_as()
        if not self._file_path:
            return self._save_as()

        body_html = self._spans_to_anchors(self._bridge.get_current_html())
        stem = Path(self._file_path).with_suffix("")
        html_path = str(stem) + _HTML_EXT

        try:
            self._write_html_file(html_path, body_html)
            self._file_path = html_path
            self._bridge.reset(body_html)
            self._update_title()
            page = self._view.page()
            if page:
                page.runJavaScript("markSaved()")
            statusbar = self.statusBar()
            if statusbar:
                statusbar.showMessage(f"Saved: {html_path}", 4000)
            log.info("Saved HTML: %s", html_path)
            self._save_documents_path(str(Path(html_path).parent))
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{exc}")
            log.error("Save failed: %s", exc)
            return False

    def _save_as(self) -> bool:
        """Prompt for an HTML filename then save. Returns True on success."""
        initial_dir = getattr(self, "_default_documents_path", "data")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            initial_dir,
            "HTML (*.html);;All Files (*)",
        )
        if not path:
            return False
        self._file_path = str(Path(path).with_suffix(_HTML_EXT))
        self._is_template = False
        result = self._save()
        if result:
            self._save_documents_path(str(Path(self._file_path).parent))
        return result

    def _write_html_file(self, path: str, body_html: str) -> None:
        """Write a complete HTML document file from body HTML."""
        # Use user-selected CSS if set; otherwise use profile/home/project default
        css_source = (
            Path(self._css_path) if self._css_path else self._get_stylesheet_path()
        )
        if css_source.exists():
            with open(css_source, encoding="utf-8") as f:
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

        self._build_file_menu(menubar)
        self._build_settings_menu(menubar)
        self._build_format_menu(menubar)
        self._build_table_menu(menubar)
        self._build_insert_menu(menubar)

    def _build_file_menu(self, menubar: Any) -> None:
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

    def _build_settings_menu(self, menubar: Any) -> None:
        settings_menu = menubar.addMenu("&Settings")
        assert settings_menu is not None

        edit_config_action = settings_menu.addAction("&Edit Config...")
        edit_config_action.triggered.connect(self._menu_edit_config)

    def _build_format_menu(self, menubar: Any) -> None:
        fmt_menu = menubar.addMenu("F&ormat")
        assert fmt_menu is not None

        bold_action = fmt_menu.addAction("&Bold")
        bold_action.setShortcut("Ctrl+B")
        bold_action.triggered.connect(
            lambda: self._run_js("quill.format('bold', !quill.getFormat().bold)")
        )

        italic_action = fmt_menu.addAction("&Italic")
        italic_action.setShortcut("Ctrl+I")
        italic_action.triggered.connect(
            lambda: self._run_js("quill.format('italic', !quill.getFormat().italic)")
        )

        underline_action = fmt_menu.addAction("&Underline")
        underline_action.setShortcut("Ctrl+U")
        underline_fmt = "quill.format('underline', !quill.getFormat().underline)"
        underline_action.triggered.connect(lambda: self._run_js(underline_fmt))

        strike_action = fmt_menu.addAction("&Strikethrough")
        strike_action.setShortcut("Ctrl+Shift+X")
        strike_action.triggered.connect(
            lambda: self._run_js("quill.format('strike', !quill.getFormat().strike)")
        )

        fmt_menu.addSeparator()

        for level in (1, 2, 3):
            h_action = fmt_menu.addAction(f"Heading &{level}")
            h_action.triggered.connect(
                lambda _checked=False, lvl=level: self._run_js(
                    f"quill.format('header', {lvl})"
                )  # noqa: ARG005
            )

        normal_action = fmt_menu.addAction("&Normal Paragraph")
        normal_action.triggered.connect(
            lambda: self._run_js("quill.format('header', false)")
        )

        fmt_menu.addSeparator()

        clean_action = fmt_menu.addAction("&Clear Formatting")
        clean_action.triggered.connect(lambda: self._run_js("quill.format('clean')"))

        fmt_menu.addSeparator()

        font_menu = fmt_menu.addMenu("&Font Family")
        font_menu.addAction("&Default").triggered.connect(
            lambda _checked=False: self._set_font_family(None)  # noqa: ARG005
        )
        for font_name in FONT_CHOICES:
            font_menu.addAction(font_name).triggered.connect(
                lambda _checked=False, family=font_name: self._set_font_family(
                    family
                )  # noqa: ARG005
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
        apply_css_action.setToolTip(
            "Choose a CSS file to style the editor and saved HTML"
        )
        apply_css_action.triggered.connect(self._menu_apply_css)

    def _build_table_menu(self, menubar: Any) -> None:
        tbl_menu = menubar.addMenu("&Table")
        assert tbl_menu is not None

        insert_tbl_action = tbl_menu.addAction(
            _svg_icon(_SVG_INSERT_TABLE), "&Insert Table..."
        )
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

    def _build_insert_menu(self, menubar: Any) -> None:
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
        quote_action.triggered.connect(
            lambda: self._run_js("quill.format('blockquote', true)")
        )

        code_action = ins_menu.addAction("&Code Block")
        code_action.triggered.connect(
            lambda: self._run_js("quill.format('code-block', true)")
        )

    def _build_toolbars(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # Profile selector dropdown (new for 005-editor-profile-clipboard)
        if hasattr(self, "_config_loader"):
            profile_label = QLabel("Profile: ")
            self._profile_selector = QComboBox(self)
            self._profile_selector.addItems(
                list(self._config_loader.get_profiles().keys())
            )
            self._profile_selector.currentTextChanged.connect(self._on_profile_selected)
            if (
                hasattr(self, "_current_profile")
                and self._current_profile in self._config_loader.get_profiles()
            ):
                self._profile_selector.setCurrentText(self._current_profile)
            toolbar.addWidget(profile_label)
            toolbar.addWidget(self._profile_selector)
            toolbar.addSeparator()

        style = self.style()
        if style:
            save_action = toolbar.addAction(
                style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
                "Save",
            )
            if save_action:
                save_action.setToolTip("Save the current HTML")
                save_action.triggered.connect(self._save)

        send_action = toolbar.addAction(_svg_icon(_SVG_SEND), "Send")
        if send_action:
            send_action.setToolTip("Save and send the edited file")
            send_action.triggered.connect(self._menu_send)

    # ------------------------------------------------------------------
    # Profile selection and session management (new for 005-editor-profile-clipboard)
    # ------------------------------------------------------------------

    def _on_profile_selected(self, profile_name: str) -> None:
        """Handle profile selection from dropdown.

        Updates default documents path and applies profile stylesheet if defined.
        """
        self._current_profile = profile_name
        profiles = self._config_loader.get_profiles()
        log.info("Profile selected: %s", profile_name)
        log.info("Available profiles: %s", list(profiles.keys()))
        if profile_name in profiles:
            profile_info = profiles[profile_name]
            log.debug(
                "Profile keys in config: %s", list(profile_info.keys())[:10]
            )  # First 10 keys
            default_path = profile_info.get("default_documents_path")
            log.debug(
                "Profile '%s' default_documents_path: %r", profile_name, default_path
            )
            # Use profile's path if set (not None and not empty); fallback to system default
            if default_path and default_path != "":
                self._default_documents_path = default_path
                self._editor_session.active_profile_default_path = default_path
                log.info("Updated editor default path to: %s", default_path)
            else:
                # Profile has no custom path set; use system default documents folder
                default_docs_path = self._get_default_documents_path()
                self._default_documents_path = default_docs_path
                self._editor_session.active_profile_default_path = default_docs_path
                log.info(
                    "Profile has no default_documents_path; using system default: %s",
                    default_docs_path,
                )

            # Apply profile stylesheet if defined (load directly from raw config, not transformed profile_info)
            # Always clear previous stylesheet first
            self._clear_profile_stylesheet()

            if hasattr(self, "_config_data") and profile_name in self._config_data:
                raw_profile = self._config_data[profile_name]
                styles_path = (
                    raw_profile.get("styles") if isinstance(raw_profile, dict) else None
                )
                log.info("Profile stylesheet path: %s", styles_path)
                if styles_path and isinstance(styles_path, str):
                    css_path = self._resolve_stylesheet_path(styles_path)
                    if css_path and css_path.exists():
                        self._apply_profile_stylesheet(css_path)
                        log.info("✓ Applied profile stylesheet: %s", css_path)
                    else:
                        log.warning("✗ Profile stylesheet not found: %s", styles_path)
                else:
                    log.info("Profile %s has no stylesheet defined", profile_name)

            self._editor_session.active_profile_name = profile_name
        self._save_editor_session()

    def _load_editor_session(self) -> None:
        """Load active profile and document state from session file."""
        session_file = Path.home() / ".claude" / "editor-session.json"
        try:
            if session_file.exists():
                with open(session_file, encoding="utf-8") as f:
                    session_data = json.load(f)
                self._editor_session = EditorSession.from_dict(session_data)
                if self._editor_session.active_profile_name:
                    self._current_profile = self._editor_session.active_profile_name
                if self._editor_session.active_profile_default_path:
                    self._default_documents_path = (
                        self._editor_session.active_profile_default_path
                    )
        except Exception as exc:
            log.debug("Failed to load editor session: %s", exc)

    def _save_editor_session(self) -> None:
        """Save active profile and document state to session file."""
        session_file = Path.home() / ".claude" / "editor-session.json"
        try:
            session_file.parent.mkdir(parents=True, exist_ok=True)
            self._editor_session.active_profile_name = self._current_profile
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(self._editor_session.to_dict(), f, indent=2)
        except Exception as exc:
            log.warning("Failed to save editor session: %s", exc)

    # ------------------------------------------------------------------
    # Menu action handlers
    # ------------------------------------------------------------------

    def _menu_open(self) -> None:
        if not self._ask_save_if_dirty():
            return
        # Use profile's default_documents_path; fallback to system default documents folder
        default_dir = (
            getattr(self, "_default_documents_path", None)
            or self._get_default_documents_path()
        )
        log.debug(
            "_menu_open: using directory: %r (current profile: %s)",
            default_dir,
            getattr(self, "_current_profile", "unknown"),
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            default_dir,
            "Supported files (*.md *.html *.htm);;Markdown (*.md);;HTML (*.html *.htm);;All Files (*)",
        )
        if path:
            self.open_file(path)

    def _open_template(self) -> None:
        """Open data/template.md if it exists, or browse templates from default_documents_path."""
        if not self._ask_save_if_dirty():
            return
        template_path = _BASE / "data" / "template.md"
        if template_path.exists():
            self.open_file(str(template_path))
        else:
            # Use profile's default_documents_path for template browsing; fallback to system default
            template_dir = (
                getattr(self, "_default_documents_path", None)
                or self._get_default_documents_path()
            )
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Template", template_dir, "Markdown (*.md);;HTML (*.html)"
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
                if cfg != -1:
                    return str(cfg)
            except Exception as exc:
                log.debug("Could not resolve sendMail config path: %s", exc)
        return str(Path.home() / ".config" / "sendMail.yml")

    def _load_send_config(
        self, config_path: str
    ) -> dict[str, dict[str, str | int | list[str] | dict[str, str]]]:
        """Load the sendMail YAML config file."""
        if not config_path or not os.path.exists(config_path):
            return {}
        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            QMessageBox.warning(self, _CONFIG_ERROR, f"Could not load config:\n{exc}")
            return {}

    def _load_default_stylesheet(self) -> None:
        """Load the current profile's stylesheet if available."""
        try:
            config_path = self._resolve_send_config_path()
            config_data = self._load_send_config(config_path)
            # Use current profile, fallback to "default" if not set
            profile_name = self._current_profile or "default"
            styles_path = config_data.get(profile_name, {}).get("styles")
            if styles_path and isinstance(styles_path, str):
                abs_path = os.path.abspath(styles_path)
                if os.path.exists(abs_path):
                    self._bridge.css_changed.emit(abs_path)
        except Exception as exc:
            log.debug("Could not load profile stylesheet: %s", exc)

    def _send_with_sendmail(self, dialog: _SendDialog) -> str:
        """Run sendMail with the options selected in the dialog."""
        args = dialog.build_args(dialog._config_data)
        if args.profile not in args.conf:
            raise ValueError(f"Profile '{args.profile}' not found in config")

        dialog_password = dialog.password_input.text().strip()
        if dialog_password:
            args.conf[args.profile]["password"] = dialog_password

        sendmail_dir = (
            Path(sm.__file__).resolve().parent
            if hasattr(sm, "__file__")
            else Path.cwd()
        )
        old_cwd = os.getcwd()
        try:
            os.chdir(sendmail_dir)
            result = sm.process_profile(args)
            return str(result) if result is not None else "ERROR"
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

    def _on_send_dialog_send(self, dialog: _SendDialog) -> None:
        """Handle Send button click in Send Mailing dialog (T023: keep dialog open during send)."""
        dialog.send_button.setEnabled(False)
        dialog.spinner_label.show()
        self._send_in_progress = True
        log_entries: list[str] = []
        log_handler = _LogCapture(log_entries)
        logging.getLogger().addHandler(log_handler)
        try:
            result = self._send_with_sendmail(dialog)
        except Exception as exc:
            QMessageBox.critical(self, "Send Error", f"Failed to send:\n{exc}")
            log.error("Send failed: %s", exc)
            dialog.send_button.setEnabled(True)
            dialog.spinner_label.hide()
            return
        finally:
            self._send_in_progress = False
            logging.getLogger().removeHandler(log_handler)

        dialog.spinner_label.hide()

        if not self._send_result_is_success(result):
            log.warning(
                "sendMail returned non-success status after send attempt: %r", result
            )
            dialog.send_button.setEnabled(True)
        elif result.strip().upper() == "OK_TEST":
            # Show confirmation dialog for test email (US3)
            confirm_result = QMessageBox.question(
                dialog,
                "Test Email Sent",
                "Test email sent successfully.\n\nHave the test recipients confirmed\nthe mailing looks good?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm_result == QMessageBox.StandardButton.Yes:
                dialog._unlock_test_mode()
                # After confirmation, clear test checkbox and refresh data for bulk send
                dialog.test_check.blockSignals(True)
                dialog.test_check.setChecked(False)
                dialog.test_check.blockSignals(False)
                # Switch from test filter to regular filter and refresh data
                dialog.load_current_filter(dialog._current_profile)
                dialog.filter_and_display_records()
            dialog.send_button.setEnabled(True)
            return  # Don't close dialog after test

        log_dialog = _SessionLogDialog(self, log_entries=log_entries)
        log_dialog.exec()

        # Close dialog only after successful bulk send (not after test)
        if result.strip().upper() == "OK" and self._send_result_is_success(result):
            dialog.accept()

    def _menu_send(self) -> None:
        """Open the send dialog and send the current HTML file if confirmed."""
        if self._send_in_progress:
            return
        if not _SM_AVAILABLE:
            QMessageBox.warning(
                self,
                "sendMail Not Available",
                "Cannot import sendMail module — sending is disabled.",
            )
            return
        if not self._ask_save_if_dirty():
            return
        if not self._file_path or not os.path.exists(self._file_path):
            if not self._save():
                return

        config_path = self._resolve_send_config_path()
        config_data = self._load_send_config(config_path)
        # Use currently selected profile in main window (not hardcoded "default")
        initial_profile = getattr(self, "_current_profile", "default")
        dialog = _SendDialog(
            self,
            attachment_path=str(self._file_path),
            config_path=config_path,
            config_data=config_data,  # type: ignore
            initial_profile=initial_profile,
        )
        # Use show() instead of exec() so send can happen while dialog is visible (T023: test mode confirmation)
        dialog.send_button.clicked.connect(lambda: self._on_send_dialog_send(dialog))
        dialog.show()

    def _menu_edit_config(self) -> None:
        """Open the settings dialog to edit the sendMail YAML config file."""
        config_path = self._resolve_send_config_path()
        config_data = self._load_send_config(config_path)
        # Use currently selected profile in main window (not hardcoded "default")
        initial_profile = getattr(self, "_current_profile", "default")
        dialog = _ConfigDialog(
            self,
            config_path=config_path,
            config_data=config_data,
            initial_profile=initial_profile,
        )
        dialog.exec()

    def _menu_table_insert(self) -> None:
        """Open the table dimensions dialog and insert a table."""
        json_str = self._bridge.request_table_insert()
        if json_str:
            d = json.loads(json_str)
            self._run_js(f"tableOp('insertTable', {d['rows']}, {d['cols']})")

    def _menu_apply_css(self) -> None:
        """Open a CSS file picker and apply the stylesheet to the editor canvas."""
        initial = (
            str(Path(self._css_path).parent)
            if self._css_path
            else str(self._get_css_directory())
        )
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
            with open(css_path, encoding="utf-8") as f:
                css_text = f.read()
            self._run_js(f"applyCSS({json.dumps(css_text)})")
            self._css_status_label.setText(f"CSS: {Path(css_path).name}")
            log.info("Applied CSS: %s", css_path)
        except Exception as exc:
            log.error("CSS apply failed: %s", exc)
            QMessageBox.warning(self, "CSS Error", f"Could not read CSS file:\n{exc}")

    def _run_js(self, script: str) -> None:
        """Fire-and-forget JavaScript execution (wraps runJavaScript)."""
        page = self._view.page()
        if page:
            page.runJavaScript(script)

    # ------------------------------------------------------------------
    # Dirty / title management
    # ------------------------------------------------------------------

    def _on_dirty_changed(self, _dirty: bool) -> None:  # noqa: ARG002
        self._update_title()

    def _on_clipboard_analyzed(
        self, content_type: str, has_html_links: bool, detected_urls: list[str]
    ) -> None:
        """Handle clipboard analysis from paste event.

        For html_rich: Quill natively preserves links.
        For plain_text with URLs: Apply linkification to convert URLs to clickable links.
        """
        if content_type == "html_rich":
            log.debug(
                "Clipboard: HTML content with links=%s, urls=%s",
                has_html_links,
                len(detected_urls),
            )
        elif content_type == "plain_text" and detected_urls:
            log.debug(
                "Clipboard: Plain text with %d URLs detected: %s",
                len(detected_urls),
                detected_urls,
            )
            # Apply linkification to detected URLs in editor content
            self._apply_url_linkification(detected_urls)
        else:
            log.debug("Clipboard: Plain text without URLs")

    def _apply_url_linkification(self, urls: list[str]) -> None:
        """Apply link formatting to detected plain-text URLs in editor.

        Converts detected plain-text URLs to clickable hyperlinks.
        Skips URLs that are already formatted as links.
        """
        if not urls:
            return
        # Create JavaScript to find and linkify plain-text URLs
        url_json = json.dumps(urls)
        script = f"""
        (function() {{
          const urls = {url_json};
          const content = quill.getContents();
          let offset = 0;

          // Iterate through editor operations to find and format URLs
          content.ops.forEach(function(op) {{
            if (op.insert && typeof op.insert === 'string') {{
              const text = op.insert;
              const isLink = op.attributes && op.attributes.link;

              // Only linkify plain text (not already formatted)
              if (!isLink) {{
                urls.forEach(function(url) {{
                  let index = text.indexOf(url);
                  while (index >= 0) {{
                    quill.formatText(offset + index, url.length, 'link', url, 'silent');
                    index = text.indexOf(url, index + url.length);
                  }}
                }});
              }}
              offset += text.length;
            }} else if (op.insert) {{
              offset += 1; // For embeds (images, etc.)
            }}
          }});
        }})();
        """
        self._run_js(script)

    def _update_title(self) -> None:
        dirty_marker = " *" if self._bridge.is_dirty else ""
        template_marker = (
            " [Read-Only Template]" if getattr(self, "_is_template", False) else ""
        )
        if self._file_path:
            filename = Path(self._file_path).name
            self.setWindowTitle(
                f"sendMail Editor — {filename}{template_marker}{dirty_marker}"
            )
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

    def closeEvent(self, event: Any) -> None:  # noqa: N802, ARG002
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

    # Force light theme by setting explicit light palette
    from PyQt6.QtGui import QColor, QPalette

    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor(76, 163, 224))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(light_palette)

    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    window = EditorWindow(file_path=file_arg)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
