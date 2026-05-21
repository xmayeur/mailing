"""Tests for profile loading and SMTP vault integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import logging
from src.profile_manager import Profile, ProfileLoadError

logger = logging.getLogger(__name__)


class TestProfileVaultLoading:
    """Test vault integration for SMTP parameter loading."""

    def test_profile_loads_smtp_from_vault(self, vault_fixture):
        """Profile.load_smtp_from_vault() fetches SMTP params from vault."""
        config = {
            "vault_key": "mailconfig: test_profile",
            "sender": "test@example.com"
        }
        profile = Profile("test_profile", config)

        with patch("src.profile_manager.get_secret", return_value=vault_fixture["response"]):
            result = profile.load_smtp_from_vault()
            assert result["host"] == "smtp.example.com"
            assert result["port"] == 587
            assert result["username"] == "test_user"

    def test_smtp_cached_per_session(self, vault_fixture):
        """SMTP params cached per-session, invalidated on profile switch."""
        config = {"vault_key": "mailconfig: test_profile"}
        profile = Profile("test_profile", config)

        with patch("src.profile_manager.get_secret", return_value=vault_fixture["response"]) as mock_get:
            # First call - fetches from vault
            profile.load_smtp_from_vault()
            assert mock_get.call_count == 1

            # Second call - should use cache
            result = profile.get_smtp_params()
            assert mock_get.call_count == 1  # Not called again

            # After cache invalidate - fetches again
            profile.invalidate_smtp_cache()
            profile.load_smtp_from_vault()
            assert mock_get.call_count == 2

    def test_vault_unreachable_fails_hard(self):
        """Vault unreachable → specific error, no fallback to stale creds."""
        config = {"vault_key": "mailconfig: test_profile"}
        profile = Profile("test_profile", config)

        with patch("src.profile_manager.get_secret", side_effect=ConnectionError("Vault unreachable")):
            with pytest.raises(ProfileLoadError) as exc_info:
                profile.load_smtp_from_vault()
            assert "Failed to fetch SMTP parameters" in str(exc_info.value)
            assert "test_profile" in str(exc_info.value)

    def test_missing_vault_key_error_message(self):
        """Missing vault key → specific error with key name."""
        config = {}  # No vault_key
        profile = Profile("test_profile", config)

        with pytest.raises(ProfileLoadError) as exc_info:
            profile.load_smtp_from_vault()
        assert "No vault_key configured" in str(exc_info.value)
        assert "test_profile" in str(exc_info.value)

    def test_invalid_smtp_parameters_error(self):
        """Invalid SMTP params → specific validation error."""
        config = {"vault_key": "mailconfig: test_profile"}
        profile = Profile("test_profile", config)

        # Mock response missing required fields
        invalid_response = {"host": "smtp.example.com"}  # Missing port, username, password

        with patch("src.profile_manager.get_secret", return_value=invalid_response):
            with pytest.raises(ProfileLoadError) as exc_info:
                profile.load_smtp_from_vault()
            assert "missing required SMTP fields" in str(exc_info.value)


class TestSmtpErrorFix:
    """Test SMTP error resolution for artscroises profile."""

    def test_artscroises_profile_sends_successfully(self):
        """Artscroises profile sends email without SMTP error."""
        # TODO: Implement end-to-end SMTP test
        pass

    def test_smtp_connection_timeout_handling(self):
        """SMTP connection timeout → 5s timeout, specific error."""
        # TODO: Implement timeout handling test
        pass


class TestFilterPersistence:
    """Test filter save/restore to profile config."""

    def test_save_filter_to_profile(self):
        """Save filter criteria to profile config.yml."""
        # TODO: Implement after filter save added
        pass

    def test_load_filter_from_profile(self):
        """Load saved filters from profile on startup."""
        # TODO: Implement after filter load added
        pass

    def test_filter_persists_across_restart(self):
        """Filter saved to profile persists across app restart."""
        # TODO: Implement end-to-end persistence test
        pass

    def test_invalid_filter_criteria_on_save(self):
        """Invalid filter criteria rejected on save."""
        # TODO: Implement validation test
        pass


class TestLoggingLevels:
    """Test log level migrations (info → debug)."""

    def test_profile_loading_at_debug_level(self):
        """Profile loading (vault, SMTP) logged at debug level."""
        # TODO: Implement log capture test
        pass

    def test_no_debug_messages_at_info_level(self):
        """Production logs at INFO level have no debug messages."""
        # TODO: Implement log filter test
        pass
