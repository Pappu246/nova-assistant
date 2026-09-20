import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import verifier


def test_success_hint_match():
    ok, _ = verifier.verify({"tool": "open_app"}, "chrome khol raha hoon")
    assert ok is True


def test_failure_hint_detected():
    ok, reason = verifier.verify({"tool": "open_app"}, "nahi mila")
    assert ok is False
    assert "failure" in reason.lower() or "nahi" in reason.lower()


def test_time_success():
    ok, _ = verifier.verify({"tool": "get_time"}, "Abhi time hai 5:00 PM")
    assert ok is True


def test_empty_result_fails():
    ok, _ = verifier.verify({"tool": "get_time"}, "")
    assert ok is False


def test_none_result_fails():
    ok, _ = verifier.verify({"tool": "get_time"}, None)
    assert ok is False


def test_browse_english_success():
    ok, _ = verifier.verify(
        {"tool": "browse"},
        "Successfully navigated to YouTube and played video"
    )
    assert ok is True


def test_browse_hinglish_success():
    ok, _ = verifier.verify(
        {"tool": "browse"},
        "Boss, YouTube khol kar Python search kar liya"
    )
    assert ok is True


def test_browse_failure():
    ok, _ = verifier.verify({"tool": "browse"}, "browser fail hua")
    assert ok is False
