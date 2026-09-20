"""
Phase 4 tests - Policy layer integration.
"""
import os
import brain
import policy


def test_safe_passthrough():
    """SAFE tools should execute without confirmation."""
    policy.clear_pending()
    result = brain.ask_nova("time kya hai")
    print(f"  time kya hai -> {result[:60]}")
    assert "time" in result.lower() or ":" in result
    print("  safe passthrough: PASS")


def test_ask_requires_confirm():
    """ASK tools should ask for confirmation."""
    policy.clear_pending()
    result = brain.ask_nova("shutdown karo")
    print(f"  shutdown karo -> {result[:80]}")
    # Should contain confirmation ask
    pending = policy.get_pending()
    assert pending is not None, "Should have pending confirmation"
    assert pending["tool"] == "shutdown_pc"
    print("  ask confirmation: PASS")


def test_confirm_yes():
    """Confirming should execute the tool."""
    # Set fake pending
    policy.set_pending("get_time", {})
    result = brain.ask_nova("haan")
    print(f"  haan -> {result[:60]}")
    pending = policy.get_pending()
    assert pending is None, "Pending should be cleared"
    print("  confirm yes: PASS")


def test_confirm_no():
    """Declining should clear pending."""
    policy.set_pending("shutdown_pc", {"mode": "shutdown"})
    result = brain.ask_nova("nahi")
    print(f"  nahi -> {result[:60]}")
    pending = policy.get_pending()
    assert pending is None
    print("  confirm no: PASS")


if __name__ == "__main__":
    print("=" * 50)
    print("  PHASE 4 TESTS")
    print("=" * 50)
    test_safe_passthrough()
    test_ask_requires_confirm()
    test_confirm_yes()
    test_confirm_no()
    print()
    print("ALL PHASE 4 TESTS PASSED")
