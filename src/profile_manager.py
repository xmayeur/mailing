"""Profile management and vault integration for email profiles."""
import logging
from typing import Any, cast

from getSecrets import get_secret

logger = logging.getLogger(__name__)


class ProfileLoadError(Exception):
    """Raised when profile loading fails."""
    pass


class Profile:
    """Email profile with SMTP configuration and optional filters."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """Initialize profile from configuration dictionary.

        Args:
            name: Profile name (e.g., 'artscroises', 'default')
            config: Profile configuration from config.yml

        Raises:
            ValueError: If required fields missing
        """
        self.name = name
        self.config = config
        self._smtp_cache: dict[str, Any] | None = None
        self._smtp_cached = False

    @property
    def vault_key(self) -> str | None:
        """Get vault key for this profile's SMTP credentials."""
        return self.config.get("vault_key") or self.config.get("MAILCONFIG") or self.config.get("mailconfig")

    @property
    def filters(self) -> dict[str, Any] | None:
        """Get saved filters for this profile."""
        return self.config.get("filters")

    def set_filters(self, filters: dict[str, Any]) -> None:
        """Set/update filters for this profile."""
        self.config["filters"] = filters

    def load_smtp_from_vault(self) -> dict[str, Any]:
        """Load SMTP parameters from vault.

        Returns:
            Dictionary with SMTP config (host, port, username, password, security)

        Raises:
            ProfileLoadError: If vault key missing/invalid or fetch fails
        """
        vault_key = self.vault_key
        if not vault_key:
            raise ProfileLoadError(
                f"No vault_key configured for profile '{self.name}'. "
                f"Add 'vault_key: mailconfig: <key>' to profile config."
            )

        logger.debug(f"Fetching SMTP params for profile '{self.name}' from vault key '{vault_key}'")

        try:
            # Parse vault key format: "mailconfig: artscroisesmailing" → "artscroisesmailing"
            secret_key = vault_key
            if vault_key.startswith("mailconfig:"):
                secret_key = vault_key.split(":", 1)[1].strip()

            smtp_params = cast(dict[str, Any], get_secret(secret_key))
            if not smtp_params:
                raise ProfileLoadError(
                    f"Vault key not found or empty: {vault_key}"
                )

            logger.debug(f"Successfully loaded SMTP params for profile '{self.name}'")

            # Validate required SMTP fields (vault returns smtp_host, smtp_port, etc.)
            required_fields = ["smtp_host", "smtp_port", "username", "password"]
            missing = [f for f in required_fields if f not in smtp_params]
            if missing:
                logger.debug(
                    f"Vault key '{vault_key}' incomplete (missing: {', '.join(missing)}). "
                    f"Using config file settings instead."
                )
                return {}

            # Cache the result
            self._smtp_cache = smtp_params
            self._smtp_cached = True
            return smtp_params

        except Exception as e:
            if isinstance(e, ProfileLoadError):
                raise
            raise ProfileLoadError(
                f"Failed to fetch SMTP parameters from vault for profile '{self.name}': {str(e)}"
            ) from e

    def get_smtp_params(self) -> dict[str, Any]:
        """Get SMTP parameters (from cache if available, else load from vault).

        Returns:
            Dictionary with SMTP config

        Raises:
            ProfileLoadError: If vault access fails
        """
        if not self._smtp_cached:
            return self.load_smtp_from_vault()
        return self._smtp_cache or {}

    def invalidate_smtp_cache(self) -> None:
        """Invalidate cached SMTP parameters (called on profile switch)."""
        self._smtp_cache = None
        self._smtp_cached = False
        logger.debug(f"SMTP cache invalidated for profile '{self.name}'")

    def __repr__(self) -> str:
        return f"Profile(name='{self.name}', vault_key='{self.vault_key}')"
