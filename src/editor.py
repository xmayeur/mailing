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
    _MEIPASS = Path(sys._MEIPASS)  # type: ignore[attr-defined]
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

ASSETS_DIR = _BASE / "Resources" / "editor_assets" if _IS_FROZEN else _BASE / "editor_assets"

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
from PyQt6.QtCore import QByteArray, QObject, QSize, QTimer, QUrl, pyqtSignal, pyqtSlot  # noqa: E402
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
    QMainWindow,
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
    '</svg>'
)

_SVG_SEND = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="2 2 14 14">'
    '<path d="M1.5 8l16-5-3.2 5 3.2 5-16-5z" fill="#1565C0"/>'
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
class _SessionLogDialog(QDialog):
    """Dialog displaying the session log from a send operation."""

    def __init__(self, parent: QWidget | None = None, log_entries: list[str] | None = None) -> None:
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
class _AnchorDialog(QDialog):
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
class _TableDialog(QDialog):
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
class _SendDialog(QDialog):
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
        self.setWindowTitle("Send Newsletter")
        self.setMinimumWidth(720)

        self._config_data: dict[str, dict[str, str | int]] = config_data or {}
        self._current_profile = ""
        self._attachment_path = attachment_path
        self._initial_config_data = config_data or {}
        self._session_filter: dict[str, str] | None = None
        self._original_filter_text = ""

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

        # Filter editor (T009, T010, T016-T021)
        self.filter_text_edit = QPlainTextEdit(self)
        self.filter_text_edit.setPlaceholderText("YAML filter (optional)\nExample: status: is active")
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

        # Validation setup (T016, T017)
        self._filter_validator = FilterValidator() if _VALIDATOR_AVAILABLE else None
        self._schema_cache: Any = None  # Initialized lazily in _get_schema_cache()
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self._run_filter_validation)
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
        self.test_check.toggled.connect(self._on_test_mode_toggled)
        self.verbose_check = QCheckBox("Verbose", flag_row)
        self.do_not_send_check = QCheckBox("Do not send", flag_row)
        self.selected_check = QCheckBox("Selected only", flag_row)
        for widget in (self.test_check, self.verbose_check, self.do_not_send_check, self.selected_check):
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("Send")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
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
        self._current_profile = profile
        profile_cfg = self._config_data.get(profile, {})

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

        self.subject_input.setText(Path(self._attachment_path).stem)
        self.message_input.setPlainText(str(profile_cfg.get("default_message", "")))
        self.body_input.setText("")
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

        self.load_current_filter(profile)
        self.filter_and_display_records()

    def load_current_filter(self, profile: str) -> None:
        """Load filter from profile config and display in filter field."""
        profile_cfg = self._config_data.get(profile, {})
        # Use filter_test if test mode enabled, otherwise use filter
        filter_key = "filter_test" if self.test_check.isChecked() else "filter"
        filter_obj = profile_cfg.get(filter_key)

        if not filter_obj:
            self.filter_text_edit.setPlainText("")
            self.filter_status_label.setText("")
            self._original_filter_text = ""
            self._session_filter = None
            return

        # Format filter dict as YAML string for display
        filter_str = ""
        if isinstance(filter_obj, dict):  # type: ignore[unreachable]
            for key, value in filter_obj.items():  # type: ignore[unreachable]
                filter_str += f"{key}: {value}\n"
            filter_str = filter_str.rstrip()
        else:
            filter_str = str(filter_obj)

        self.filter_text_edit.setPlainText(filter_str)
        self.filter_status_label.setText("")
        self._original_filter_text = filter_str
        self._session_filter = None

    def _on_test_mode_toggled(self, _checked: bool) -> None:
        """Update filter when test mode is toggled (T041)."""
        # Reload filter to show filter_test when in test mode, filter otherwise
        self.load_current_filter(self._current_profile)
        # Clear session filter since we're switching filter mode
        self._session_filter = None

    def _on_filter_text_changed(self) -> None:
        """Handle filter text change with debounced validation (T016, T017)."""
        self._validation_timer.stop()
        self._validation_timer.start(200)

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
        if not db_path and profile_cfg.get("SHEETID"):
            # Google Sheets profile - try to load schema from Google Sheets
            sa = profile_cfg.get("SA")
            sheet_id = profile_cfg.get("SHEETID")
            if sa and sheet_id:
                def _load_gsheet_schema() -> list[str]:
                    try:
                        import sendMail as sm  # noqa: N813

                        if hasattr(sm, "get_google_sheets_schema"):
                            result = sm.get_google_sheets_schema(str(sa), str(sheet_id))
                            if isinstance(result, list):
                                return result
                    except Exception as e:
                        log.debug("Could not load Google Sheets schema: %s", e)
                    return []

                return cast(list[str], cache.get(f"{profile_name}_gsheet", _load_gsheet_schema))
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

        return cast(list[str], cache.get(f"{profile_name}_csv_{db_path}", _load_csv_schema))

    def _update_validation_ui(self, status: dict[str, Any]) -> None:
        """Update filter field UI based on validation status (T019, T020, T021)."""
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

        # T020: Error message display
        error_msg = ""
        if syntax_errors:
            error_msg += "Syntax: " + "; ".join(syntax_errors)
        if missing_fields:
            if error_msg:
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
        """Load database records from CSV or Google Sheets (T026)."""
        db_path = self.database_input.text().strip()

        # Check if current profile uses Google Sheets (has SHEETID, no CSV database)
        profile_cfg = self._config_data.get(self._current_profile, {})
        if not db_path and profile_cfg.get("SHEETID"):
            # Google Sheets profile - try to load records from Google Sheets
            sa = profile_cfg.get("SA")
            sheet_id = profile_cfg.get("SHEETID")
            if sa and sheet_id:
                try:
                    import sendMail as sm  # noqa: N813

                    if hasattr(sm, "open_google_db_members_sheet") and hasattr(sm, "read_all_sheet"):
                        wb = sm.open_google_db_members_sheet(str(sa), str(sheet_id))
                        data = sm.read_all_sheet(wb)
                        if data and len(data) > 0:
                            headers = [h.strip() for h in data[0] if h.strip()]
                            rows = data[1:]  # Skip header row
                            log.debug(f"Loaded {len(rows)} records from Google Sheet {sheet_id}")
                            return rows, headers
                except Exception as e:
                    log.debug("Could not load Google Sheets records: %s", e)
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
                            log.debug(f"Loaded {len(rows)} records from {db_path} (encoding: {encoding})")
                            return rows, headers
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                # If all encodings fail, raise error
                raise ValueError(f"Could not decode {db_path} with any supported encoding")
        except Exception as e:
            log.debug("Could not load database: %s", e)

        return [], []

    def filter_and_display_records(self) -> None:
        """Load, filter, and display database records (T027, T028, T040, T041, T042)."""
        # T041: Handle profile switching by tracking current profile
        if not hasattr(self, "_last_profile"):
            self._last_profile = self._current_profile

        filter_text = self.filter_text_edit.toPlainText()
        rows, headers = self.load_database_records()

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
            if filter_text and filter_text.strip():
                import yaml

                filter_dict = yaml.safe_load(filter_text) or {}
                filtered_rows = matcher.filter_rows(rows, filter_dict, headers)
                log.debug(f"Filter applied: {filter_dict}, matched {len(filtered_rows)}/{len(rows)} records")
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

    def _update_record_display(self, rows: list[list[str]], headers: list[str], total: int) -> None:
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

    def _apply_filter(self) -> None:
        """Apply edited filter as session-active filter (T034)."""
        filter_text = self.filter_text_edit.toPlainText().strip()

        if not filter_text:
            self._session_filter = None
            self.filter_status_label.setText("(Filter cleared - will use profile default)")
            self.filter_status_label.setStyleSheet("color: #666; font-size: 11px;")
            self.filter_and_display_records()
            return

        if not self._filter_validator:
            self.filter_status_label.setText("Filter validator not available")
            self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")
            return

        schema = self._get_database_schema()
        status = self._filter_validator.get_validation_status(filter_text, schema)

        if not status.get("is_valid"):
            errors = status.get("syntax_errors", []) + status.get("missing_fields", [])
            self.filter_status_label.setText(f"Cannot apply: {', '.join(errors)}")
            self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")
            return

        import yaml

        try:
            filter_dict = yaml.safe_load(filter_text) or {}
            if isinstance(filter_dict, dict):
                self._session_filter = filter_dict
                self.filter_status_label.setText("✓ Session filter applied")
                self.filter_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
                self.filter_and_display_records()
            else:
                self.filter_status_label.setText("Filter must be YAML mapping (key: value)")
                self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")
        except Exception as e:
            self.filter_status_label.setText(f"Parse error: {e}")
            self.filter_status_label.setStyleSheet("color: #f44336; font-size: 11px;")

    def _reset_filter(self) -> None:
        """Reset filter to original from profile config (T035)."""
        self._session_filter = None
        if self._original_filter_text:
            self.filter_text_edit.setPlainText(self._original_filter_text)
        else:
            self.filter_text_edit.setPlainText("")
        self.filter_status_label.setText("(Filter reset to profile default)")
        self.filter_status_label.setStyleSheet("color: #666; font-size: 11px;")

    def build_args(self, config_data: dict[str, dict[str, str | int]]) -> SimpleNamespace:
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
        namespace.session_filter = self._session_filter  # T036: Pass session-active filter if set
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


# ---------------------------------------------------------------------------
# Settings / config editor
# ---------------------------------------------------------------------------
class _ConfigDialog(QDialog):
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
            "<pre>filter:\n  email: is not empty\n  country: one of \"BE\", \"FR\"</pre>"
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
            config_data: dict[str, dict[str, str | int | list[str] | dict[str, str]]] | None = None,
            initial_profile: str = "default",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(1080)
        self.setMinimumHeight(780)

        self._config_data: ConfigProfile = self._normalize_config_data(config_data or {})
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

    def _normalize_config_data(
        self, data: ConfigProfile
    ) -> ConfigProfile:
        normalized: ConfigProfile = {}
        for name, profile in data.items():
            if isinstance(profile, dict):
                normalized[str(name)] = dict(profile)
        return normalized

    def _default_profile_data(self) -> dict[str, str | int | list[str] | dict[str, str]]:
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

    def _read_config_file(self, path: str) -> dict[str, dict[str, str | int | list[str] | dict[str, str]]]:
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return self._normalize_config_data(data if isinstance(data, dict) else {})
        except Exception as exc:
            QMessageBox.warning(self, _CONFIG_ERROR, f"Could not load config:\n{exc}")
            return {}

    def _browse_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select sendMail config",
            str(Path(self.config_input.text()).parent) if self.config_input.text() else str(Path.home()),
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
            start_dir = str(Path(edit.text()).parent) if edit.text() else str(Path.home())
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
        self._add_line_field(layout,
                             _LineFieldSpec("MAILCONFIG", "MAILCONFIG", tooltip="Secret name used by getSecrets()."))
        self._add_line_field(layout,
                             _LineFieldSpec("sender", "Sender", tooltip="Email address used in the From header."))
        self._add_line_field(layout,
                             _LineFieldSpec("sendername", "Sender name", tooltip="Display name for the sender."))
        self._add_line_field(layout, _LineFieldSpec("username", "Username", tooltip="SMTP or IMAP login user."))
        self._add_line_field(layout,
                             _LineFieldSpec("password", "Password", tooltip="SMTP or IMAP password.", password=True))
        self._add_line_field(layout,
                             _LineFieldSpec("domain", "Domain", tooltip="Message-ID domain for generated emails."))

    def _build_delivery_tab(self) -> None:
        _, layout = self._build_tab("Delivery")
        self._add_line_field(layout, _LineFieldSpec("smtp_host", "SMTP host", tooltip="SMTP server hostname."))
        self._add_spin_field(layout, "smtp_port", "SMTP port", tooltip="SMTP server port.", minimum=0, maximum=65535)
        self._add_line_field(layout, _LineFieldSpec("imap_host", "IMAP host", tooltip="IMAP server hostname."))
        self._add_spin_field(layout, "imap_port", "IMAP port", tooltip="IMAP server port.", minimum=0, maximum=65535)
        self._add_line_field(layout, _LineFieldSpec("sent_folder", "Sent folder",
                                                    tooltip="Remote IMAP folder used to archive sent mail."))

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
        self._add_line_field(layout, _LineFieldSpec("sa", "Service account (SA)",
                                                    tooltip="Secret key name for Google service account JSON."))
        self._add_line_field(layout, _LineFieldSpec("sheetid", "Sheet ID",
                                                    tooltip="Secret key name for the Google Sheet identifier."))
        self._add_line_field(layout, _LineFieldSpec("mail", "Email",
                                                    tooltip="Gmail account email address for sending via Gmail API."))
        self._add_line_field(layout, _LineFieldSpec("folder", "Gmail Folder",
                                                    tooltip="Gmail folder name for storing messages to send."))
        self._add_line_field(layout, _LineFieldSpec("members", "Members Endpoint",
                                                    tooltip="URL endpoint for retrieving member data."))
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
        self._add_line_field(layout, _LineFieldSpec("token_id", "Token ID",
                                                    tooltip="Secret key name for Gmail OAuth token."))
        self._add_line_field(layout, _LineFieldSpec("credentials_id", "Credentials ID",
                                                    tooltip="Secret key name for Gmail OAuth client config."))
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
        self._add_line_field(layout, _LineFieldSpec("subject", "Subject", tooltip="Optional default subject."))
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
        self._add_line_field(layout,
                             _LineFieldSpec("body", "Body", tooltip="Optional body replacement text for ${body}."))
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
        self._add_spin_field(layout, "pause", "Pause (sec)", tooltip="Pause between batches, in seconds.", minimum=0,
                             maximum=3600)
        self._add_spin_field(layout, "from_index", "From index", tooltip="Starting subscriber row.", minimum=0)
        self._add_spin_field(layout, "to_index", "To index", tooltip="Stopping subscriber row.", minimum=0)
        self._add_spin_field(layout, "wait", "Wait (min)", tooltip="Wait before restarting, in minutes.", minimum=0)
        self._add_spin_field(layout, "max_mails_per_hour", "Max mails/hour", tooltip="Hourly sending limit.", minimum=1)
        self._add_spin_field(layout, "max_addr_per_mail", "Max addr/mail",
                             tooltip="Maximum recipient addresses per email.", minimum=1)

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
        self._add_check_field(layout, "verbose", "Verbose", tooltip="Increase logging verbosity.")
        self._add_check_field(layout, "doNotSend", "Do not send", tooltip="Suppress actual sending.")
        self._add_check_field(layout, "selected", "Selected only", tooltip="Send only selected rows.")
        self._add_check_field(layout, "md2html", "md2html", tooltip="Keep the Markdown-to-HTML compatibility flag.")
        self._add_check_field(layout, "keep-html", "keep-html", tooltip="Preserve generated HTML output.")

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
        if isinstance(value, dict):
            return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).strip()
        try:
            return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).strip()
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

    def _load_widget_spin_box(self, widget: QSpinBox, value: object, default: int) -> None:
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

    def _load_widget_plain_text(self, widget: QPlainTextEdit, value: object, key: str) -> None:
        if key in self._yaml_keys:
            widget.setPlainText(self._dump_yaml_block(value))
        elif key in self._list_keys:
            self._load_widget_plain_text_list(widget, value)
        else:
            widget.setPlainText("" if value is None else str(value))

    def _load_widget_plain_text_list(self, widget: QPlainTextEdit, value: object) -> None:
        if isinstance(value, list):
            widget.setPlainText("\n".join(str(item) for item in value if str(item).strip()))
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
        self, widget: QWidget, key: str, value: object, cfg: ConfigData, defaults: ConfigData
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
            value = self._get_config_value_for_widget(key, widget, cfg, defaults)  # type: ignore[arg-type]
            self._load_widget_by_type(widget, key, value, cfg, defaults)  # type: ignore[arg-type]

        current_index = self.tabs.currentIndex()
        if current_index >= 0:
            self._update_help(current_index)

    def _collect_profile_data(self) -> dict[str, object]:
        original_profile = self._config_data.get(self._current_profile, {})
        original_case_map = {str(k).lower(): k for k in original_profile.keys()} if isinstance(original_profile,
                                                                                               dict) else {}

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
        self._config_data[self._current_profile] = self._collect_profile_data()  # type: ignore[assignment]

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
            QMessageBox.warning(self, "Profile Exists", f"Profile '{name}' already exists.")
            return
        self._config_data[name] = self._default_profile_data()
        self._reload_profiles(name)

    def _duplicate_profile(self) -> None:
        if not self._current_profile:
            return
        name = self._new_profile_name("Duplicate Profile", f"{self._current_profile}-copy")
        if not name:
            return
        self._persist_current_profile()
        if name in self._config_data:
            QMessageBox.warning(self, "Profile Exists", f"Profile '{name}' already exists.")
            return
        self._config_data[name] = self._collect_profile_data()  # type: ignore[assignment]
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
            QMessageBox.critical(self, "Save Error", f"Could not save configuration:\n{exc}")
            return
        self.accept()


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

    @pyqtSlot(result=str)  # type: ignore[arg-type]
    def request_image_insert(self) -> str:
        """
        Opens a file dialog and returns a base64 data URI for the chosen image.
        Returns "" if the user cancels.
        """
        parent_obj = self.parent()
        try:
            parent_widget: QWidget | None = parent_obj if isinstance(parent_obj, QWidget) else None
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

    @pyqtSlot(str, result=str)  # type: ignore[arg-type]
    def request_link_insert(self, selected_text: str) -> str:
        """
        Opens a link dialog pre-filled with *selected_text*.
        Returns a JSON string {"url": "...", "text": "..."} on confirm,
        or "" on cancel.
        """
        parent_obj = self.parent()
        try:
            parent_widget: QWidget | None = parent_obj if isinstance(parent_obj, QWidget) else None
        except TypeError:
            parent_widget = None
        dialog = _LinkDialog(parent_widget, selected_text=selected_text)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return ""
        url = dialog.get_url()
        if not url:
            return ""
        return json.dumps({"url": url, "text": dialog.get_text()})

    @pyqtSlot(result=str)  # type: ignore[arg-type]
    def request_table_insert(self) -> str:
        """
        Opens a dialog asking for table dimensions.
        Returns JSON string {"rows": n, "cols": m} on confirm, or "" on cancel.
        """
        parent_obj = self.parent()
        try:
            parent_widget: QWidget | None = parent_obj if isinstance(parent_obj, QWidget) else None
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
    """Main WYSIWYG newsletter editor window.

    Desktop application for composing and editing HTML newsletters.
    Uses Quill.js for rich text editing in QWebEngineView.
    Supports inline images, attachments, CSS customization, and sendMail output.

    Args:
        file_path: Optional markdown or HTML file to open on startup
    """

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
        page = self._view.page()
        if page:
            page.setWebChannel(self._channel)

        # Connect signals
        self._bridge.dirty_changed.connect(self._on_dirty_changed)
        self._bridge.css_changed.connect(self._on_css_changed)

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
                self, "Unsupported File", f"Unsupported file type: {ext}\nOpen .md or .html files."
            )
            return

        self._file_path = path
        self._bridge.reset(body_html)
        self._update_title()

        # Load default profile stylesheet if available
        self._load_default_stylesheet()

        self._load_editor_page(body_html)

    def _md_to_body_html(self, md_path: str) -> str:
        """Convert a .md file to an HTML body string."""
        if _SM_AVAILABLE:
            return self._md_to_body_html_sendmail(md_path)
        if _MD2_AVAILABLE:
            return self._md_to_body_html_markdown2(md_path)
        QMessageBox.warning(
            self, "Markdown Not Available",
            "Cannot import markdown — MD conversion disabled. Install 'markdown2' package."
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
                img_path = os.path.join(base_dir, src) if not os.path.isabs(src) else src
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
        _empty_p = r'<p(?:[^>]*)?>(?:\s*<br\s*/?>)?\s*</p>'
        return re.sub(
            rf'({_empty_p})\s*(?:{_empty_p}\s*){{2,}}',
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
                **{"class": "editor-anchor", "data-anchor-id": anchor_id,  # type: ignore[arg-type]
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
                c for c in cell.children
                if getattr(c, "name", None) in block_tags
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
        block_tags = ("p", "h1", "h2", "h3", "h4", "h5", "h6",
                      "div", "blockquote", "pre")

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
        self._file_path = str(Path(path).with_suffix(_HTML_EXT))
        return self._save()

    def _write_html_file(self, path: str, body_html: str) -> None:
        """Write a complete HTML document file from body HTML."""
        # Use user-selected CSS if set; otherwise fall back to project default
        css_path = (_BASE / "Resources" / "css" / "styles.css") if _IS_FROZEN else (_BASE / "css" / "styles.css")
        css_source = Path(self._css_path) if self._css_path else css_path
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
        bold_action.triggered.connect(lambda: self._run_js("quill.format('bold', !quill.getFormat().bold)"))

        italic_action = fmt_menu.addAction("&Italic")
        italic_action.setShortcut("Ctrl+I")
        italic_action.triggered.connect(lambda: self._run_js("quill.format('italic', !quill.getFormat().italic)"))

        underline_action = fmt_menu.addAction("&Underline")
        underline_action.setShortcut("Ctrl+U")
        underline_fmt = "quill.format('underline', !quill.getFormat().underline)"
        underline_action.triggered.connect(lambda: self._run_js(underline_fmt))

        strike_action = fmt_menu.addAction("&Strikethrough")
        strike_action.setShortcut("Ctrl+Shift+X")
        strike_action.triggered.connect(lambda: self._run_js("quill.format('strike', !quill.getFormat().strike)"))

        fmt_menu.addSeparator()

        for level in (1, 2, 3):
            h_action = fmt_menu.addAction(f"Heading &{level}")
            h_action.triggered.connect(
                lambda _checked=False, lvl=level: self._run_js(f"quill.format('header', {lvl})")  # noqa: ARG005
            )

        normal_action = fmt_menu.addAction("&Normal Paragraph")
        normal_action.triggered.connect(lambda: self._run_js("quill.format('header', false)"))

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
                lambda _checked=False, family=font_name: self._set_font_family(family)  # noqa: ARG005
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

    def _build_table_menu(self, menubar: Any) -> None:
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
        quote_action.triggered.connect(lambda: self._run_js("quill.format('blockquote', true)"))

        code_action = ins_menu.addAction("&Code Block")
        code_action.triggered.connect(lambda: self._run_js("quill.format('code-block', true)"))

    def _build_toolbars(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

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
                if cfg != -1:
                    return str(cfg)
            except Exception as exc:
                log.debug("Could not resolve sendMail config path: %s", exc)
        return str(Path.home() / ".config" / "sendMail.yml")

    def _load_send_config(self, config_path: str) -> dict[str, dict[str, str | int | list[str] | dict[str, str]]]:
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
        """Load the default profile's stylesheet if available."""
        try:
            config_path = self._resolve_send_config_path()
            config_data = self._load_send_config(config_path)
            styles_path = config_data.get("default", {}).get("styles")
            if styles_path and isinstance(styles_path, str):
                abs_path = os.path.abspath(styles_path)
                if os.path.exists(abs_path):
                    self._bridge.css_changed.emit(abs_path)
        except Exception as exc:
            log.debug("Could not load default stylesheet: %s", exc)

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
            config_data=config_data,  # type: ignore[arg-type]
            initial_profile="default",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._send_in_progress = True
        log_entries: list[str] = []
        log_handler = _LogCapture(log_entries)
        logging.getLogger().addHandler(log_handler)
        try:
            result = self._send_with_sendmail(dialog)
        except Exception as exc:
            QMessageBox.critical(self, "Send Error", f"Failed to send:\n{exc}")
            log.error("Send failed: %s", exc)
            return
        finally:
            self._send_in_progress = False
            logging.getLogger().removeHandler(log_handler)

        if not self._send_result_is_success(result):
            log.warning("sendMail returned non-success status after send attempt: %r", result)

        log_dialog = _SessionLogDialog(self, log_entries=log_entries)
        log_dialog.exec()

    def _menu_edit_config(self) -> None:
        """Open the settings dialog to edit the sendMail YAML config file."""
        config_path = self._resolve_send_config_path()
        config_data = self._load_send_config(config_path)
        dialog = _ConfigDialog(
            self,
            config_path=config_path,
            config_data=config_data,
            initial_profile="default",
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
        css_dir = (_BASE / "Resources" / "css") if _IS_FROZEN else (_BASE / "css")
        initial = str(Path(self._css_path).parent) if self._css_path else str(css_dir)
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
