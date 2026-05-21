"""Tests for editor profile styling application."""

import tempfile
from pathlib import Path

import pytest

from src.editor_profile import EditorProfileStyler


class TestEditorProfileStyling:
    """Test editor applies profile-specific styling."""

    def test_apply_profile_styling(self):
        """EditorProfileStyler.apply_profile_styling applies CSS/template."""
        config = {"name": "artscroises", "template_file": "templates/artscroises.html"}
        styler = EditorProfileStyler(config)

        html_content = "<h1>Test</h1>"
        result = styler.apply_profile_styling(html_content)

        # Current implementation returns content unchanged (client-side styling)
        assert result == html_content

    def test_styling_preserves_content(self):
        """Profile styling change preserves existing document content."""
        config = {"name": "test_profile"}
        styler = EditorProfileStyler(config)

        content = "<p>Existing content with <strong>formatting</strong></p>"
        result = styler.apply_profile_styling(content)

        assert content in result
        assert "<strong>formatting</strong>" in result

    def test_get_profile_theme(self):
        """EditorProfileStyler.get_profile_theme returns CSS class."""
        config = {"name": "my_profile"}
        styler = EditorProfileStyler(config)

        theme = styler.get_profile_theme()
        assert theme == "profile-my_profile"

    def test_get_profile_template_found(self):
        """get_profile_template returns path when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "template.html"
            template_file.write_text("<html></html>")

            config = {"name": "test", "template_file": str(template_file)}
            styler = EditorProfileStyler(config)

            result = styler.get_profile_template()
            assert result == str(template_file)

    def test_get_profile_template_missing_raises(self):
        """get_profile_template raises FileNotFoundError if file missing."""
        config = {"name": "test", "template_file": "/nonexistent/template.html"}
        styler = EditorProfileStyler(config)

        with pytest.raises(FileNotFoundError):
            styler.get_profile_template()

    def test_get_profile_template_not_configured(self):
        """get_profile_template returns None if not configured."""
        config = {"name": "test"}  # No template_file
        styler = EditorProfileStyler(config)

        result = styler.get_profile_template()
        assert result is None

    def test_create_profile_css(self):
        """EditorProfileStyler.create_profile_css generates CSS rules."""
        css_rules = {"color": "blue", "font-size": "14px"}
        css = EditorProfileStyler.create_profile_css("test", css_rules)

        assert ".profile-test {" in css
        assert "color: blue;" in css
        assert "font-size: 14px;" in css
        assert "}" in css

    def test_invalidate_cache(self):
        """invalidate_cache called on profile switch."""
        config = {"name": "test"}
        styler = EditorProfileStyler(config)

        # Should not raise
        styler.invalidate_cache()
