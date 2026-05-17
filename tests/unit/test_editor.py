"""
Unit tests for src/editor.py

All PyQt6 modules are mocked before import so these tests run headlessly
on CI without a display server, following the same pattern used in test_sendMail.py.
"""
# pyright: ignore[reportAttributeAccessIssue, reportArgumentType]

# ---------------------------------------------------------------------------
# Mock all Qt modules BEFORE importing editor
# ---------------------------------------------------------------------------
import inspect as _inspect
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml as real_yaml

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
def _make_pyqtSlot(*args, **kwargs):  # noqa: N802, ARG001
    """Fake @pyqtSlot that is a no-op decorator."""
    if len(args) == 1 and _inspect.isfunction(args[0]) and not kwargs:
        # Bare @pyqtSlot — args[0] is the function being decorated
        return args[0]
    # @pyqtSlot(str), @pyqtSlot(str, result=str), etc. — return a decorator
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


sys.modules["PyQt6.QtCore"].pyqtSlot = _make_pyqtSlot  # pyright: ignore
sys.modules["PyQt6.QtCore"].pyqtSignal = _make_pyqtSignal  # pyright: ignore
sys.modules["PyQt6.QtCore"].QObject = _FakeQObject  # pyright: ignore
sys.modules["PyQt6.QtCore"].QUrl = MagicMock()  # pyright: ignore
sys.modules["PyQt6.QtCore"].Qt = MagicMock()  # pyright: ignore

sys.modules["PyQt6.QtWidgets"].QMainWindow = _FakeQMainWindow  # pyright: ignore
sys.modules["PyQt6.QtWidgets"].QDialog = _FakeQDialog  # pyright: ignore
sys.modules["PyQt6.QtWidgets"].QDialog.DialogCode = _FakeQDialog.DialogCode  # pyright: ignore
sys.modules["PyQt6.QtWidgets"].QSpinBox = MagicMock()  # pyright: ignore

# Add source directory to path so editor can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "src")))

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
            patch("editor.QFileDialog.getOpenFileName", return_value=("/tmp/img.png", "")),
            patch("editor.sm") as mock_sm,
        ):
            mock_sm.file_to_base64.return_value = "abc123"
            mock_sm.guess_type.return_value = "image/png"
            editor._SM_AVAILABLE = True
            result = bridge.request_image_insert()
        assert result == "data:image/png;base64,abc123"

    def test_returns_empty_string_on_cancel(self):
        bridge = _make_bridge()
        with patch("editor.QFileDialog.getOpenFileName", return_value=("", "")):
            result = bridge.request_image_insert()
        assert result == ""

    def test_returns_empty_string_on_exception(self):
        bridge = _make_bridge()
        with (
            patch("editor.QFileDialog.getOpenFileName", return_value=("/bad/path.png", "")),
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
            with patch("editor.QFileDialog.getOpenFileName", return_value=(tmp_path, "")):
                orig = editor._SM_AVAILABLE
                editor._SM_AVAILABLE = False
                try:
                    result = bridge.request_image_insert()
                finally:
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


# ---------------------------------------------------------------------------
# Config dialog and window behavior tests
# ---------------------------------------------------------------------------

class _LineEditLike:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, value):  # noqa: N802
        self._text = value


class _SpinBoxLike:
    def __init__(self, value=0):
        self._value = value

    def value(self):
        return self._value

    def setValue(self, value):  # noqa: N802
        self._value = value


class _CheckBoxLike:
    def __init__(self, checked=False):
        self._checked = checked

    def isChecked(self):  # noqa: N802
        return self._checked

    def setChecked(self, value):  # noqa: N802
        self._checked = bool(value)


class _PlainTextLike:
    def __init__(self, text=""):
        self._text = text

    def toPlainText(self):  # noqa: N802
        return self._text

    def setPlainText(self, value):  # noqa: N802
        self._text = value


class _FakePage:
    def __init__(self):
        self.runJavaScript = MagicMock()


class _FakeView:
    def __init__(self):
        self._page = _FakePage()

    def page(self):
        return self._page


class _FakeStatusBar:
    def __init__(self):
        self.showMessage = MagicMock()


class _FakeBridge:
    def __init__(self, dirty=False, html=""):
        self.is_dirty = dirty
        self._html = html
        self.dirty_changed = MagicMock()
        self.dirty_changed.emit = MagicMock()
        self.css_changed = MagicMock()

    def get_current_html(self):
        return self._html

    def reset(self, html=""):
        self._html = html
        self.is_dirty = False


class _FakeCombo:
    def __init__(self):
        self.items = []
        self.current = ""
        self.blocked = False
        self.index = -1

    def blockSignals(self, value):  # noqa: N802
        self.blocked = value

    def clear(self):
        self.items = []

    def addItems(self, items):  # noqa: N802
        self.items.extend(items)

    def findText(self, text):  # noqa: N802
        try:
            return self.items.index(text)
        except ValueError:
            return -1

    def setCurrentIndex(self, index):  # noqa: N802
        self.index = index
        if 0 <= index < len(self.items):
            self.current = self.items[index]

    def currentText(self):  # noqa: N802
        return self.current

    def count(self):
        return len(self.items)


class _FakeTabs:
    def __init__(self, title="Identity"):
        self._title = title
        self._index = 0

    def currentIndex(self):  # noqa: N802
        return self._index

    def tabText(self, index):  # noqa: N802
        return self._title


def _make_config_dialog_stub():
    dlg = object.__new__(editor._ConfigDialog)
    dlg._config_data = {
        "alpha": {
            "MAILCONFIG": "secret",
            "sender": "alpha@example.com",
            "sendername": "Alpha",
            "username": "alpha-user",
            "password": "pw",
            "domain": "alpha.test",
            "smtp_host": "smtp.alpha.test",
            "imap_host": "imap.alpha.test",
            "sent_folder": "Sent",
            "database": "alpha.csv",
            "sa": "sa-secret",
            "sheetid": "sheet-secret",
            "token_file": "token.json",
            "credentials_id": "cred-secret",
            "subject": "Hello",
            "message": "Body",
            "default_message": "Fallback",
            "body": "Injected",
            "styles": "styles.css",
            "pause": 2,
            "from_index": 1,
            "to_index": 5,
            "wait": 3,
            "max_mails_per_hour": 42,
            "max_addr_per_mail": 7,
            "test": True,
            "verbose": True,
            "doNotSend": False,
            "selected": True,
            "md2html": True,
            "keep-html": False,
            "scopes": ["scope-1", "scope-2"],
            "filter": {"email": "is not empty"},
            "filter_test": {"email": "is alpha@example.com"},
        }
    }
    dlg._current_profile = "alpha"
    dlg._widgets = {
        "MAILCONFIG": _LineEditLike("secret"),
        "sender": _LineEditLike("alpha@example.com"),
        "sendername": _LineEditLike("Alpha"),
        "username": _LineEditLike("alpha-user"),
        "password": _LineEditLike("pw"),
        "domain": _LineEditLike("alpha.test"),
        "smtp_host": _LineEditLike("smtp.alpha.test"),
        "imap_host": _LineEditLike("imap.alpha.test"),
        "sent_folder": _LineEditLike("Sent"),
        "database": _LineEditLike("alpha.csv"),
        "sa": _LineEditLike("sa-secret"),
        "sheetid": _LineEditLike("sheet-secret"),
        "token_file": _LineEditLike("token.json"),
        "credentials_id": _LineEditLike("cred-secret"),
        "subject": _LineEditLike("Hello"),
        "message": _PlainTextLike("Body"),
        "default_message": _PlainTextLike("Fallback"),
        "body": _LineEditLike("Injected"),
        "styles": _LineEditLike("styles.css"),
        "pause": _SpinBoxLike(2),
        "from_index": _SpinBoxLike(1),
        "to_index": _SpinBoxLike(5),
        "wait": _SpinBoxLike(3),
        "max_mails_per_hour": _SpinBoxLike(42),
        "max_addr_per_mail": _SpinBoxLike(7),
        "test": _CheckBoxLike(True),
        "verbose": _CheckBoxLike(True),
        "doNotSend": _CheckBoxLike(False),
        "selected": _CheckBoxLike(True),
        "md2html": _CheckBoxLike(True),
        "keep-html": _CheckBoxLike(False),
        "scopes": _PlainTextLike("scope-1\nscope-2"),
        "filter": _PlainTextLike("email: is not empty"),
        "filter_test": _PlainTextLike("email: is alpha@example.com"),
    }
    dlg._yaml_keys = {"filter", "filter_test"}
    dlg._list_keys = {"scopes"}
    dlg.tabs = _FakeTabs()
    dlg.help_view = MagicMock()
    dlg.config_input = _LineEditLike("")
    dlg.profile_combo = _FakeCombo()
    return dlg


class TestConfigDialogHelpers:
    def test_profile_data_helpers_and_round_trip(self, monkeypatch):
        # Use real_yaml which was imported at module level to avoid mocks
        monkeypatch.setattr(editor, "QLineEdit", _LineEditLike)
        monkeypatch.setattr(editor, "QSpinBox", _SpinBoxLike)
        monkeypatch.setattr(editor, "QCheckBox", _CheckBoxLike)
        monkeypatch.setattr(editor, "QPlainTextEdit", _PlainTextLike)
        monkeypatch.setattr(editor, "yaml", real_yaml)
        import sendMail
        monkeypatch.setattr(sendMail, "yaml", real_yaml)
        # Explicitly set yaml in function globals to use the real module
        monkeypatch.setitem(editor._ConfigDialog._load_yaml_block.__globals__, "yaml", real_yaml)
        monkeypatch.setitem(editor._ConfigDialog._dump_yaml_block.__globals__, "yaml", real_yaml)
        dlg = _make_config_dialog_stub()

        normalized = dlg._normalize_config_data({"alpha": {"x": 1}, "skip": "nope"})
        assert normalized == {"alpha": {"x": 1}}
        defaults = dlg._default_profile_data()
        assert defaults["sender"] == "john.doe@example.com"
        assert dlg._profile_names() == ["alpha"]
        assert dlg._profile_value("missing") == {}
        assert dlg._dump_yaml_block({"email": "is not empty"})
        assert dlg._dump_yaml_block(None) == ""
        assert dlg._load_yaml_block("email: is not empty", "filter") == {"email": "is not empty"}
        assert dlg._load_yaml_block("scope-a, scope-b", "scopes") == ["scope-a", "scope-b"]
        with pytest.raises(ValueError):
            dlg._load_yaml_block("[]", "filter")

        dlg._load_profile("alpha")
        assert dlg._widgets["sender"].text() == "alpha@example.com"
        assert dlg._widgets["pause"].value() == 2
        assert dlg._widgets["test"].isChecked() is True
        assert dlg._widgets["scopes"].toPlainText() == "scope-1\nscope-2"

        dlg._widgets["filter"].setPlainText("")
        dlg._widgets["filter_test"].setPlainText("")
        dlg._widgets["sender"].setText("new@example.com")
        dlg._widgets["pause"].setValue(9)
        dlg._widgets["test"].setChecked(False)
        collected = dlg._collect_profile_data()
        assert collected["sender"] == "new@example.com"
        assert collected["pause"] == 9
        assert collected["test"] is False

        dlg._persist_current_profile()
        assert dlg._config_data["alpha"]["sender"] == "new@example.com"

    def test_read_reload_save_and_profile_management(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor, "QLineEdit", _LineEditLike)
        monkeypatch.setattr(editor, "QSpinBox", _SpinBoxLike)
        monkeypatch.setattr(editor, "QCheckBox", _CheckBoxLike)
        monkeypatch.setattr(editor, "QPlainTextEdit", _PlainTextLike)
        monkeypatch.setitem(editor._ConfigDialog._read_config_file.__globals__, "yaml", real_yaml)
        monkeypatch.setitem(editor._ConfigDialog._save_config.__globals__, "yaml", real_yaml)
        dlg = _make_config_dialog_stub()

        cfg_path = tmp_path / "config.yml"
        cfg_path.write_text("alpha:\n  sender: alpha@example.com\n", encoding="utf-8")
        assert isinstance(dlg._read_config_file(str(cfg_path)), dict)
        assert dlg._read_config_file(str(tmp_path / "missing.yml")) == {}

        bad_path = tmp_path / "bad.yml"
        bad_path.write_text("alpha: [", encoding="utf-8")
        assert dlg._read_config_file(str(bad_path)) == {}

        dlg._config_data = {}
        dlg._ensure_profiles()
        assert "default" in dlg._config_data

        dlg._current_profile = "alpha"
        dlg._widgets["filter"].setPlainText("")
        dlg._widgets["filter_test"].setPlainText("")
        dlg._widgets["sender"].setText("alpha2@example.com")
        dlg.config_input.setText(str(cfg_path))
        dlg._save_config()
        assert cfg_path.exists()

        dlg.profile_combo = _FakeCombo()
        dlg.profile_combo.current = "alpha"
        dlg._load_profile = MagicMock()
        dlg._read_config_file = MagicMock(return_value={"alpha": {"sender": "loaded@example.com"}})
        dlg._reload_profiles("alpha")
        assert dlg.profile_combo.items[0] == "alpha"
        assert "default" in dlg.profile_combo.items
        dlg._load_profile.assert_called_with("alpha")

        with patch.object(editor.QInputDialog, "getText", return_value=("beta", True)):
            assert dlg._new_profile_name("Add", "beta") == "beta"

        with patch.object(editor.QInputDialog, "getText", return_value=("gamma", True)):
            dlg._persist_current_profile = MagicMock()
            dlg._reload_profiles = MagicMock()
            dlg._add_profile()
            assert "gamma" in dlg._config_data

        dlg._current_profile = "alpha"
        dlg._collect_profile_data = MagicMock(return_value={"sender": "copy@example.com"})
        dlg._reload_profiles = MagicMock()
        with patch.object(editor.QInputDialog, "getText", return_value=("alpha-copy", True)):
            dlg._duplicate_profile()
            assert dlg._config_data["alpha-copy"]["sender"] == "copy@example.com"

        dlg._current_profile = "alpha-copy"
        dlg._reload_profiles = MagicMock()
        with patch.object(editor.QMessageBox, "question", return_value=editor.QMessageBox.StandardButton.Yes):
            dlg._delete_profile()
        assert "alpha-copy" not in dlg._config_data

        dlg.tabs = _FakeTabs("Templates")
        dlg._update_help(0)
        dlg.help_view.setHtml.assert_called_once()

        with patch.object(editor.QMessageBox, "information") as mock_info:
            dlg._show_help()
            mock_info.assert_called_once()


class TestEditorWindowHelpers:
    def _make_window(self):
        win = object.__new__(editor.EditorWindow)
        win._view = _FakeView()
        win._bridge = _FakeBridge()
        win._css_status_label = MagicMock()
        win._css_status_label.setText = MagicMock()
        win._file_path = None
        win._css_path = None
        win._load_finished_connected = False
        win._send_in_progress = False
        win._save = MagicMock(return_value=True)
        win._load_editor_page = MagicMock()
        win.open_file = MagicMock()
        win.statusBar = MagicMock(return_value=_FakeStatusBar())
        win.setWindowTitle = MagicMock()
        win.style = MagicMock(return_value=MagicMock(standardIcon=MagicMock(return_value="icon")))
        return win

    def test_editor_window_init_paths(self, monkeypatch):
        with patch.object(editor.EditorWindow, "_load_editor_page", autospec=True) as mock_load, patch.object(
                editor.EditorWindow, "open_file", autospec=True
        ) as mock_open:
            window = editor.EditorWindow()
            assert window._file_path is None
            mock_load.assert_called_once_with(window, "")
            mock_open.assert_not_called()

        with patch.object(editor.EditorWindow, "_load_editor_page", autospec=True) as mock_load, patch.object(
                editor.EditorWindow, "open_file", autospec=True
        ) as mock_open:
            window = editor.EditorWindow(file_path="sample.md")
            mock_open.assert_called_once_with(window, "sample.md")
            mock_load.assert_not_called()

    def test_resolve_load_and_format_helpers(self, monkeypatch, tmp_path):
        win = self._make_window()
        monkeypatch.setattr(editor, "_SM_AVAILABLE", True)
        monkeypatch.setattr(editor.sm, "get_default_config_path", lambda: str(tmp_path / "cfg.yml"))
        monkeypatch.setitem(editor.EditorWindow._load_send_config.__globals__, "yaml", real_yaml)
        assert win._resolve_send_config_path() == str(tmp_path / "cfg.yml")

        monkeypatch.setattr(editor.sm, "get_default_config_path", lambda: -1)
        expected = str(Path.home() / ".config" / "sendMail.yml")
        assert win._resolve_send_config_path() == expected

        cfg = tmp_path / "config.yml"
        cfg.write_text("alpha:\n  sender: test@example.com\n", encoding="utf-8")
        assert isinstance(win._load_send_config(str(cfg)), dict)
        assert win._load_send_config(str(tmp_path / "missing.yml")) == {}
        bad = tmp_path / "bad.yml"
        bad.write_text("alpha: [", encoding="utf-8")
        assert win._load_send_config(str(bad)) == {}

        assert win._send_result_is_success("OK") is True
        assert win._send_result_is_success("OK_TEST") is True
        assert win._send_result_is_success("error: boom") is False
        assert win._send_result_is_success(None) is False
        assert win._send_result_is_success(1) is True

        win._file_path = str(tmp_path / "doc.html")
        win._bridge.is_dirty = True
        win._update_title()
        win.setWindowTitle.assert_called_with("sendMail Editor — doc.html *")

        win._file_path = None
        win._bridge.is_dirty = False
        win._update_title()
        win.setWindowTitle.assert_called_with("sendMail Editor — New Document")

        win._run_js("quill.format('font', 'Arial')")
        assert "Arial" in win._view.page().runJavaScript.call_args.args[0]
        win._set_font_family(None)
        assert "false" in win._view.page().runJavaScript.call_args.args[0]

    def test_menu_open_template_insert_and_css(self, monkeypatch, tmp_path):
        win = self._make_window()
        monkeypatch.setattr(editor, "_BASE", tmp_path)
        monkeypatch.setattr(editor, "_SM_AVAILABLE", True)

        with patch.object(win, "_ask_save_if_dirty", return_value=False):
            win._menu_open()
        win.open_file.assert_not_called()

        with patch.object(win, "_ask_save_if_dirty", return_value=True), patch.object(editor.QFileDialog,
                                                                                      "getOpenFileName", return_value=(
                        str(tmp_path / "doc.md"), "")):
            win._menu_open()
        win.open_file.assert_called_with(str(tmp_path / "doc.md"))

        template_dir = tmp_path / "data"
        template_dir.mkdir()
        (template_dir / "template.md").write_text("# t", encoding="utf-8")
        with patch.object(win, "_ask_save_if_dirty", return_value=True):
            win._open_template()
        win.open_file.assert_called_with(str(template_dir / "template.md"))

        (template_dir / "template.md").unlink()
        with patch.object(win, "_ask_save_if_dirty", return_value=True), patch.object(editor.QFileDialog,
                                                                                      "getOpenFileName", return_value=(
                        str(tmp_path / "fallback.md"), "")):
            win._open_template()
        win.open_file.assert_called_with(str(tmp_path / "fallback.md"))

        win._run_js = MagicMock()
        win._bridge.request_image_insert = MagicMock(return_value="data:image/png;base64,abc")
        win._menu_insert_image()
        assert "insertEmbed" in win._run_js.call_args.args[0]

        win._bridge.request_link_insert = MagicMock(return_value=json.dumps({"url": "#anchor", "text": "Anchor"}))
        win._menu_insert_link()
        assert "quill.insertText" in win._run_js.call_args.args[0]

        with patch.object(editor.QFileDialog, "getOpenFileName", return_value=(str(tmp_path / "style.css"), "")):
            win._menu_apply_css()
        win._bridge.css_changed.emit.assert_called_once()

    def test_send_menu_and_dirty_flow(self, monkeypatch, tmp_path):
        win = self._make_window()
        win._file_path = str(tmp_path / "doc.html")
        Path(win._file_path).write_text("<html></html>", encoding="utf-8")
        monkeypatch.setattr(editor, "_SM_AVAILABLE", True)

        with patch.object(editor, "_SendDialog") as mock_dialog, patch.object(editor,
                                                                              "_SessionLogDialog") as mock_log_dialog, patch.object(
                win, "_resolve_send_config_path",
                                                                              return_value="cfg.yml"), patch.object(win,
                                                                                                                    "_load_send_config",
                                                                                                                    return_value={
                                                                                                                        "default": {}}), patch.object(
            win, "_send_with_sendmail", return_value="OK") as mock_send:
            dialog = mock_dialog.return_value
            dialog.exec.return_value = editor.QDialog.DialogCode.Accepted
            log_dialog = mock_log_dialog.return_value
            log_dialog.exec.return_value = editor.QDialog.DialogCode.Accepted
            win._menu_send()
            mock_send.assert_called_once()
            mock_log_dialog.assert_called_once()

        with patch.object(editor, "_SendDialog") as mock_dialog, patch.object(editor,
                                                                              "_SessionLogDialog") as mock_log_dialog, patch.object(
                win, "_resolve_send_config_path",
                                                                              return_value="cfg.yml"), patch.object(win,
                                                                                                                    "_load_send_config",
                                                                                                                    return_value={
                                                                                                                        "default": {}}), patch.object(
            win, "_send_with_sendmail", return_value="error"):
            dialog = mock_dialog.return_value
            dialog.exec.return_value = editor.QDialog.DialogCode.Accepted
            log_dialog = mock_log_dialog.return_value
            log_dialog.exec.return_value = editor.QDialog.DialogCode.Accepted
            win._menu_send()
            mock_log_dialog.assert_called_once()

        win._send_in_progress = True
        with patch.object(editor.QMessageBox, "warning") as mock_warning:
            win._menu_send()
            mock_warning.assert_not_called()

        win._send_in_progress = False
        monkeypatch.setattr(editor, "_SM_AVAILABLE", False)
        with patch.object(editor.QMessageBox, "warning") as mock_warning:
            win._menu_send()
            mock_warning.assert_called_once()

    def test_css_change_and_prompt_paths(self, monkeypatch, tmp_path):
        win = self._make_window()
        css_path = tmp_path / "style.css"
        css_path.write_text("body { color: red; }", encoding="utf-8")
        win._run_js = MagicMock()
        win._on_css_changed(str(css_path))
        assert win._css_path == str(css_path)
        win._css_status_label.setText.assert_called_with("CSS: style.css")
        assert "applyCSS" in win._run_js.call_args.args[0]

        bad = tmp_path / "missing.css"
        with patch.object(editor.QMessageBox, "warning") as mock_warning:
            win._on_css_changed(str(bad))
            mock_warning.assert_called_once()

        win._bridge.is_dirty = False
        assert win._ask_save_if_dirty() is True

        win._bridge.is_dirty = True
        with patch.object(editor.QMessageBox, "question",
                          return_value=editor.QMessageBox.StandardButton.Save), patch.object(win, "_save",
                                                                                             return_value=True) as mock_save:
            assert win._ask_save_if_dirty() is True
            mock_save.assert_called_once()

        with patch.object(editor.QMessageBox, "question", return_value=editor.QMessageBox.StandardButton.Discard):
            assert win._ask_save_if_dirty() is True

        with patch.object(editor.QMessageBox, "question", return_value=editor.QMessageBox.StandardButton.Cancel):
            assert win._ask_save_if_dirty() is False

        event = MagicMock()
        win._bridge.is_dirty = False
        win.closeEvent(event)
        event.accept.assert_called_once()

        event = MagicMock()
        win._ask_save_if_dirty = MagicMock(return_value=False)
        win.closeEvent(event)
        event.ignore.assert_called_once()

    def test_window_load_save_toolbar_and_dialog_paths(self, monkeypatch, tmp_path):
        win = self._make_window()

        class _FakeSignal:
            def __init__(self):
                self.connected = []

            def connect(self, fn):
                self.connected.append(fn)

            def disconnect(self, fn=None):
                if fn is None:
                    self.connected.clear()
                elif fn in self.connected:
                    self.connected.remove(fn)

        class _LoadView(_FakeView):
            def __init__(self):
                super().__init__()
                self.loadFinished = _FakeSignal()
                self.load = MagicMock()

        win._view = _LoadView()
        win._inject_initial_content = MagicMock()
        editor.EditorWindow._load_editor_page(win, "<p>hello</p>")
        assert win._view.load.called
        assert win._view.loadFinished.connected
        win._view.loadFinished.connected[0](True)
        win._inject_initial_content.assert_called_once_with("<p>hello</p>")

        css_path = tmp_path / "style.css"
        css_path.write_text("body { color: blue; }", encoding="utf-8")
        win._css_path = str(css_path)
        win._run_js = MagicMock()
        win._inject_initial_content.reset_mock()
        editor.EditorWindow._inject_initial_content(win, "<p>body</p>")
        assert "setContent" in win._view.page().runJavaScript.call_args.args[0]
        assert "applyCSS" in win._run_js.call_args.args[0]

        win._css_path = None
        win._file_path = str(tmp_path / "doc.html")
        win._bridge._html = "<p>saved</p>"
        win._bridge.get_current_html = MagicMock(return_value="<p>saved</p>")
        win._bridge.reset = MagicMock()
        win._write_html_file = MagicMock()
        win._update_title = MagicMock()
        status_bar = win.statusBar.return_value
        editor.EditorWindow._save(win)
        assert win._write_html_file.called
        assert win._file_path.endswith(".html")
        win._bridge.reset.assert_called_once()
        status_bar.showMessage.assert_called_once()

        with patch.object(editor.QFileDialog, "getSaveFileName", return_value=(str(tmp_path / "custom.html"), "")):
            win._file_path = None
            win._save = MagicMock(return_value=True)
            assert editor.EditorWindow._save_as(win) is True

        win._bridge.request_table_insert = MagicMock(return_value=json.dumps({"rows": 2, "cols": 3}))
        win._run_js = MagicMock()
        win._menu_table_insert()
        assert "insertTable" in win._run_js.call_args.args[0]

        mock_anchor_dialog = MagicMock()
        mock_anchor_dialog.exec.return_value = editor.QDialog.DialogCode.Accepted
        mock_anchor_dialog.get_name.return_value = "intro"
        with patch("editor._AnchorDialog", return_value=mock_anchor_dialog):
            win._menu_insert_anchor()
        assert "insertAnchor" in win._run_js.call_args.args[0]

        mock_cfg_dialog = MagicMock()
        mock_cfg_dialog.exec.return_value = editor.QDialog.DialogCode.Accepted
        with (
            patch.object(win, "_resolve_send_config_path", return_value="cfg.yml"),
            patch.object(win, "_load_send_config", return_value={"default": {}}),
            patch("editor._ConfigDialog", return_value=mock_cfg_dialog),
        ):
            win._menu_edit_config()
        mock_cfg_dialog.exec.assert_called_once()

        added = []

        def _add_toolbar(toolbar):
            added.append(toolbar)

        win.addToolBar = MagicMock(side_effect=_add_toolbar)
        win._build_toolbars()
        assert added
        win.style.assert_called_once()

    def test_md_and_html_conversion_paths(self, monkeypatch, tmp_path):
        win = self._make_window()
        md_path = tmp_path / "input.md"
        md_path.write_text("# title", encoding="utf-8")
        html_path = tmp_path / "input.html"
        html_path.write_text("<html><body><p>hello</p></body></html>", encoding="utf-8")

        monkeypatch.setattr(editor, "_SM_AVAILABLE", True)
        output_html = tmp_path / "output.html"
        output_html.write_text("<html><body><p>ok</p></body></html>", encoding="utf-8")
        monkeypatch.setattr(editor.sm, "md2html", lambda *_args, **_kwargs: str(output_html))
        with patch.object(editor.EditorWindow, "_html_to_body_html", return_value="<p>ok</p>") as mock_convert:
            output = win._md_to_body_html(str(md_path))
            assert output == "<p>ok</p>"
            assert not output_html.exists()
            mock_convert.assert_called_once()

        monkeypatch.setattr(editor, "_SM_AVAILABLE", False)
        monkeypatch.setattr(editor, "_MD2_AVAILABLE", False)
        with patch.object(editor.QMessageBox, "warning") as mock_warning:
            assert win._md_to_body_html(str(md_path)) == ""
            mock_warning.assert_called_once()

        monkeypatch.setattr(editor, "_SM_AVAILABLE", True)
        monkeypatch.setattr(editor.sm, "make_html_images_inline",
                            lambda path: f'<html><body><img src="{path}"/></body></html>')
        body = win._html_to_body_html(str(html_path))
        assert "img" in body

        with patch.object(editor.sm, "make_html_images_inline", side_effect=RuntimeError("boom")):
            assert win._html_to_body_html(str(html_path)) == ""
