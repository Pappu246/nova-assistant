"""
Simple test: run continuous mode briefly, check state updates.
This test does NOT run for real - just imports and validates.
"""
import agent_state
import main

# Reset state
agent_state.reset_state()
s = agent_state.get_state()

# Verify main.py imports agent_state
assert hasattr(main, "agent_state"), "main should import agent_state"
print("main imports agent_state: OK")

# Verify state API works
s.set_mode("listening")
assert s.get_mode() == "listening"
print("mode set/get: OK")

s.add_to_context("user", "test input")
assert len(s.get_context()) == 1
print("context tracking: OK")

s.record_action("test_action")
assert s.get_snapshot()["last_action"] == "test_action"
print("action tracking: OK")

print()
print("ALL PHASE 3 TESTS PASSED")
