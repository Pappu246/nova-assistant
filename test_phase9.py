"""
Phase 9 tests - Reminder hardening.
"""
import reminders


def test_clear_parse():
    r = reminders.add_reminder("test chai", "10 minute baad")
    print("  valid parse: " + r[:80])
    assert "yaad dilaunga" in r.lower() or "theek hai" in r.lower()
    print("  valid parse: PASS")


def test_bad_parse_asks():
    r = reminders.add_reminder("test meeting", "kabhi bhi")
    print("  bad parse: " + r[:80])
    assert "samajh nahi aaya" in r.lower() or "dobara" in r.lower()
    print("  bad parse asks: PASS")


def test_baje_parse():
    r = reminders.add_reminder("test lunch", "5 baje")
    print("  baje parse: " + r[:80])
    assert "yaad dilaunga" in r.lower() or "theek hai" in r.lower()
    print("  baje parse: PASS")


if __name__ == "__main__":
    print("=" * 50)
    print("  PHASE 9 TESTS")
    print("=" * 50)
    test_clear_parse()
    test_bad_parse_asks()
    test_baje_parse()
    reminders.clear_reminders()
    print()
    print("ALL PHASE 9 TESTS PASSED")
