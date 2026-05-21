"""
Tests for filter_matcher.py and schema_provider.py.

Uses sys.modules mocking (same pattern as test_sendMail.py / test_coverage_gap.py)
so that sendMail is importable when FilterMatcher tries to import it inside __init__.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Mock heavy dependencies before any source import
# ---------------------------------------------------------------------------
for _mod in [
    "gspread",
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
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "src"))
)

from filter_matcher import FilterMatcher  # noqa: E402
from schema_provider import DatabaseSchemaProvider  # noqa: E402

# ===========================================================================
# FilterMatcher tests
# ===========================================================================


class TestFilterMatcherInit:
    def test_available_when_sendmail_importable(self):
        mock_sm = MagicMock()
        mock_sm.filter = MagicMock(return_value=False)
        with patch.dict(sys.modules, {"sendMail": mock_sm}):
            fm = FilterMatcher()
        assert fm.is_available() is True
        assert fm._filter_fn is mock_sm.filter

    def test_unavailable_when_sendmail_none(self):
        saved = sys.modules.pop("sendMail", None)
        try:
            with patch.dict(sys.modules, {"sendMail": None}):
                fm = FilterMatcher()
            assert fm.is_available() is False
            assert fm._filter_fn is None
        finally:
            if saved is not None:
                sys.modules["sendMail"] = saved

    def test_unavailable_when_no_filter_attr(self):
        mock_sm = MagicMock(spec=[])  # No 'filter' attribute
        with patch.dict(sys.modules, {"sendMail": mock_sm}):
            fm = FilterMatcher()
        assert fm.is_available() is False


class TestFilterMatcherMatchRow:
    def _make_fm(self, filter_result: bool = False) -> FilterMatcher:
        fm = FilterMatcher.__new__(FilterMatcher)
        fm._available = True
        fm._filter_fn = MagicMock(return_value=filter_result)
        return fm

    def test_returns_true_when_not_available(self):
        fm = self._make_fm()
        fm._available = False
        assert fm.match_row(["a"], {"name": "is a"}, ["name"]) is True

    def test_returns_true_when_empty_filter(self):
        fm = self._make_fm()
        assert fm.match_row(["a"], {}, ["name"]) is True

    def test_returns_true_when_empty_row(self):
        fm = self._make_fm()
        assert fm.match_row([], {"name": "is a"}, ["name"]) is True

    def test_returns_true_when_no_headers(self):
        fm = self._make_fm()
        assert fm.match_row(["a"], {"name": "is a"}, []) is True

    def test_returns_true_when_no_filter_fn(self):
        fm = self._make_fm()
        fm._filter_fn = None
        assert fm.match_row(["a"], {"name": "is a"}, ["name"]) is True

    def test_returns_false_when_excluded(self):
        # sendMail.filter returns True to exclude a row
        fm = self._make_fm(filter_result=True)
        assert fm.match_row(["a"], {"name": "is a"}, ["name"]) is False

    def test_returns_true_when_included(self):
        # sendMail.filter returns False to include a row
        fm = self._make_fm(filter_result=False)
        assert fm.match_row(["a"], {"name": "is a"}, ["name"]) is True

    def test_builds_correct_indices(self):
        fm = self._make_fm()
        headers = ["email", "name", "status"]
        fm.match_row(["a@b.com", "Alice", "active"], {"status": "is active"}, headers)
        passed_indices = fm._filter_fn.call_args[0][2]
        assert passed_indices == {"email": 0, "name": 1, "status": 2}

    def test_returns_true_on_exception(self):
        fm = self._make_fm()
        fm._filter_fn.side_effect = Exception("unexpected error")
        assert fm.match_row(["a"], {"name": "is a"}, ["name"]) is True


class TestFilterMatcherFilterRows:
    def _make_fm(self, filter_result: bool = False) -> FilterMatcher:
        fm = FilterMatcher.__new__(FilterMatcher)
        fm._available = True
        fm._filter_fn = MagicMock(return_value=filter_result)
        return fm

    def test_empty_filter_returns_all_rows(self):
        fm = self._make_fm()
        rows = [["a"], ["b"], ["c"]]
        assert fm.filter_rows(rows, {}, ["name"]) == rows

    def test_filter_keeps_matching_rows(self):
        def exclude_b(_flt, row, _idx):
            return row[0] == "b"

        fm = self._make_fm()
        fm._filter_fn = exclude_b
        rows = [["a"], ["b"], ["c"]]
        result = fm.filter_rows(rows, {"name": "is not b"}, ["name"])
        assert result == [["a"], ["c"]]

    def test_filter_excludes_all(self):
        fm = self._make_fm(filter_result=True)
        rows = [["a"], ["b"]]
        assert fm.filter_rows(rows, {"name": "is z"}, ["name"]) == []

    def test_filter_includes_all(self):
        fm = self._make_fm(filter_result=False)
        rows = [["a"], ["b"]]
        assert fm.filter_rows(rows, {"name": "is a"}, ["name"]) == rows

    def test_empty_rows(self):
        fm = self._make_fm()
        assert fm.filter_rows([], {"name": "is a"}, ["name"]) == []


class TestFilterMatcherFilterRowsWithCount:
    def test_returns_rows_and_original_count(self):
        fm = FilterMatcher.__new__(FilterMatcher)
        fm._available = False
        rows = [["a"], ["b"], ["c"]]
        filtered, total = fm.filter_rows_with_count(rows, {}, ["name"])
        assert filtered == rows
        assert total == 3

    def test_total_reflects_pre_filter_count(self):
        fm = FilterMatcher.__new__(FilterMatcher)
        fm._available = True
        fm._filter_fn = MagicMock(return_value=True)  # Exclude everything
        rows = [["a"], ["b"]]
        filtered, total = fm.filter_rows_with_count(rows, {"name": "is x"}, ["name"])
        assert len(filtered) == 0
        assert total == 2

    def test_empty_input(self):
        fm = FilterMatcher.__new__(FilterMatcher)
        fm._available = False
        filtered, total = fm.filter_rows_with_count([], {}, [])
        assert filtered == []
        assert total == 0


# ===========================================================================
# DatabaseSchemaProvider tests
# ===========================================================================


class TestDatabaseSchemaProviderFromCsv:
    def test_reads_header_row(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "name,email,status\nAlice,alice@example.com,active\n", encoding="utf-8"
        )
        result = DatabaseSchemaProvider.from_csv(str(csv_file))
        assert result == ["name", "email", "status"]

    def test_strips_whitespace_from_headers(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(" name , email , status \n", encoding="utf-8")
        result = DatabaseSchemaProvider.from_csv(str(csv_file))
        assert result == ["name", "email", "status"]

    def test_empty_file_returns_empty(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")
        result = DatabaseSchemaProvider.from_csv(str(csv_file))
        assert result == []

    def test_missing_file_returns_empty(self, tmp_path):
        result = DatabaseSchemaProvider.from_csv(str(tmp_path / "missing.csv"))
        assert result == []

    def test_filters_empty_columns(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,,status\n", encoding="utf-8")
        result = DatabaseSchemaProvider.from_csv(str(csv_file))
        assert result == ["name", "status"]

    def test_header_only_file(self, tmp_path):
        csv_file = tmp_path / "headers.csv"
        csv_file.write_text("a,b,c\n", encoding="utf-8")
        assert DatabaseSchemaProvider.from_csv(str(csv_file)) == ["a", "b", "c"]


class TestDatabaseSchemaProviderFromGoogleSheets:
    def test_first_sheet_no_name(self):
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = ["name", "email", "status"]
        mock_service = MagicMock()
        mock_service.worksheets.return_value = [mock_ws]
        result = DatabaseSchemaProvider.from_google_sheets(mock_service, "sheet_id")
        assert result == ["name", "email", "status"]

    def test_named_sheet_found(self):
        mock_ws1 = MagicMock()
        mock_ws1.title = "Sheet1"
        mock_ws2 = MagicMock()
        mock_ws2.title = "Members"
        mock_ws2.row_values.return_value = ["id", "name"]
        mock_service = MagicMock()
        mock_service.worksheets.return_value = [mock_ws1, mock_ws2]
        result = DatabaseSchemaProvider.from_google_sheets(
            mock_service, "sheet_id", sheet_name="Members"
        )
        assert result == ["id", "name"]

    def test_named_sheet_not_found(self):
        mock_ws = MagicMock()
        mock_ws.title = "Sheet1"
        mock_service = MagicMock()
        mock_service.worksheets.return_value = [mock_ws]
        result = DatabaseSchemaProvider.from_google_sheets(
            mock_service, "sheet_id", sheet_name="Missing"
        )
        assert result == []

    def test_empty_worksheets_list(self):
        mock_service = MagicMock()
        mock_service.worksheets.return_value = []
        result = DatabaseSchemaProvider.from_google_sheets(mock_service, "sheet_id")
        assert result == []

    def test_service_without_worksheets_attr(self):
        mock_service = MagicMock(spec=[])
        result = DatabaseSchemaProvider.from_google_sheets(mock_service, "sheet_id")
        assert result == []

    def test_exception_returns_empty(self):
        mock_service = MagicMock()
        mock_service.worksheets.side_effect = Exception("API error")
        result = DatabaseSchemaProvider.from_google_sheets(mock_service, "sheet_id")
        assert result == []

    def test_strips_whitespace_and_filters_empty(self):
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = [" name ", " email ", ""]
        mock_service = MagicMock()
        mock_service.worksheets.return_value = [mock_ws]
        result = DatabaseSchemaProvider.from_google_sheets(mock_service, "sheet_id")
        assert result == ["name", "email"]


class TestDatabaseSchemaProviderDetectAndExtract:
    def test_empty_path_returns_empty(self):
        assert DatabaseSchemaProvider.detect_and_extract("") == []

    def test_csv_path(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b,c\n", encoding="utf-8")
        result = DatabaseSchemaProvider.detect_and_extract(str(csv_file))
        assert result == ["a", "b", "c"]

    def test_nonexistent_csv_returns_empty(self, tmp_path):
        result = DatabaseSchemaProvider.detect_and_extract(
            str(tmp_path / "missing.csv")
        )
        assert result == []

    def test_google_sheets_url(self):
        mock_service = MagicMock()
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = ["field1", "field2"]
        mock_service.worksheets.return_value = [mock_ws]
        result = DatabaseSchemaProvider.detect_and_extract(
            "https://docs.google.com/spreadsheets/d/abc123",
            gsheet_service=mock_service,
        )
        assert result == ["field1", "field2"]

    def test_google_sheets_long_id(self):
        mock_service = MagicMock()
        mock_ws = MagicMock()
        mock_ws.row_values.return_value = ["a", "b"]
        mock_service.worksheets.return_value = [mock_ws]
        # String longer than 20 chars treated as Google Sheets ID
        result = DatabaseSchemaProvider.detect_and_extract(
            "aabbccdd11223344556677889900",
            gsheet_service=mock_service,
        )
        assert result == ["a", "b"]

    def test_gsheet_without_service_returns_empty(self):
        result = DatabaseSchemaProvider.detect_and_extract(
            "https://docs.google.com/spreadsheets/d/abc",
            gsheet_service=None,
        )
        assert result == []

    def test_unknown_file_type_returns_empty(self, tmp_path):
        xlsx_path = tmp_path / "data.xlsx"
        result = DatabaseSchemaProvider.detect_and_extract(str(xlsx_path))
        assert result == []
