"""Editor profile styling integration."""
import logging
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


class EditorProfileStyler:
    """Manage profile-specific styling in editor."""

    def __init__(self, profile_config: dict[str, Any]) -> None:
        """Initialize with profile configuration.

        Args:
            profile_config: Profile configuration dictionary
        """
        self.profile_config = profile_config
        self.current_profile = profile_config.get("name", "default")

    def get_profile_template(self) -> str | None:
        """Get profile's HTML template path.

        Returns:
            Path to template file or None if not configured

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_file = self.profile_config.get("template_file")
        if not template_file:
            logger.debug(f"No template file configured for profile '{self.current_profile}'")
            return None

        template_path = Path(template_file)
        if not template_path.exists():
            logger.warning(f"Template file not found: {template_file}")
            raise FileNotFoundError(f"Template file not found: {template_file}")

        logger.debug(f"Found template file for profile '{self.current_profile}': {template_file}")
        return cast(str, template_file)

    def apply_profile_styling(self, html_content: str) -> str:
        """Apply profile styling to HTML content.

        Preserves existing inline styles while applying profile defaults.

        Args:
            html_content: Original HTML content

        Returns:
            HTML with profile styling applied

        Note:
            Current implementation:
            - Returns content unchanged (styling applied via Quill theme)
            - Future: Can inject profile CSS into <head>
        """
        logger.debug(f"Applying profile styling for '{self.current_profile}'")

        # Current approach: Quill theme applied client-side via editor.html
        # Future enhancement: Inject profile CSS here if needed
        return html_content

    def get_profile_theme(self) -> str:
        """Get CSS theme class for profile.

        Returns:
            CSS class name (e.g., 'profile-artscroises')
        """
        profile_name = self.current_profile.lower().replace(" ", "-")
        return f"profile-{profile_name}"

    @staticmethod
    def create_profile_css(profile_name: str, css_rules: dict[str, str] | None = None) -> str:
        """Generate CSS for profile styling.

        Args:
            profile_name: Profile name
            css_rules: Optional dict of CSS properties

        Returns:
            CSS string
        """
        css_rules = css_rules or {}
        profile_class = f"profile-{profile_name.lower().replace(' ', '-')}"

        css_lines = [f".{profile_class} {{"]
        for prop, value in css_rules.items():
            css_lines.append(f"  {prop}: {value};")
        css_lines.append("}")

        return "\n".join(css_lines)

    def invalidate_cache(self) -> None:
        """Invalidate any cached styling (on profile switch)."""
        logger.debug(f"Styling cache invalidated for profile '{self.current_profile}'")
