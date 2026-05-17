"""Filter matching wrapper for editor filter preview.

Wraps sendMail.filter() to apply filters in the newsletter editor UI.
Provides live preview of how filters will affect subscriber lists.

Classes:
    FilterMatcher: Applies filters to rows for preview in editor UI
"""

import logging
from typing import Any

log = logging.getLogger("filter_matcher")


class FilterMatcher:
    """Wrapper around sendMail.filter() for filter matching."""

    def __init__(self) -> None:
        # Import here to avoid circular dependencies
        self._filter_fn: Any = None
        try:
            import sendMail as sm  # noqa: N813
            self._filter_fn = sm.filter
            self._available = True
        except (ImportError, AttributeError) as e:
            log.warning("Could not import sendMail.filter: %s", e)
            self._filter_fn = None
            self._available = False

    def is_available(self) -> bool:
        """Check if sendMail.filter is available."""
        return self._available

    def match_row(
        self, row_data: list[Any], filter_dict: dict[str, str], headers: list[str]
    ) -> bool:
        """Apply filter to a row of data.

        Args:
            row_data: List of values (one per column)
            filter_dict: Filter conditions {"field": "operator value"}
            headers: List of field/column names

        Returns:
            True if row matches filter (should be included), False if filtered out
        """
        if not self._available or not filter_dict:
            return True

        if not row_data or not headers:
            return True

        # Build indices dict: {"field": column_index}
        indices = {field: i for i, field in enumerate(headers)}

        try:
            if not self._filter_fn:
                return True
            # sendMail.filter returns True if row should be FILTERED OUT (excluded)
            # We want True = matches (included), so invert the result
            should_exclude = self._filter_fn(filter_dict, row_data, indices)
            return not should_exclude
        except Exception as e:
            log.warning("Filter matching error: %s", e)
            return True

    def filter_rows(
        self, rows_data: list[list[Any]], filter_dict: dict[str, str], headers: list[str]
    ) -> list[list[Any]]:
        """Apply filter to multiple rows.

        Args:
            rows_data: List of rows, each a list of values
            filter_dict: Filter conditions
            headers: Column/field names

        Returns:
            Filtered list of rows (matching filter)
        """
        if not filter_dict:
            return rows_data

        return [row for row in rows_data if self.match_row(row, filter_dict, headers)]

    def filter_rows_with_count(
        self, rows_data: list[list[Any]], filter_dict: dict[str, str], headers: list[str]
    ) -> tuple[list[list[Any]], int]:
        """Apply filter and return both results and original count.

        Args:
            rows_data: List of rows
            filter_dict: Filter conditions
            headers: Column/field names

        Returns:
            Tuple of (filtered_rows, original_count)
        """
        filtered = self.filter_rows(rows_data, filter_dict, headers)
        return filtered, len(rows_data)
