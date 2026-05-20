"""Pytest configuration and shared fixtures for tests directory."""

import sys
from pathlib import Path
import pytest

# Add project root and src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_dir) not in sys.path:
    sys.path.insert(1, str(src_dir))


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
