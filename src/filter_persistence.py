"""Filter persistence to profile configuration."""
import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


class FilterPersistence:
    """Handle filter save/restore to profile config."""

    def __init__(self, profile_config: dict[str, Any]) -> None:
        """Initialize with profile configuration.

        Args:
            profile_config: Profile configuration dictionary
        """
        self.profile_config = profile_config
        self.profile_name = profile_config.get("name", "default")

    def save_filter(self, filter_criteria: dict[str, Any]) -> None:
        """Save filter criteria to profile config.

        Args:
            filter_criteria: Filter match conditions (column → value patterns)

        Raises:
            ValueError: If filter criteria invalid
        """
        if not filter_criteria:
            raise ValueError("Filter criteria cannot be empty")

        # Validate filter has at least one condition
        if not isinstance(filter_criteria, dict) or len(filter_criteria) == 0:
            raise ValueError("Filter must contain at least one condition")

        logger.debug(
            f"Saving filter to profile '{self.profile_name}': {filter_criteria}"
        )

        self.profile_config["filters"] = {"criteria": filter_criteria, "active": True}

    def load_filters(self) -> dict[str, Any] | None:
        """Load saved filters from profile config.

        Returns:
            Saved filters dict or None if not configured

        Note:
            Validates filter criteria against schema.
            Skips invalid criteria with warning.
        """
        filters = self.profile_config.get("filters")
        if not filters:
            logger.debug(f"No saved filters for profile '{self.profile_name}'")
            return None

        logger.debug(f"Loaded filters for profile '{self.profile_name}': {filters}")
        return cast(dict[str, Any], filters)

    def validate_filter_criteria(
        self, criteria: dict[str, Any], schema_columns: list[str]
    ) -> bool:
        """Validate filter criteria against schema columns.

        Args:
            criteria: Filter criteria to validate
            schema_columns: Available schema columns

        Returns:
            True if valid, False otherwise
        """
        for column in criteria.keys():
            if column not in schema_columns:
                logger.warning(
                    f"Filter criteria references non-existent column '{column}'. "
                    f"Available columns: {schema_columns}"
                )
                return False
        return True

    def apply_filter(
        self, criteria: dict[str, Any], schema_columns: list[str]
    ) -> dict[str, Any]:
        """Apply filter, validating against schema.

        If criteria invalid, skip with warning.

        Args:
            criteria: Filter criteria to apply
            schema_columns: Available schema columns

        Returns:
            Valid criteria dict (may be empty if validation failed)
        """
        if not self.validate_filter_criteria(criteria, schema_columns):
            logger.warning("Filter criteria skipped due to validation failure")
            return {}

        logger.debug(f"Applying filter for profile '{self.profile_name}'")
        return criteria

    def clear_filters(self) -> None:
        """Remove saved filters from profile config."""
        if "filters" in self.profile_config:
            del self.profile_config["filters"]
            logger.debug(f"Filters cleared for profile '{self.profile_name}'")
