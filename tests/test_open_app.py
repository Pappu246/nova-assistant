import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools


def test_desktop_apps_in_aliases():
    assert "whatsapp" in tools.APP_ALIASES
    assert "telegram" in tools.APP_ALIASES
    assert "spotify" in tools.APP_ALIASES
    assert "discord" in tools.APP_ALIASES
    assert "notepad" in tools.APP_ALIASES
    assert "calculator" in tools.APP_ALIASES


def test_desktop_apps_in_protocols():
    assert tools.APP_PROTOCOLS.get("whatsapp") == "whatsapp:"
    assert tools.APP_PROTOCOLS.get("spotify") == "spotify:"
    assert tools.APP_PROTOCOLS.get("telegram") == "tg:"


def test_normalize_app_name():
    assert tools._normalize("whatsapp kholo") == "whatsapp"
    assert tools._normalize("open notepad please") == "notepad"
    assert tools._normalize("spotify open karo") == "spotify"


def test_open_app_desktop_priority_over_browser():
    with patch("platform.system", return_value="Windows"), \
         patch("tools._launch_windows", return_value=True) as mock_launch, \
         patch("webbrowser.open") as mock_web:
        res = tools.open_app({"app_name": "whatsapp"})
        assert "whatsapp" in res.lower()
        mock_launch.assert_called_once_with("whatsapp")
        mock_web.assert_not_called()


def test_open_app_spotify_desktop_priority():
    with patch("platform.system", return_value="Windows"), \
         patch("tools._launch_windows", return_value=True) as mock_launch, \
         patch("webbrowser.open") as mock_web:
        res = tools.open_app({"app_name": "spotify"})
        assert "spotify" in res.lower()
        mock_launch.assert_called_once_with("spotify")
        mock_web.assert_not_called()


def test_open_app_website_fallback():
    with patch("platform.system", return_value="Windows"), \
         patch("tools._launch_windows", return_value=False), \
         patch("webbrowser.open") as mock_web:
        res = tools.open_app({"app_name": "github"})
        assert "browser" in res.lower()
        mock_web.assert_called_once_with("https://github.com")
