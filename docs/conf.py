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


def _make_pyqtSlot(*args, **kwargs):
    """Fake @pyqtSlot that behaves as a no-op decorator."""
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]

    def _decorator(fn):
        return fn

    return _decorator


def _make_pyqtSignal(*args, **kwargs):
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

    def menuBar(self):
        return MagicMock()

    def addToolBar(self, toolbar):
        pass

    def style(self):
        return MagicMock(standardIcon=MagicMock(return_value="icon"))

    def setStatusBar(self, bar):
        pass

    def statusBar(self):
        sb = MagicMock()
        sb.showMessage = MagicMock()
        return sb

    def setMinimumSize(self, w, h):
        pass

    def setWindowTitle(self, t):
        pass

    def centralWidget(self):
        return None

    def setCentralWidget(self, w):
        pass

    def show(self):
        pass

    def close(self):
        pass


MOCK_MODULES = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebChannel",
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
    "requests",
    "markdown2",
]

sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

sys.modules["PyQt6.QtCore"].pyqtSlot = _make_pyqtSlot
sys.modules["PyQt6.QtCore"].pyqtSignal = _make_pyqtSignal
sys.modules["PyQt6.QtCore"].QObject = _FakeQObject
sys.modules["PyQt6.QtCore"].QUrl = MagicMock()
sys.modules["PyQt6.QtCore"].QSize = MagicMock()
sys.modules["PyQt6.QtCore"].Qt = MagicMock()

sys.modules["PyQt6.QtWidgets"].QDialog = _FakeQDialog
sys.modules["PyQt6.QtWidgets"].QDialog.DialogCode = _FakeQDialog.DialogCode
sys.modules["PyQt6.QtWidgets"].QMainWindow = _FakeQMainWindow
sys.modules["PyQt6.QtWidgets"].QFileDialog = MagicMock()
sys.modules["PyQt6.QtWidgets"].QApplication = MagicMock()
sys.modules["PyQt6.QtWidgets"].QCheckBox = MagicMock()
sys.modules["PyQt6.QtWidgets"].QDialogButtonBox = MagicMock()
sys.modules["PyQt6.QtWidgets"].QInputDialog = MagicMock()
sys.modules["PyQt6.QtWidgets"].QFormLayout = MagicMock()
sys.modules["PyQt6.QtWidgets"].QComboBox = MagicMock()
sys.modules["PyQt6.QtWidgets"].QLabel = MagicMock()
sys.modules["PyQt6.QtWidgets"].QLineEdit = MagicMock()
sys.modules["PyQt6.QtWidgets"].QMessageBox = MagicMock()
sys.modules["PyQt6.QtWidgets"].QPlainTextEdit = MagicMock()
sys.modules["PyQt6.QtWidgets"].QPushButton = MagicMock()
sys.modules["PyQt6.QtWidgets"].QStyle = MagicMock()
sys.modules["PyQt6.QtWidgets"].QToolBar = MagicMock()
sys.modules["PyQt6.QtWidgets"].QSpinBox = MagicMock()
sys.modules["PyQt6.QtWidgets"].QStatusBar = MagicMock()
sys.modules["PyQt6.QtWidgets"].QTabWidget = MagicMock()
sys.modules["PyQt6.QtWidgets"].QTextBrowser = MagicMock()
sys.modules["PyQt6.QtWidgets"].QHBoxLayout = MagicMock()
sys.modules["PyQt6.QtWidgets"].QVBoxLayout = MagicMock()
sys.modules["PyQt6.QtWidgets"].QWidget = MagicMock()

sys.modules["PyQt6.QtGui"].QIcon = MagicMock()
sys.modules["PyQt6.QtGui"].QPixmap = MagicMock()

sys.modules["PyQt6.QtWebChannel"].QWebChannel = MagicMock()
sys.modules["PyQt6.QtWebEngineWidgets"].QWebEngineView = MagicMock()

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "sendMail"
copyright = "2025-2026, Xavier Mayeur"
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
    "sphinx.ext.coverage",
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
html_static_path = ["_static"]

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
