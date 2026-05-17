import os
import sys
from unittest.mock import MagicMock

# Save real yaml module to restore after tests (prevent pollution of other tests)
import yaml as _real_yaml

# Mock external dependencies before importing sendMail
mock_get_secret = MagicMock(return_value={"key": "value"})
sys.modules["gspread"] = MagicMock()
sys.modules["yaml"] = MagicMock()
# sys.modules['bs4'] = MagicMock()
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
