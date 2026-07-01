"""Tests for src/editor_profile.py and src/filter_persistence.py."""

from unittest.mock import patch

import pytest

from editor_profile import EditorProfileStyler
from filter_persistence import FilterPersistence


class TestEditorProfileStyler:
    def test_init(self):
        styler = EditorProfileStyler({"name": "artscroises"})
        assert styler.current_profile == "artscroises"

    def test_init_default_name(self):
        styler = EditorProfileStyler({})
        assert styler.current_profile == "default"

    def test_get_profile_template_none_when_not_configured(self):
        styler = EditorProfileStyler({"name": "test"})
        assert styler.get_profile_template() is None

    def test_get_profile_template_file_exists(self, tmp_path):
        tmpl = tmp_path / "template.html"
        tmpl.write_text("<html></html>")
        styler = EditorProfileStyler({"template_file": str(tmpl)})
        assert styler.get_profile_template() == str(tmpl)

    def test_get_profile_template_file_missing_raises(self):
        styler = EditorProfileStyler({"template_file": "/nonexistent/template.html"})
        with pytest.raises(FileNotFoundError):
            styler.get_profile_template()

    def test_apply_profile_styling_passthrough(self):
        styler = EditorProfileStyler({"name": "test"})
        html = "<html><body>Hello</body></html>"
        assert styler.apply_profile_styling(html) == html

    def test_get_profile_theme(self):
        styler = EditorProfileStyler({"name": "Arts Croises"})
        assert styler.get_profile_theme() == "profile-arts-croises"

    def test_create_profile_css_empty_rules(self):
        css = EditorProfileStyler.create_profile_css("myprofile")
        assert ".profile-myprofile {" in css
        assert css.strip().endswith("}")

    def test_create_profile_css_with_rules(self):
        css = EditorProfileStyler.create_profile_css("myprofile", {"color": "red", "font-size": "12px"})
        assert "color: red;" in css
        assert "font-size: 12px;" in css

    def test_invalidate_cache_logs(self):
        styler = EditorProfileStyler({"name": "test"})
        with patch("editor_profile.logger") as mock_log:
            styler.invalidate_cache()
            mock_log.debug.assert_called_once()


class TestFilterPersistence:
    def test_init(self):
        fp = FilterPersistence({"name": "cambristi"})
        assert fp.profile_name == "cambristi"

    def test_init_default_name(self):
        fp = FilterPersistence({})
        assert fp.profile_name == "default"

    def test_save_filter(self):
        config: dict = {}
        fp = FilterPersistence(config)
        fp.save_filter({"status": "active"})
        assert config["filters"]["criteria"] == {"status": "active"}
        assert config["filters"]["active"] is True

    def test_save_filter_empty_raises(self):
        fp = FilterPersistence({})
        with pytest.raises(ValueError, match="cannot be empty"):
            fp.save_filter({})

    def test_save_filter_none_raises(self):
        fp = FilterPersistence({})
        with pytest.raises((ValueError, TypeError)):
            fp.save_filter(None)  # type: ignore[arg-type]

    def test_load_filters_none_when_not_set(self):
        fp = FilterPersistence({"name": "test"})
        assert fp.load_filters() is None

    def test_load_filters_returns_saved(self):
        config = {"filters": {"criteria": {"status": "active"}, "active": True}}
        fp = FilterPersistence(config)
        result = fp.load_filters()
        assert result == config["filters"]

    def test_validate_filter_criteria_valid(self):
        fp = FilterPersistence({})
        assert fp.validate_filter_criteria({"email": "x"}, ["email", "name"]) is True

    def test_validate_filter_criteria_invalid_column(self):
        fp = FilterPersistence({})
        assert fp.validate_filter_criteria({"ghost": "x"}, ["email", "name"]) is False

    def test_apply_filter_valid(self):
        fp = FilterPersistence({})
        criteria = {"email": "x"}
        result = fp.apply_filter(criteria, ["email", "name"])
        assert result == criteria

    def test_apply_filter_invalid_returns_empty(self):
        fp = FilterPersistence({})
        result = fp.apply_filter({"ghost": "x"}, ["email", "name"])
        assert result == {}

    def test_clear_filters(self):
        config = {"filters": {"criteria": {}, "active": True}}
        fp = FilterPersistence(config)
        fp.clear_filters()
        assert "filters" not in config

    def test_clear_filters_noop_when_not_set(self):
        config: dict = {}
        fp = FilterPersistence(config)
        fp.clear_filters()
        assert config == {}
