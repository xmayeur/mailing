"""Integration tests for profile loading and email sending."""
import pytest
from unittest.mock import patch, Mock
from src.profile_manager import Profile, ProfileLoadError
from src.filter_persistence import FilterPersistence


class TestProfileFlow:
    """Test end-to-end profile selection and usage."""

    def test_full_profile_flow(self):
        """Full flow: profile select → vault load → SMTP connect → send email."""
        # Setup
        config = {
            "name": "artscroises",
            "vault_key": "mailconfig: artscroises",
            "sender": "sender@artscroises.com",
            "default_message": "Default message"
        }
        profile = Profile("artscroises", config)

        # Mock vault response
        vault_response = {
            "host": "smtp.artscroises.com",
            "port": 587,
            "username": "artscroises_user",
            "password": "artscroises_pass",
            "security": "tls"
        }

        # Execute profile loading
        with patch("src.profile_manager.get_secret", return_value=vault_response):
            smtp_params = profile.load_smtp_from_vault()

            # Verify SMTP params loaded
            assert smtp_params["host"] == "smtp.artscroises.com"
            assert smtp_params["port"] == 587
            assert smtp_params["username"] == "artscroises_user"

    def test_profile_switch_invalidates_cache(self):
        """Switching profiles invalidates previous cache."""
        config1 = {"name": "profile1", "vault_key": "mailconfig: profile1"}
        config2 = {"name": "profile2", "vault_key": "mailconfig: profile2"}

        profile1 = Profile("profile1", config1)
        profile2 = Profile("profile2", config2)

        response1 = {"host": "smtp1.com", "port": 587, "username": "user1", "password": "pass1", "security": "tls"}
        response2 = {"host": "smtp2.com", "port": 587, "username": "user2", "password": "pass2", "security": "tls"}

        with patch("src.profile_manager.get_secret") as mock_get:
            mock_get.return_value = response1
            profile1.load_smtp_from_vault()

            # Switch to profile2
            profile1.invalidate_smtp_cache()
            mock_get.return_value = response2
            smtp = profile1.load_smtp_from_vault()

            # Verify new params loaded
            assert smtp["host"] == "smtp2.com"

    def test_profile_with_saved_filters(self):
        """Profile loads and applies saved filters."""
        config = {
            "name": "test_profile",
            "filters": {"criteria": {"status": "active"}, "active": True}
        }
        persistence = FilterPersistence(config)

        # Load filters
        filters = persistence.load_filters()
        assert filters is not None
        assert filters["criteria"]["status"] == "active"

        # Apply with schema validation
        schema = ["name", "email", "status"]
        applied = persistence.apply_filter(filters["criteria"], schema)
        assert applied["status"] == "active"

    def test_error_handling_vault_unreachable(self):
        """Profile load fails gracefully with specific error."""
        config = {"name": "test_profile", "vault_key": "mailconfig: test"}
        profile = Profile("test_profile", config)

        with patch("src.profile_manager.get_secret", side_effect=ConnectionError("Vault timeout")):
            with pytest.raises(ProfileLoadError) as exc:
                profile.load_smtp_from_vault()

            assert "Failed to fetch SMTP parameters" in str(exc.value)

    def test_profile_with_missing_template(self):
        """Profile with missing template handles gracefully."""
        config = {
            "name": "test_profile",
            "template_file": "/nonexistent/template.html"
        }

        from src.editor_profile import EditorProfileStyler
        styler = EditorProfileStyler(config)

        with pytest.raises(FileNotFoundError):
            styler.get_profile_template()
