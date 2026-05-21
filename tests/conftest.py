"""Pytest configuration and shared fixtures for tests directory."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root and src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_dir) not in sys.path:
    sys.path.insert(1, str(src_dir))

# Save real yaml module to restore after mocking (for sendMail import)
import yaml as _real_yaml

# Setup global mocks for external dependencies BEFORE any test imports
# This must happen at module load time, before test files import sendMail
mock_get_secret = MagicMock(return_value={"key": "value"})

sys.modules["gspread"] = MagicMock()
sys.modules["yaml"] = MagicMock()
sys.modules["certifi"] = MagicMock()
sys.modules["getSecrets"] = MagicMock()
sys.modules["getSecrets"].get_secret = mock_get_secret
sys.modules["google"] = MagicMock()
sys.modules["google.auth"] = MagicMock()
sys.modules["google.auth.transport"] = MagicMock()
sys.modules["google.auth.transport.requests"] = MagicMock()
sys.modules["google.oauth2"] = MagicMock()
sys.modules["google.oauth2.credentials"] = MagicMock()
sys.modules["google_auth_oauthlib"] = MagicMock()
sys.modules["google_auth_oauthlib.flow"] = MagicMock()
sys.modules["googleapiclient"] = MagicMock()
sys.modules["googleapiclient.discovery"] = MagicMock()
sys.modules["googleapiclient.http"] = MagicMock()

# Mock googleapiclient.errors with HttpError class
class MockHttpError(Exception):
    def __init__(self, resp, content, uri=None):
        self.resp = resp
        self.content = content
        self.uri = uri

    def __str__(self):
        return f"HttpError {self.resp.status if hasattr(self.resp, 'status') else 'unknown'} when requesting {self.uri} returned {self.content}"


mock_errors = MagicMock()
mock_errors.HttpError = MockHttpError
sys.modules["googleapiclient.errors"] = mock_errors

# Restore real yaml module immediately to prevent pollution of other test modules
# (sendMail should be imported after mocks are set up but we need real yaml for other tests)
sys.modules["yaml"] = _real_yaml


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "slow: slow tests (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "bdd: BDD behavior tests")


@pytest.fixture
def tmp_yaml_file(tmp_path):
    """Create a temporary YAML config file for testing."""
    yaml_file = tmp_path / "config.yml"
    yaml_file.write_text("default:\n  sender: test@example.com\ntest:\n  sender: test2@example.com\n", encoding="utf-8")
    return yaml_file


@pytest.fixture
def tmp_csv_file(tmp_path):
    """Create a temporary CSV subscriber file for testing."""
    csv_file = tmp_path / "subscribers.csv"
    csv_file.write_text("name,email,status\nAlice,alice@example.com,active\nBob,bob@example.com,inactive\n", encoding="utf-8")
    return csv_file


@pytest.fixture
def tmp_html_file(tmp_path):
    """Create a temporary HTML file for testing."""
    html_file = tmp_path / "newsletter.html"
    html_file.write_text("<!DOCTYPE html>\n<html><head><title>Test</title></head><body><h1>Test</h1></body></html>", encoding="utf-8")
    return html_file


@pytest.fixture
def sample_email_config():
    """Provide sample email configuration for testing."""
    return {"sender": "test@example.com", "smtp_server": "localhost", "smtp_port": 25}


@pytest.fixture
def mock_vault_smtp_response():
    """Provide mock vault response for SMTP credentials."""
    return {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "username": "test_user",
        "password": "test_password",
        "sender": "test@example.com",
        "sendername": "Test Sender"
    }


@pytest.fixture
def vault_fixture(monkeypatch, mock_vault_smtp_response):
    """Mock get-hc-secrets for vault integration testing."""
    from unittest.mock import Mock, patch

    mock_get_secrets = Mock(return_value=mock_vault_smtp_response)

    # Monkeypatch the vault access function (location depends on implementation)
    # This will be adjusted when Profile.load_smtp_from_vault() is implemented
    return {
        "mock_get_secrets": mock_get_secrets,
        "response": mock_vault_smtp_response
    }
