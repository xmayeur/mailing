import os
import sys
import tempfile
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

def test_make_html_images_inline():
    html_content = '<html><body><img src="http://example.com/img.png"><img src="data:image/png;base64,xxxx"></body></html>'
    # Use a real file instead of mock_open to avoid BeautifulSoup issues if it uses other file methods

    with tempfile.TemporaryDirectory() as tmp_dir:
        html_file = os.path.join(tmp_dir, "test.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        """Test make_html_images_inline with a real HTML file"""

        sendMail.make_html_images_inline(html_file, html_file)
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
            assert "data:image/png;base64," in html_content
            assert "src=\"data:image/png;base64," in html_content
