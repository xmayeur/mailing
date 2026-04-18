import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sendMail


class TestCheckMandatoryParam(unittest.TestCase):
    def setUp(self):
        # Base valid parameters for common fields
        self.common_valid = {
            "subject": "Test Subject",
            "sender": "sender@example.com",
            "sendername": "Sender Name",
            "message": "Test Message",
            "database": "data/test.csv",
        }

    def test_missing_common_param(self):
        """Test missing common parameters like subject, sender, etc."""
        for p in ["sender", "sendername"]:
            params = self.common_valid.copy()
            del params[p]
            param_obj = sendMail.Dict2Class(params)
            # Add some additional params to avoid other failures
            param_obj.token_file = "token.json"
            param_obj.scopes = ["scope"]
            param_obj.credentials_id = "creds"

            self.assertFalse(
                sendMail.check_mandatory_param(param_obj),
                f"Should fail when {p} is missing",
            )

    def test_missing_data_source(self):
        """Test missing database and sheet information."""
        params = self.common_valid.copy()
        del params["database"]
        param_obj = sendMail.Dict2Class(params)
        # Gmail mode params
        param_obj.token_file = "token.json"
        param_obj.scopes = ["scope"]
        param_obj.credentials_id = "creds"

        # Should fail as neither database nor (sa and sheetid) are provided
        self.assertFalse(sendMail.check_mandatory_param(param_obj))

        # Should pass with sa and sheetid
        param_obj.sa = "service_account.json"
        param_obj.sheetid = "sheet_id"
        self.assertTrue(sendMail.check_mandatory_param(param_obj))

    def test_smtp_mode_valid(self):
        """Test valid configuration for SMTP/IMAP mode."""
        params = self.common_valid.copy()
        params.update(
            {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "username": "user",
                "password": "password",
                "sent_folder": "Sent",
            }
        )
        param_obj = sendMail.Dict2Class(params)
        self.assertTrue(sendMail.check_mandatory_param(param_obj))

    def test_smtp_mode_missing_param(self):
        """Test missing parameters in SMTP/IMAP mode."""
        smtp_params = [
            "smtp_port",
            "imap_host",
            "imap_port",
            "username",
            "password",
            "sent_folder",
        ]
        for p in smtp_params:
            params = self.common_valid.copy()
            params.update(
                {
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "imap_host": "imap.example.com",
                    "imap_port": 993,
                    "username": "user",
                    "password": "password",
                    "sent_folder": "Sent",
                }
            )
            del params[p]
            param_obj = sendMail.Dict2Class(params)
            self.assertFalse(
                sendMail.check_mandatory_param(param_obj),
                f"Should fail when {p} is missing in SMTP mode",
            )

    def test_gmail_mode_valid(self):
        """Test valid configuration for Gmail mode."""
        params = self.common_valid.copy()
        params.update(
            {
                "token_file": "token.json",
                "scopes": ["https://www.googleapis.com/auth/gmail.send"],
                "credentials_id": "gmail_creds",
            }
        )
        param_obj = sendMail.Dict2Class(params)
        self.assertTrue(sendMail.check_mandatory_param(param_obj))

    def test_gmail_mode_missing_param(self):
        """Test missing parameters in Gmail mode."""
        gmail_params = ["token_file", "scopes", "credentials_id"]
        for p in gmail_params:
            params = self.common_valid.copy()
            params.update(
                {
                    "token_file": "token.json",
                    "scopes": ["scope"],
                    "credentials_id": "creds",
                }
            )
            del params[p]
            param_obj = sendMail.Dict2Class(params)
            self.assertFalse(
                sendMail.check_mandatory_param(param_obj),
                f"Should fail when {p} is missing in Gmail mode",
            )


if __name__ == "__main__":
    unittest.main()
