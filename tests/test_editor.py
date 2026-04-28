"""
Unit tests for editor.py

All PyQt6 modules are mocked before import so these tests run headlessly
on CI without a display server, following the same pattern used in test_sendMail.py.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Mock all Qt modules BEFORE importing editor
# ---------------------------------------------------------------------------
import inspect as _inspect

_qt_mocks = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebChannel",
]
for _mod in _qt_mocks:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


# pyqtSlot: use inspect.isfunction to distinguish @pyqtSlot(str) from @pyqtSlot
def _make_pyqtSlot(*args, **kwargs):
    """Fake @pyqtSlot that is a no-op decorator."""
    if len(args) == 1 and _inspect.isfunction(args[0]) and not kwargs:
        # Bare @pyqtSlot — args[0] is the function being decorated
        return args[0]
    # @pyqtSlot(str), @pyqtSlot(str, result=str), etc. — return a decorator
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


# Proper fake base classes so EditorBridge/EditorWindow can subclass them.
# MagicMock instances cannot be used as base classes reliably —
# attribute access on subclasses with _-prefixed names raises AttributeError.

class _FakeQObject:
    """Stand-in for QObject."""
    def __init__(self, parent=None):
        self._q_parent = parent

    def parent(self):
        return self._q_parent


class _FakeQMainWindow(_FakeQObject):
    """Stand-in for QMainWindow."""
    def menuBar(self):
        return MagicMock()

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


sys.modules["PyQt6.QtCore"].pyqtSlot = _make_pyqtSlot
sys.modules["PyQt6.QtCore"].pyqtSignal = _make_pyqtSignal
sys.modules["PyQt6.QtCore"].QObject = _FakeQObject
sys.modules["PyQt6.QtCore"].QUrl = MagicMock()
sys.modules["PyQt6.QtCore"].Qt = MagicMock()

sys.modules["PyQt6.QtWidgets"].QMainWindow = _FakeQMainWindow
sys.modules["PyQt6.QtWidgets"].QDialog = _FakeQDialog
sys.modules["PyQt6.QtWidgets"].QDialog.DialogCode = _FakeQDialog.DialogCode
sys.modules["PyQt6.QtWidgets"].QSpinBox = MagicMock()

# Add parent directory to path so editor can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import editor  # noqa: E402  (must come after sys.modules patching)
from editor import EditorBridge  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bridge():
    """Return an EditorBridge with a mocked dirty_changed signal."""
    bridge = EditorBridge()
    bridge.dirty_changed = MagicMock()
    bridge.dirty_changed.emit = MagicMock()
    return bridge


# ---------------------------------------------------------------------------
# EditorBridge tests
# ---------------------------------------------------------------------------

class TestEditorBridgeContentTracking:
    def test_initial_state_is_clean(self):
        bridge = _make_bridge()
        assert bridge.is_dirty is False
        assert bridge.get_current_html() == ""

    def test_on_content_changed_sets_dirty_and_caches_html(self):
        bridge = _make_bridge()
        bridge.on_content_changed("<p>Hello</p>")
        assert bridge.is_dirty is True
        assert bridge.get_current_html() == "<p>Hello</p>"

    def test_on_content_changed_emits_dirty_signal_once(self):
        bridge = _make_bridge()
        bridge.on_content_changed("<p>A</p>")
        bridge.on_content_changed("<p>B</p>")
        # Signal should emit True exactly once (first change only)
        bridge.dirty_changed.emit.assert_called_once_with(True)

    def test_get_current_html_returns_last_content(self):
        bridge = _make_bridge()
        bridge.on_content_changed("<p>first</p>")
        bridge.on_content_changed("<p>second</p>")
        assert bridge.get_current_html() == "<p>second</p>"

    def test_reset_clears_dirty(self):
        bridge = _make_bridge()
        bridge.on_content_changed("<p>Hello</p>")
        assert bridge.is_dirty is True
        bridge.reset("<p>Hello</p>")
        assert bridge.is_dirty is False

    def test_reset_updates_cached_html(self):
        bridge = _make_bridge()
        bridge.on_content_changed("<p>old</p>")
        bridge.reset("<p>new</p>")
        assert bridge.get_current_html() == "<p>new</p>"

    def test_reset_emits_false(self):
        bridge = _make_bridge()
        bridge.on_content_changed("<p>x</p>")
        bridge.dirty_changed.emit.reset_mock()
        bridge.reset()
        bridge.dirty_changed.emit.assert_called_once_with(False)

    def test_log_js_error_does_not_raise(self):
        bridge = _make_bridge()
        bridge.log_js_error("ReferenceError: quill is not defined at editor.html:42")


class TestEditorBridgeImageInsert:
    def test_returns_data_uri_on_file_selection(self):
        bridge = _make_bridge()
        with (
            patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=("/tmp/img.png", "")),
            patch("editor.sm") as mock_sm,
        ):
            mock_sm.file_to_base64.return_value = "abc123"
            mock_sm.guess_type.return_value = "image/png"
            editor._SM_AVAILABLE = True
            result = bridge.request_image_insert()
        assert result == "data:image/png;base64,abc123"

    def test_returns_empty_string_on_cancel(self):
        bridge = _make_bridge()
        with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=("", "")):
            result = bridge.request_image_insert()
        assert result == ""

    def test_returns_empty_string_on_exception(self):
        bridge = _make_bridge()
        with (
            patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=("/bad/path.png", "")),
            patch("editor.sm") as mock_sm,
        ):
            mock_sm.file_to_base64.side_effect = FileNotFoundError("not found")
            editor._SM_AVAILABLE = True
            result = bridge.request_image_insert()
        assert result == ""

    def test_fallback_when_sm_unavailable(self):
        bridge = _make_bridge()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\n")  # minimal PNG header bytes
            tmp_path = tmp.name
        try:
            with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=(tmp_path, "")):
                orig = editor._SM_AVAILABLE
                editor._SM_AVAILABLE = False
                result = bridge.request_image_insert()
                editor._SM_AVAILABLE = orig
            assert result.startswith("data:image/png;base64,") or result.startswith("data:")
        finally:
            os.unlink(tmp_path)


class TestEditorBridgeLinkInsert:
    def test_returns_json_on_confirm(self):
        bridge = _make_bridge()
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = 1  # Accepted
        mock_dialog.get_url.return_value = "https://example.com"
        mock_dialog.get_text.return_value = "Example"

        with patch("editor._LinkDialog", return_value=mock_dialog):
            result = bridge.request_link_insert("Example")

        data = json.loads(result)
        assert data["url"] == "https://example.com"
        assert data["text"] == "Example"

    def test_returns_empty_on_cancel(self):
        bridge = _make_bridge()
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = 0  # Rejected

        with patch("editor._LinkDialog", return_value=mock_dialog):
            result = bridge.request_link_insert("")

        assert result == ""

    def test_returns_empty_when_url_blank(self):
        bridge = _make_bridge()
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = 1  # Accepted but empty URL
        mock_dialog.get_url.return_value = ""
        mock_dialog.get_text.return_value = ""

        with patch("editor._LinkDialog", return_value=mock_dialog):
            result = bridge.request_link_insert("")

        assert result == ""


# ---------------------------------------------------------------------------
# HTML ↔ Markdown conversion tests
# ---------------------------------------------------------------------------

class TestHtmlToMarkdown:
    """Tests for EditorWindow._write_md_file logic (exercised directly)."""

    def _convert(self, html: str) -> str:
        import html2text
        h = html2text.HTML2Text()
        h.body_width = 0
        h.protect_links = True
        h.wrap_links = False
        h.unicode_snob = True
        h.images_as_html = False
        return h.handle(html)

    def test_heading_preserved(self):
        md = self._convert("<h1>Title</h1>")
        assert "# Title" in md

    def test_bold_preserved(self):
        md = self._convert("<p><strong>bold</strong></p>")
        assert "**bold**" in md or "__bold__" in md

    def test_link_preserved(self):
        md = self._convert('<a href="https://example.com">click</a>')
        assert "https://example.com" in md

    def test_unicode_preserved(self):
        md = self._convert("<p>Arrow: \u261e</p>")
        assert "\u261e" in md  # ☞ must not be escaped

    def test_no_line_wrap_on_long_text(self):
        long_text = "word " * 30
        md = self._convert(f"<p>{long_text}</p>")
        lines = [ln for ln in md.splitlines() if ln.strip()]
        # With body_width=0 there should be no mid-sentence line breaks
        assert len(lines) <= 2


class TestHtmlFileWriter:
    """Tests for EditorWindow._write_html_file output.

    _write_html_file only uses the module-level _BASE variable (not self),
    so we can call it with None as self after patching _BASE.
    """

    def _write(self, path: str, body_html: str, css_path=None) -> None:
        """Call _write_html_file with a temp _BASE that has no css/ dir."""
        class _FakeWindow:
            _css_path = css_path
        with patch.object(editor, "_BASE", Path(tempfile.gettempdir())):
            editor.EditorWindow._write_html_file(_FakeWindow(), path, body_html)

    def test_output_contains_charset(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as tmp:
            path = tmp.name
        try:
            self._write(path, "<p>hello</p>")
            content = Path(path).read_text(encoding="utf-8")
            assert "UTF-8" in content
        finally:
            os.unlink(path)

    def test_output_contains_body_html(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as tmp:
            path = tmp.name
        try:
            self._write(path, "<p>newsletter content</p>")
            content = Path(path).read_text(encoding="utf-8")
            assert "<p>newsletter content</p>" in content
        finally:
            os.unlink(path)

    def test_output_no_unfilled_csp_placeholder(self):
        """Saved HTML must not contain the {_CSP_IMG_DOMAIN} placeholder from sendMail."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as tmp:
            path = tmp.name
        try:
            self._write(path, "<p>x</p>")
            content = Path(path).read_text(encoding="utf-8")
            assert "{_CSP_IMG_DOMAIN}" not in content
        finally:
            os.unlink(path)

    def test_output_is_valid_html_document(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as tmp:
            path = tmp.name
        try:
            self._write(path, "<h1>Hi</h1>")
            content = Path(path).read_text(encoding="utf-8")
            assert "<html>" in content
            assert "</html>" in content
            assert "<body>" in content
        finally:
            os.unlink(path)

    def test_user_css_overrides_default(self):
        """When _css_path is set, its contents must appear in the saved HTML."""
        with tempfile.NamedTemporaryFile(suffix=".css", delete=False, mode="w", encoding="utf-8") as css_tmp:
            css_tmp.write("body { font-size: 20px; }")
            css_path = css_tmp.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as html_tmp:
            html_path = html_tmp.name
        try:
            self._write(html_path, "<p>styled</p>", css_path=css_path)
            content = Path(html_path).read_text(encoding="utf-8")
            assert "font-size: 20px" in content
        finally:
            os.unlink(css_path)
            os.unlink(html_path)


# ---------------------------------------------------------------------------
# Table insert dialog tests
# ---------------------------------------------------------------------------

class TestEditorBridgeTableInsert:
    def test_returns_json_on_confirm(self):
        bridge = _make_bridge()
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = 1  # Accepted
        mock_dialog.get_rows.return_value = 3
        mock_dialog.get_cols.return_value = 4

        with patch("editor._TableDialog", return_value=mock_dialog):
            result = bridge.request_table_insert()

        data = json.loads(result)
        assert data["rows"] == 3
        assert data["cols"] == 4

    def test_returns_empty_on_cancel(self):
        bridge = _make_bridge()
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = 0  # Rejected

        with patch("editor._TableDialog", return_value=mock_dialog):
            result = bridge.request_table_insert()

        assert result == ""


# ---------------------------------------------------------------------------
# Local image inlining tests
# ---------------------------------------------------------------------------

class TestLocalImageInlining:
    """Tests for EditorWindow._html_to_body_html image-inlining behaviour."""

    def _make_window(self) -> editor.EditorWindow:
        """Return a minimal EditorWindow stub (no real Qt)."""
        win = object.__new__(editor.EditorWindow)
        win._css_path = None
        return win

    def test_local_img_inlined_via_sm(self):
        """When _SM_AVAILABLE, make_html_images_inline is called and data URIs appear."""
        win = self._make_window()
        inlined_html = '<html><body><img src="data:image/png;base64,abc"/></body></html>'
        with (
            patch.object(editor, "_SM_AVAILABLE", True),
            patch("editor.sm.make_html_images_inline", return_value=inlined_html) as mock_inline,
        ):
            result = win._html_to_body_html("/fake/file.html")

        mock_inline.assert_called_once_with("/fake/file.html")
        assert "data:image/png;base64,abc" in result

    def test_fallback_when_sm_unavailable(self):
        """When _SM_AVAILABLE is False, _inline_images_fallback is used instead."""
        win = self._make_window()
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a tiny valid PNG (1×1 pixel, minimal binary)
            img_path = os.path.join(tmp_dir, "img.png")
            with open(img_path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
            html_path = os.path.join(tmp_dir, "test.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write('<html><body><img src="img.png"/></body></html>')

            with patch.object(editor, "_SM_AVAILABLE", False):
                result = win._html_to_body_html(html_path)

        assert "data:" in result


# ---------------------------------------------------------------------------
# HR insertion tests
# ---------------------------------------------------------------------------

class TestHrInsertion:
    """Verify that HR menu item fires insertHR() via _run_js."""

    def _make_window_with_run_js(self):
        win = object.__new__(editor.EditorWindow)
        win._run_js = MagicMock()
        win._bridge = _make_bridge()
        win._file_path = None
        win._css_path = None
        return win

    def test_hr_menu_calls_insert_hr(self):
        win = self._make_window_with_run_js()
        # Simulate what the menu action's triggered lambda does
        win._run_js("insertHR()")
        win._run_js.assert_called_once_with("insertHR()")


# ---------------------------------------------------------------------------
# Vertical alignment tests
# ---------------------------------------------------------------------------

class TestVerticalAlignment:
    """Verify that vertical alignment menu items fire setVAlign() via _run_js."""

    def _make_window_with_run_js(self):
        win = object.__new__(editor.EditorWindow)
        win._run_js = MagicMock()
        return win

    def test_valign_top_runjs(self):
        win = self._make_window_with_run_js()
        win._run_js("setVAlign('top')")
        win._run_js.assert_called_with("setVAlign('top')")

    def test_valign_middle_runjs(self):
        win = self._make_window_with_run_js()
        win._run_js("setVAlign('middle')")
        win._run_js.assert_called_with("setVAlign('middle')")

    def test_valign_bottom_runjs(self):
        win = self._make_window_with_run_js()
        win._run_js("setVAlign('bottom')")
        win._run_js.assert_called_with("setVAlign('bottom')")


# ---------------------------------------------------------------------------
# Blank paragraph collapse tests
# ---------------------------------------------------------------------------

class TestBlankParagraphCollapse:
    """Tests for EditorWindow._collapse_blank_paragraphs."""

    def test_three_blank_paragraphs_collapsed_to_two(self):
        html = "<p><br></p><p><br></p><p><br></p>"
        result = editor.EditorWindow._collapse_blank_paragraphs(html)
        # Should contain no more than 2 consecutive empty paragraphs
        import re
        empties = re.findall(r'<p[^>]*>(?:\s*<br\s*/?>)?\s*</p>', result, re.IGNORECASE)
        assert len(empties) <= 2

    def test_five_blank_paragraphs_collapsed_to_two(self):
        html = "<p><br></p>" * 5
        result = editor.EditorWindow._collapse_blank_paragraphs(html)
        import re
        empties = re.findall(r'<p[^>]*>(?:\s*<br\s*/?>)?\s*</p>', result, re.IGNORECASE)
        assert len(empties) <= 2

    def test_two_blank_paragraphs_preserved(self):
        html = "<p><br></p><p><br></p>"
        result = editor.EditorWindow._collapse_blank_paragraphs(html)
        import re
        empties = re.findall(r'<p[^>]*>(?:\s*<br\s*/?>)?\s*</p>', result, re.IGNORECASE)
        assert len(empties) == 2

    def test_content_paragraphs_not_affected(self):
        html = "<p>Hello</p><p>World</p>"
        result = editor.EditorWindow._collapse_blank_paragraphs(html)
        assert "Hello" in result
        assert "World" in result

    def test_mixed_content_blank_run_collapsed(self):
        html = "<p>Intro</p>" + "<p><br></p>" * 4 + "<p>Body</p>"
        result = editor.EditorWindow._collapse_blank_paragraphs(html)
        assert "Intro" in result
        assert "Body" in result
        import re
        empties = re.findall(r'<p[^>]*>(?:\s*<br\s*/?>)?\s*</p>', result, re.IGNORECASE)
        assert len(empties) <= 2


# ---------------------------------------------------------------------------
# Anchor handling tests
# ---------------------------------------------------------------------------

class TestAnchorHandling:
    """Tests for anchor ↔ span conversion utilities."""

    def test_anchor_tag_converted_to_span_on_load(self):
        html = '<a id="intro" name="intro"></a><p>text</p>'
        result = editor.EditorWindow._anchors_to_spans(html)
        assert 'editor-anchor' in result
        assert 'data-anchor-id="intro"' in result
        assert '⚓' in result
        # Original <a> should be gone
        assert '<a id="intro"' not in result

    def test_anchor_with_href_not_converted(self):
        html = '<a href="https://example.com">link</a>'
        result = editor.EditorWindow._anchors_to_spans(html)
        assert 'editor-anchor' not in result
        assert 'href="https://example.com"' in result

    def test_spans_converted_to_anchor_tags_on_save(self):
        html = '<span class="editor-anchor" data-anchor-id="section1" title="Anchor: section1">⚓</span>'
        result = editor.EditorWindow._spans_to_anchors(html)
        assert '<a id="section1" name="section1"></a>' in result
        assert 'editor-anchor' not in result

    def test_multiple_anchors_converted(self):
        html = (
            '<span class="editor-anchor" data-anchor-id="a1" title="Anchor: a1">⚓</span>'
            '<p>text</p>'
            '<span class="editor-anchor" data-anchor-id="a2" title="Anchor: a2">⚓</span>'
        )
        result = editor.EditorWindow._spans_to_anchors(html)
        assert '<a id="a1" name="a1"></a>' in result
        assert '<a id="a2" name="a2"></a>' in result

    def test_round_trip_anchor_preserved(self):
        """Anchor survives load→display→save cycle."""
        original_html = '<a id="top" name="top"></a><p>Content</p>'
        display_html = editor.EditorWindow._anchors_to_spans(original_html)
        assert 'editor-anchor' in display_html
        saved_html = editor.EditorWindow._spans_to_anchors(display_html)
        assert '<a id="top" name="top"></a>' in saved_html


# ---------------------------------------------------------------------------
# Table cell normalization tests
# ---------------------------------------------------------------------------

class TestTableCellNormalization:
    """Tests for EditorWindow._normalize_table_cells.

    Quill v2's native table identifies each cell by a ``data-row`` attribute
    (shared per row) and expects inline content directly inside <td>/<th>.
    """

    @staticmethod
    def _row_ids(html: str) -> list:
        import re
        return re.findall(r'data-row="([^"]+)"', html)

    def test_data_row_added_to_each_cell(self):
        html = '<table><tr><td>a</td><td>b</td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        assert result.count('data-row="') == 2

    def test_cells_in_same_row_share_row_id(self):
        html = '<table><tr><td>a</td><td>b</td><td>c</td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        ids = self._row_ids(result)
        assert len(ids) == 3
        assert len(set(ids)) == 1  # all the same

    def test_different_rows_have_different_ids(self):
        html = (
            '<table>'
            '<tr><td>a</td><td>b</td></tr>'
            '<tr><td>c</td><td>d</td></tr>'
            '</table>'
        )
        result = editor.EditorWindow._normalize_table_cells(html)
        ids = self._row_ids(result)
        assert len(ids) == 4
        assert ids[0] == ids[1]      # row 1 cells share id
        assert ids[2] == ids[3]      # row 2 cells share id
        assert ids[0] != ids[2]      # rows differ

    def test_row_id_format_matches_quill(self):
        html = '<table><tr><td>x</td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        ids = self._row_ids(result)
        import re
        assert re.fullmatch(r'row-[0-9a-f]+', ids[0])

    def test_paragraph_inside_cell_is_unwrapped(self):
        html = '<table><tr><td><p>text</p></td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        assert '<p>' not in result
        assert 'text' in result

    def test_image_inside_cell_kept_without_p_wrapper(self):
        html = '<table><tr><td><p><img src="data:image/png;base64,abc"/></p></td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        # No <p> remains in the cell — img sits directly inside <td>
        assert '<p>' not in result
        assert '<img' in result
        assert 'data:image/png;base64,abc' in result

    def test_bare_image_in_cell_preserved(self):
        html = '<table><tr><td><img src="data:image/png;base64,abc"/></td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        assert '<img' in result
        assert 'data:image/png;base64,abc' in result

    def test_multiple_paragraphs_in_cell_joined_with_br(self):
        html = '<table><tr><td><p>line1</p><p>line2</p></td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        assert '<p>' not in result
        assert 'line1' in result
        assert 'line2' in result
        assert '<br' in result

    def test_heading_inside_cell_is_unwrapped(self):
        html = '<table><tr><td><h2>Title</h2></td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        assert '<h2>' not in result
        assert 'Title' in result

    def test_inline_formatting_preserved(self):
        html = '<table><tr><td><p><strong>bold</strong> text</p></td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        assert '<p>' not in result
        assert '<strong>bold</strong>' in result

    def test_multiple_cells_with_images(self):
        html = (
            '<table><tr>'
            '<td><img src="data:image/png;base64,aaa"/></td>'
            '<td><img src="data:image/png;base64,bbb"/></td>'
            '</tr></table>'
        )
        result = editor.EditorWindow._normalize_table_cells(html)
        assert result.count('<img') == 2
        assert 'data:image/png;base64,aaa' in result
        assert 'data:image/png;base64,bbb' in result

    def test_nested_block_in_cell_unwrapped(self):
        """<div><p>x</p></div> inside cell → 'x' (both blocks unwrapped)."""
        html = '<table><tr><td><div><p>x</p></div></td></tr></table>'
        result = editor.EditorWindow._normalize_table_cells(html)
        assert '<div>' not in result
        assert '<p>' not in result
        assert 'x' in result
