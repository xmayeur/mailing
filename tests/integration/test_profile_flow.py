"""Integration tests for profile loading and email sending."""
import pytest
from unittest.mock import patch, Mock
from src.profile_manager import Profile, ProfileLoadError
# Note: FilterPersistence is from US5 (P3) - not yet implemented
# from src.filter_persistence import FilterPersistence


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
            "smtp_host": "smtp.artscroises.com",
            "smtp_port": 587,
            "username": "artscroises_user",
            "password": "artscroises_pass",
            "sender": "sender@artscroises.com",
            "sendername": "Arts Croisés"
        }

        # Execute profile loading
        with patch("src.profile_manager.get_secret", return_value=vault_response):
            smtp_params = profile.load_smtp_from_vault()

            # Verify SMTP params loaded
            assert smtp_params["smtp_host"] == "smtp.artscroises.com"
            assert smtp_params["smtp_port"] == 587
            assert smtp_params["username"] == "artscroises_user"

    def test_profile_switch_invalidates_cache(self):
        """Switching profiles invalidates previous cache."""
        config1 = {"name": "profile1", "vault_key": "mailconfig: profile1"}
        config2 = {"name": "profile2", "vault_key": "mailconfig: profile2"}

        profile1 = Profile("profile1", config1)
        profile2 = Profile("profile2", config2)

        response1 = {"smtp_host": "smtp1.com", "smtp_port": 587, "username": "user1", "password": "pass1", "sender": "user1@test.com", "sendername": "User1"}
        response2 = {"smtp_host": "smtp2.com", "smtp_port": 587, "username": "user2", "password": "pass2", "sender": "user2@test.com", "sendername": "User2"}

        with patch("src.profile_manager.get_secret") as mock_get:
            mock_get.return_value = response1
            profile1.load_smtp_from_vault()

            # Switch to profile2
            profile1.invalidate_smtp_cache()
            mock_get.return_value = response2
            smtp = profile1.load_smtp_from_vault()

            # Verify new params loaded
            assert smtp["smtp_host"] == "smtp2.com"

    @pytest.mark.skip(reason="US5 (Filter Persistence) not yet implemented")
    def test_profile_with_saved_filters(self):
        """Profile loads and applies saved filters."""
        # TODO: Implement after FilterPersistence class created in US5
        pass

    def test_error_handling_vault_unreachable(self):
        """Profile load fails gracefully with specific error."""
        config = {"name": "test_profile", "vault_key": "mailconfig: test"}
        profile = Profile("test_profile", config)

        with patch("src.profile_manager.get_secret", side_effect=ConnectionError("Vault timeout")):
            with pytest.raises(ProfileLoadError) as exc:
                profile.load_smtp_from_vault()

            assert "Failed to fetch SMTP parameters" in str(exc.value)

    @pytest.mark.skip(reason="EditorProfileStyler class not yet implemented")
    def test_profile_with_missing_template(self):
        """Profile with missing template handles gracefully."""
        # TODO: Implement after EditorProfileStyler class created
        pass
