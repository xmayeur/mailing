import os
import sys
from unittest.mock import MagicMock

import sendMail

# Mock external dependencies before importing sendMail
mock_get_secret = MagicMock(return_value={"key": "value"})
sys.modules['gspread'] = MagicMock()
sys.modules['yaml'] = MagicMock()
# sys.modules['bs4'] = MagicMock()
sys.modules['certifi'] = MagicMock()
sys.modules['getSecrets'] = MagicMock()
sys.modules['getSecrets'].get_secret = mock_get_secret
sys.modules['google'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.transport'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['google_auth_oauthlib'] = MagicMock()
sys.modules['google_auth_oauthlib.flow'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.errors'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()
sys.modules['oauth2client'] = MagicMock()
sys.modules['oauth2client.service_account'] = MagicMock()
sys.modules['PIL'] = MagicMock()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_filter():
    filter = {}
    assert sendMail.filter(filter, {}, {}) == False


def test_filter_with_data():
    filter = {
        "email": "is not empty",
        "bounced": "is not bounced",
        "cotisation": "greater than 0",
        "first_name": "one of Jean, Xavier"
    }

    indices = {
        'email': 0,
        'bounced': 1,
        'cotisation': 2,
        'first_name': 3,
        'last_name': 4,
        'selected': 5
    }

    row = ['xavier@mayeur.be', '', 100, 'Xavier', 'Mayeur', 'True']
    assert sendMail.filter(filter, row, indices) == False
    filter['email'] = "is not xavier@mayeur.be"
    assert sendMail.filter(filter, row, indices) == True
    filter['email'] = "is not empty"
    filter['first_name'] = "one of Jean, Arthur"
    assert sendMail.filter(filter, row, indices) == True
    filter['first_name'] = "in Jean, Xavier"
    filter['cotisation'] = "gt 200"
    assert sendMail.filter(filter, row, indices) == True
    filter['cotisation'] = "gt xxx"
    assert sendMail.filter(filter, row, indices) == True
    filter = {"selected": "is True"}
    assert sendMail.filter(filter, row, indices) == False
    row[2] = "15.0"
    filter = {"cotisation": "eq 15.0"}
    assert sendMail.filter(filter, row, indices) == False
    filter = {"cotisation": "gt 14.0"}
    assert sendMail.filter(filter, row, indices) == False
    filter = {"cotisation": "le 16.0"}
    assert sendMail.filter(filter, row, indices) == False
    filter = {"cotisation": "le 15.0"}
    assert sendMail.filter(filter, row, indices) == False
    filter = {"cotisation": "ge 15.0"}
    assert sendMail.filter(filter, row, indices) == False
    filter = {"cotisation": "lt 15.0"}
    assert sendMail.filter(filter, row, indices) == True
    filter = {"cotisation": "ne 15.0"}
    assert sendMail.filter(filter, row, indices) == True
    row[5] = ""
    filter = {"selected": "is empty"}
    assert sendMail.filter(filter, row, indices) == False
    filter = {"selected": "has None"}
    assert sendMail.filter(filter, row, indices) == True
    filter = {"SSelected": "is not empty"}
    assert sendMail.filter(filter, row, indices) == True
    row[5] = "True"
    filter = {"selected": "not in x, y, X, Yes"}
    assert sendMail.filter(filter, row, indices) == False
