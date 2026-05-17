"""Filter validation for editor UI.

Validates YAML filter syntax and subscriber database field names.
Detects parsing errors and missing fields to provide user feedback
when editing filters in the newsletter editor.

Classes:
    FilterValidator: Validates filter syntax and field references
"""

import logging
from typing import Any

import yaml

log = logging.getLogger("filter_validator")


class FilterValidator:
    """Validates YAML filter syntax and field names."""

    def __init__(self) -> None:
        pass

    def parse_yaml_filter(self, text: str) -> dict[str, str] | None:
        """Parse YAML filter text into dict.

        Returns dict on success, None on parse error.
        """
        if not text or not text.strip():
            return {}
        try:
            result = yaml.safe_load(text)
            if result is None:
                return {}
            if not isinstance(result, dict):
                return None
            return result
        except yaml.YAMLError as e:
            log.debug("YAML parse error: %s", e)
            return None

    def validate_field_names(
        self, filter_dict: dict[str, str], database_schema: list[str]
    ) -> list[str]:
        """Validate filter field names exist in database schema.

        Args:
            filter_dict: Filter with field names as keys
            database_schema: List of available field names from database

        Returns:
            List of missing field names (empty if all valid)
        """
        if not filter_dict:
            return []

        schema_set = set(database_schema)
        missing = []
        for field_name in filter_dict.keys():
            if field_name not in schema_set:
                missing.append(field_name)
        return missing

    def get_validation_status(
        self, filter_text: str, database_schema: list[str]
    ) -> dict[str, Any]:
        """Get complete validation status of filter.

        Returns dict with keys:
            - is_valid: bool
            - syntax_errors: list[str]
            - missing_fields: list[str]
        """
        status = {"is_valid": True, "syntax_errors": [], "missing_fields": []}

        if not filter_text or not filter_text.strip():
            return status

        # T044: Parse and check for YAML syntax errors
        filter_dict = self.parse_yaml_filter(filter_text)
        if filter_dict is None:
            status["is_valid"] = False
            status["syntax_errors"] = ["Invalid YAML syntax (check colons, quotes, indentation)"]
            return status

        missing = self.validate_field_names(filter_dict, database_schema)
        if missing:
            status["is_valid"] = False
            status["missing_fields"] = missing

        return status
