# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


# Mock modules that are not installed
class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):  # type: ignore[override]
        return MagicMock()


def _make_pyqtSlot(*args, **kwargs):  # noqa: N802, ARG001
    """Fake @pyqtSlot that behaves as a no-op decorator."""
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]

    def _decorator(fn):
        return fn

    return _decorator


def _make_pyqtSignal(*args, **kwargs):  # noqa: N802, ARG001
    """Fake pyqtSignal instance with connect/disconnect/emit."""
    sig = MagicMock()
    sig.connect = MagicMock()
    sig.disconnect = MagicMock()
    sig.emit = MagicMock()
    return sig


class _FakeQObject:
    """Stand-in for QObject."""

    def __init__(self, parent=None):
        self._q_parent = parent

    def parent(self):
        return self._q_parent


class _FakeQDialog(_FakeQObject):
    """Stand-in for QDialog."""

    class DialogCode:
        Accepted = 1
        Rejected = 0

    def exec(self):
        return self.DialogCode.Accepted

    def accept(self):
        pass

    def reject(self):
        pass


class _FakeQMainWindow(_FakeQObject):
    """Stand-in for QMainWindow."""

    def menuBar(self):  # noqa: N802
        return MagicMock()

    def addToolBar(self, toolbar):  # noqa: N802
        pass

    def style(self):
        return MagicMock(standardIcon=MagicMock(return_value="icon"))

    def setStatusBar(self, bar):  # noqa: N802
        pass

    def statusBar(self):  # noqa: N802
        sb = MagicMock()
        sb.showMessage = MagicMock()
        return sb

    def setMinimumSize(self, w, h):  # noqa: N802
        pass

    def setWindowTitle(self, t):  # noqa: N802
        pass

    def centralWidget(self):  # noqa: N802
        return None

    def setCentralWidget(self, w):  # noqa: N802
        pass

    def show(self):
        pass

    def close(self):
        pass


MOCK_MODULES = [
    # Qt binding: the project uses PySide6 (>=6.12); not installed on RTD
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
    "shiboken6",
    "python_calamine",
    "gspread",
    "yaml",
    "bs4",
    "certifi",
    "getSecrets",
    "google",
    "google.auth",
    "google.auth.transport",
    "google.auth.transport.requests",
    "google.oauth2",
    "google.oauth2.credentials",
    "google_auth_oauthlib",
    "google_auth_oauthlib.flow",
    "googleapiclient",
    "googleapiclient.discovery",
    "googleapiclient.errors",
    "googleapiclient.http",
    "oauth2client",
    "oauth2client.service_account",
    "PIL",
    "markdown2",
]

sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

sys.modules["PySide6.QtCore"].Signal = _make_pyqtSignal
sys.modules["PySide6.QtCore"].Slot = _make_pyqtSlot
sys.modules["PySide6.QtCore"].pyqtSlot = _make_pyqtSlot
sys.modules["PySide6.QtCore"].pyqtSignal = _make_pyqtSignal
sys.modules["PySide6.QtCore"].QObject = _FakeQObject
sys.modules["PySide6.QtCore"].QByteArray = MagicMock()
sys.modules["PySide6.QtCore"].QThread = MagicMock()
sys.modules["PySide6.QtCore"].QTimer = MagicMock()
sys.modules["PySide6.QtCore"].QUrl = MagicMock()
sys.modules["PySide6.QtCore"].QSize = MagicMock()
sys.modules["PySide6.QtCore"].Qt = MagicMock()

sys.modules["PySide6.QtWidgets"].QDialog = _FakeQDialog
sys.modules["PySide6.QtWidgets"].QDialog.DialogCode = _FakeQDialog.DialogCode
sys.modules["PySide6.QtWidgets"].QMainWindow = _FakeQMainWindow
sys.modules["PySide6.QtWidgets"].QFileDialog = MagicMock()
sys.modules["PySide6.QtWidgets"].QApplication = MagicMock()
sys.modules["PySide6.QtWidgets"].QApplication.setAttribute = MagicMock()
sys.modules["PySide6.QtWidgets"].QListWidget = MagicMock()
sys.modules["PySide6.QtWidgets"].QListWidgetItem = MagicMock()
sys.modules["PySide6.QtWidgets"].QTableWidget = MagicMock()
sys.modules["PySide6.QtWidgets"].QTableWidgetItem = MagicMock()
sys.modules["PySide6.QtWidgets"].QCheckBox = MagicMock()
sys.modules["PySide6.QtWidgets"].QDialogButtonBox = MagicMock()
sys.modules["PySide6.QtWidgets"].QInputDialog = MagicMock()
sys.modules["PySide6.QtWidgets"].QFormLayout = MagicMock()
sys.modules["PySide6.QtWidgets"].QComboBox = MagicMock()
sys.modules["PySide6.QtWidgets"].QLabel = MagicMock()
sys.modules["PySide6.QtWidgets"].QLineEdit = MagicMock()
sys.modules["PySide6.QtWidgets"].QMessageBox = MagicMock()
sys.modules["PySide6.QtWidgets"].QPlainTextEdit = MagicMock()
sys.modules["PySide6.QtWidgets"].QPushButton = MagicMock()
sys.modules["PySide6.QtWidgets"].QStyle = MagicMock()
sys.modules["PySide6.QtWidgets"].QStyle.StandardPixmap = MagicMock()
sys.modules["PySide6.QtWidgets"].QToolBar = MagicMock()
sys.modules["PySide6.QtWidgets"].QSpinBox = MagicMock()
sys.modules["PySide6.QtWidgets"].QStatusBar = MagicMock()
sys.modules["PySide6.QtWidgets"].QTabWidget = MagicMock()
sys.modules["PySide6.QtWidgets"].QTextBrowser = MagicMock()
sys.modules["PySide6.QtWidgets"].QHBoxLayout = MagicMock()
sys.modules["PySide6.QtWidgets"].QVBoxLayout = MagicMock()
sys.modules["PySide6.QtWidgets"].QWidget = MagicMock()

sys.modules["PySide6.QtGui"].QIcon = MagicMock()
sys.modules["PySide6.QtGui"].QPixmap = MagicMock()
sys.modules["PySide6.QtGui"].QCursor = MagicMock()

sys.modules["PySide6.QtWebChannel"].QWebChannel = MagicMock()
sys.modules["PySide6.QtWebEngineCore"].QWebEnginePage = MagicMock()
sys.modules["PySide6.QtWebEngineWidgets"].QWebEngineView = MagicMock()

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "sendMail"
copyright = "2025-2026, Xavier Mayeur"  # noqa: A001
author = "Xavier Mayeur"

version = "1.1"
release = "1.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = []  # no static assets yet; avoids a warning for a missing _static dir

# ReadTheDocs theme options
html_theme_options = {
    "logo_only": False,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "#2980B9",
    # Toc options
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

html_context = {
    "display_github": False,
}

html_show_sourcelink = True
