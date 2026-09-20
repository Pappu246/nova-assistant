"""
Phase 5 test - agent multi-step execution.
"""
import policy
import brain

def test_multistep():
    policy.clear_pending()
    print("Testing multi-step: Chrome kholo aur YouTube search karo...")
    print()
    result = brain.ask_nova("Chrome kholo aur YouTube pe Python tutorial search karo")
    print()
    print("RESULT:")
    print(result)
    print()

def test_single_step():
    """Single step should still work normally."""
    policy.clear_pending()
    result = brain.ask_nova("time kya hai")
    print("Single step test: " + result[:60])
    assert "time" in result.lower() or ":" in result
    print("single step: PASS")


if __name__ == "__main__":
    print("=" * 55)
    print("  PHASE 5 TESTS")
    print("=" * 55)
    print()
    test_single_step()
    print()
    test_multistep()
    print()
    print("Done")
