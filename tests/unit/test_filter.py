import os
import sys
from unittest.mock import MagicMock

# Save real yaml module to restore after tests (prevent pollution of other tests)
import yaml as _real_yaml

# Mock external dependencies before importing sendMail
mock_get_secret = MagicMock(return_value={"key": "value"})
sys.modules["gspread"] = MagicMock()
sys.modules["yaml"] = MagicMock()
sys.modules["certifi"] = MagicMock()
sys.modules["getSecrets"] = MagicMock()
sys.modules["getSecrets"].get_secret = mock_get_secret  # type: ignore[attr-defined]
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
sys.modules["googleapiclient.errors"] = MagicMock()
sys.modules["googleapiclient.http"] = MagicMock()
sys.modules["oauth2client"] = MagicMock()
sys.modules["oauth2client.service_account"] = MagicMock()
sys.modules["PIL"] = MagicMock()

# Add source directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "src")))

import sendMail  # noqa: E402

# Restore real yaml module immediately after importing sendMail to prevent pollution
sys.modules["yaml"] = _real_yaml


def test_filter():
    filter_rules = {}
    assert not sendMail.filter(filter_rules, {}, {})


def test_filter_with_data():
    filter_rules = {
        "email": "is not empty",
        "bounced": "is not bounced",
        "cotisation": "greater than 0",
        "first_name": "one of Jean, Xavier",
    }

    indices = {
        "email": 0,
        "bounced": 1,
        "cotisation": 2,
        "first_name": 3,
        "last_name": 4,
        "selected": 5,
    }

    row = ["xavier@mayeur.be", "", 100, "Xavier", "Mayeur", "True"]
    assert not sendMail.filter(filter_rules, row, indices)
    filter_rules["email"] = "is not xavier@mayeur.be"
    assert sendMail.filter(filter_rules, row, indices)
    filter_rules["email"] = "is not empty"
    filter_rules["first_name"] = "one of Jean, Arthur"
    assert sendMail.filter(filter_rules, row, indices)
    filter_rules["first_name"] = "in Jean, Xavier"
    filter_rules["cotisation"] = "gt 200"
    assert sendMail.filter(filter_rules, row, indices)
    filter_rules["cotisation"] = "gt xxx"
    assert sendMail.filter(filter_rules, row, indices)
    filter_rules = {"selected": "is True"}
    assert not sendMail.filter(filter_rules, row, indices)
    row[2] = "15.0"
    filter_rules = {"cotisation": "eq 15.0"}
    assert not sendMail.filter(filter_rules, row, indices)
    filter_rules = {"cotisation": "gt 14.0"}
    assert not sendMail.filter(filter_rules, row, indices)
    filter_rules = {"cotisation": "le 16.0"}
    assert not sendMail.filter(filter_rules, row, indices)
    filter_rules = {"cotisation": "le 15.0"}
    assert not sendMail.filter(filter_rules, row, indices)
    filter_rules = {"cotisation": "ge 15.0"}
    assert not sendMail.filter(filter_rules, row, indices)
    filter_rules = {"cotisation": "lt 15.0"}
    assert sendMail.filter(filter_rules, row, indices)
    filter_rules = {"cotisation": "ne 15.0"}
    assert sendMail.filter(filter_rules, row, indices)
    row[5] = ""
    filter_rules = {"selected": "is empty"}
    assert not sendMail.filter(filter_rules, row, indices)
    filter_rules = {"selected": "has None"}
    assert sendMail.filter(filter_rules, row, indices)
    filter_rules = {"SSelected": "is not empty"}
    assert sendMail.filter(filter_rules, row, indices)
    row[5] = "True"
    filter_rules = {"selected": "not in x, y, X, Yes"}
    assert not sendMail.filter(filter_rules, row, indices)


def test_filter_contains():
    """Test 'contains' operation."""
    indices = {"email": 0, "name": 1, "domain": 2}
    row = ["john@example.com", "John Smith", "example.com"]

    # Matching contains
    assert not sendMail.filter({"email": "contains @"}, row, indices)
    assert not sendMail.filter({"name": "contains Smith"}, row, indices)

    # Non-matching contains
    assert sendMail.filter({"email": "contains @gmail"}, row, indices)
    assert sendMail.filter({"name": "contains Doe"}, row, indices)

    # Case sensitive
    assert sendMail.filter({"name": "contains john"}, row, indices)


def test_filter_does_not_contain():
    """Test 'does not contain' operation."""
    indices = {"email": 0, "name": 1}
    row = ["john@example.com", "John Smith"]

    # Matching does not contain
    assert not sendMail.filter({"email": "does not contain @gmail"}, row, indices)
    assert not sendMail.filter({"name": "does not contain Doe"}, row, indices)

    # Non-matching does not contain
    assert sendMail.filter({"email": "does not contain @"}, row, indices)
    assert sendMail.filter({"name": "does not contain Smith"}, row, indices)


def test_filter_starts_with():
    """Test 'starts with' operation."""
    indices = {"email": 0, "name": 1, "domain": 2}
    row = ["john@example.com", "John Smith", "example.com"]

    # Matching starts with
    assert not sendMail.filter({"email": "starts with john"}, row, indices)
    assert not sendMail.filter({"name": "starts with John"}, row, indices)
    assert not sendMail.filter({"domain": "starts with example"}, row, indices)

    # Non-matching starts with
    assert sendMail.filter({"email": "starts with jane"}, row, indices)
    assert sendMail.filter({"name": "starts with jane"}, row, indices)

    # Case sensitive
    assert sendMail.filter({"name": "starts with john"}, row, indices)


def test_filter_ends_with():
    """Test 'ends with' operation."""
    indices = {"email": 0, "name": 1, "domain": 2}
    row = ["john@example.com", "John Smith", "example.com"]

    # Matching ends with
    assert not sendMail.filter({"email": "ends with .com"}, row, indices)
    assert not sendMail.filter({"name": "ends with Smith"}, row, indices)
    assert not sendMail.filter({"domain": "ends with .com"}, row, indices)

    # Non-matching ends with
    assert sendMail.filter({"email": "ends with .org"}, row, indices)
    assert sendMail.filter({"name": "ends with Doe"}, row, indices)

    # Case sensitive
    assert sendMail.filter({"name": "ends with smith"}, row, indices)


def test_filter_matches_regex():
    """Test 'matches' operation with regex."""
    indices = {"email": 0, "name": 1, "phone": 2}
    row = ["john@example.com", "John Smith", "123-456-7890"]

    # Matching regex patterns
    assert not sendMail.filter({"email": "matches .*@example\\.com"}, row, indices)
    assert not sendMail.filter({"name": "matches John.*"}, row, indices)
    assert not sendMail.filter({"phone": "matches \\d{3}-\\d{3}-\\d{4}"}, row, indices)

    # Non-matching regex patterns
    assert sendMail.filter({"email": "matches .*@gmail\\.com"}, row, indices)
    assert sendMail.filter({"name": "matches Jane.*"}, row, indices)

    # Multiple matches
    assert not sendMail.filter({"email": "matches john|jane"}, row, indices)

    # Case sensitive regex
    assert sendMail.filter({"email": "matches JOHN.*"}, row, indices)


def test_filter_matches_regex_invalid():
    """Test 'matches' operation with invalid regex patterns."""
    indices = {"text": 0}
    row = ["test string"]

    # Invalid regex should return False (exclude row)
    assert sendMail.filter({"text": "matches [invalid("}, row, indices)

    # Invalid regex in 'does not match' should return True (include row)
    assert not sendMail.filter({"text": "does not match [invalid("}, row, indices)


def test_filter_does_not_match_regex():
    """Test 'does not match' operation with regex."""
    indices = {"email": 0, "name": 1}
    row = ["john@example.com", "John Smith"]

    # Matching does not match
    assert not sendMail.filter({"email": "does not match .*@gmail\\.com"}, row, indices)
    assert not sendMail.filter({"name": "does not match Jane.*"}, row, indices)

    # Non-matching does not match
    assert sendMail.filter({"email": "does not match .*@example\\.com"}, row, indices)
    assert sendMail.filter({"name": "does not match John.*"}, row, indices)
