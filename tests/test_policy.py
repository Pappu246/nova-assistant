import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import policy


def test_safe_tools():
    assert policy.classify("get_time") == policy.SAFE
    assert policy.classify("get_weather") == policy.SAFE
    assert policy.classify("take_screenshot") == policy.SAFE


def test_ask_tools():
    assert policy.classify("shutdown_pc") == policy.ASK
    assert policy.classify("open_app") == policy.ASK
    assert policy.classify("type_text") == policy.ASK


def test_unknown_tool_defaults_ask():
    assert policy.classify("unknown_tool_xyz") == policy.ASK


def test_blocked_pattern():
    assert policy.is_blocked("type_text", {"text": "rm -rf /"}) is True
    assert policy.is_blocked("type_text", {"text": "hello world"}) is False


def test_requires_confirmation():
    assert policy.requires_confirmation("get_time") is False
    assert policy.requires_confirmation("shutdown_pc") is True


def test_yes_detection():
    for word in ["haan", "yes", "ok", "theek", "kar do"]:
        assert policy.is_yes(word) is True, f"'{word}' should be yes"
    assert policy.is_yes("nahi") is False


def test_no_detection():
    for word in ["nahi", "no", "cancel", "mat karo", "ruko"]:
        assert policy.is_no(word) is True, f"'{word}' should be no"
    assert policy.is_no("haan") is False


def test_pending_flow():
    policy.clear_pending()
    assert policy.get_pending() is None

    policy.set_pending("shutdown_pc", {"mode": "shutdown"})
    p = policy.get_pending()
    assert p is not None
    assert p["tool"] == "shutdown_pc"

    policy.clear_pending()
    assert policy.get_pending() is None


def test_confirmation_message():
    msg = policy.make_confirmation_message("open_app", {"app_name": "chrome"})
    assert "chrome" in msg.lower()

    msg = policy.make_confirmation_message("shutdown_pc", {"mode": "shutdown"})
    assert "shutdown" in msg.lower()
