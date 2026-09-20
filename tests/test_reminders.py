import os
import sys
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reminders


def test_parse_minutes():
    target = reminders._parse_time("10 minute baad")
    assert target is not None
    diff = target - datetime.now()
    assert 9 <= diff.total_seconds() / 60 <= 11


def test_parse_hours():
    target = reminders._parse_time("2 ghante baad")
    assert target is not None
    diff = target - datetime.now()
    assert 1.9 <= diff.total_seconds() / 3600 <= 2.1


def test_parse_baje():
    target = reminders._parse_time("5 baje")
    assert target is not None
    assert target.hour in (5, 17)


def test_parse_tomorrow():
    target = reminders._parse_time("kal 9 baje")
    assert target is not None
    assert target.day >= datetime.now().day


def test_bad_parse_returns_none():
    assert reminders._parse_time("kabhi bhi nahi") is None


def test_add_reminder_bad_time_asks():
    r = reminders.add_reminder("test", "ajib samay")
    assert "samajh nahi aaya" in r.lower()


def test_add_reminder_valid():
    r = reminders.add_reminder("test meeting", "30 minute baad")
    assert "yaad dilaunga" in r.lower() or "theek hai" in r.lower()
    reminders.clear_reminders()


def test_clear_reminders():
    reminders.add_reminder("t1", "10 minute baad")
    reminders.add_reminder("t2", "20 minute baad")
    result = reminders.clear_reminders()
    assert "2" in result or "0" in result
