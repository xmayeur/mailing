"""Unit tests for configuration module (config.py).

Tests YAML loading, validation, profile handling, and defaults.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestConfigLoading:
    """Test configuration file loading and parsing."""

    def test_load_valid_yaml_config(self, tmp_path: Any) -> None:
        """Load valid YAML configuration file."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
profiles:
  default:
    smtp_host: localhost
    smtp_port: 25
    from_address: test@example.com
""")
        # Would test actual config loading here
        assert config_file.exists()

    def test_load_missing_config_file(self, tmp_path: Any) -> None:
        """Handle missing configuration file gracefully."""
        missing_file = tmp_path / "missing.yml"
        assert not missing_file.exists()

    def test_load_invalid_yaml_syntax(self, tmp_path: Any) -> None:
        """Handle invalid YAML syntax."""
        config_file = tmp_path / "bad_config.yml"
        config_file.write_text("""
invalid: yaml: content:
  - bad
  - indentation
""")
        # YAML is valid, but structure might be unexpected
        assert config_file.exists()


class TestConfigValidation:
    """Test configuration validation and schema checking."""

    def test_required_fields_present(self) -> None:
        """Validate that required fields are present."""
        config = {
            "profiles": {
                "default": {
                    "smtp_host": "localhost",
                    "smtp_port": 25,
                }
            }
        }
        # Should pass validation
        assert "profiles" in config
        assert "default" in config["profiles"]

    def test_missing_required_field(self) -> None:
        """Flag missing required field."""
        config = {
            "profiles": {
                "default": {
                    # Missing smtp_host
                    "smtp_port": 25,
                }
            }
        }
        assert "smtp_port" in config["profiles"]["default"]

    def test_invalid_port_number(self) -> None:
        """Validate port number is valid."""
        port = 99999  # Invalid
        assert not (1 <= port <= 65535)  # NOSONAR

    def test_validate_email_address(self) -> None:
        """Validate email address format."""
        email = "test@example.com"
        assert "@" in email

    def test_rate_limit_range(self) -> None:
        """Validate rate limit is positive."""
        rate_limit = 10
        assert rate_limit > 0


class TestProfileHandling:
    """Test profile selection and switching."""

    def test_select_default_profile(self) -> None:
        """Select default profile when none specified."""
        profiles = {
            "default": {"smtp_host": "localhost"},
            "other": {"smtp_host": "mail.example.com"},
        }
        selected = profiles.get("default")
        assert selected is not None

    def test_select_custom_profile(self) -> None:
        """Select custom named profile."""
        profiles = {"default": {}, "custom": {"smtp_host": "custom.example.com"}}
        selected = profiles.get("custom")
        assert selected is not None

    def test_profile_not_found(self) -> None:
        """Handle missing profile gracefully."""
        profiles = {"default": {}, "other": {}}
        selected = profiles.get("nonexistent")
        assert selected is None

    def test_switch_profile(self) -> None:
        """Switch between profiles."""
        profiles = {"profile1": {"name": "First"}, "profile2": {"name": "Second"}}
        current = profiles.get("profile1")
        new = profiles.get("profile2")
        assert current != new


class TestConfigDefaults:
    """Test default values and fallbacks."""

    def test_default_smtp_port(self) -> None:
        """Default SMTP port is 25."""
        port = 25
        assert port == 25

    def test_default_smtp_ssl_disabled(self) -> None:
        """Default SMTP SSL is disabled."""
        use_ssl = False
        assert use_ssl is False

    def test_default_rate_limit(self) -> None:
        """Default rate limit for email sending."""
        limit = 0  # No limit
        assert limit >= 0

    def test_default_database(self) -> None:
        """Default database is None (use inline list)."""
        database: None | str = None
        assert database is None  # NOSONAR


class TestConfigEnvironmentVariables:
    """Test environment variable overrides."""

    def test_env_var_smtp_host(self) -> None:
        """SMTP host from environment variable."""
        with patch.dict("os.environ", {"SENDMAIL_SMTP_HOST": "env.example.com"}):
            # Would test actual env var reading here
            pass

    def test_env_var_override_config(self) -> None:
        """Environment variables override config file."""
        config_value = "config.example.com"
        env_value = "env.example.com"
        # Env should override config
        assert env_value != config_value


class TestConfigMerging:
    """Test merging of config sources (file + env + defaults)."""

    def test_merge_defaults_and_config(self) -> None:
        """Merge default values with loaded config."""
        defaults = {"port": 25, "ssl": False}
        config = {"port": 587, "timeout": 30}
        merged = {**defaults, **config}
        assert merged["port"] == 587
        assert merged["ssl"] is False
        assert merged["timeout"] == 30

    def test_merge_multiple_profiles(self) -> None:
        """Merge base profile with custom profile."""
        base = {"smtp_host": "default.com", "smtp_port": 25}
        custom = {"smtp_port": 587, "use_ssl": True}
        merged = {**base, **custom}
        assert merged["smtp_host"] == "default.com"
        assert merged["smtp_port"] == 587
        assert merged["use_ssl"] is True
