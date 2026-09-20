"""
Tests for identity and memory reliability.
"""
import os
import json
import tempfile
import shutil

def test_identity():
    """Test identity module."""
    # Backup existing
    backup = None
    if os.path.exists("identity.json"):
        with open("identity.json", "r") as f:
            backup = f.read()
        os.remove("identity.json")

    import identity

    # Test 1: No name -> Boss
    assert identity.get_name() == "Boss", "Should be Boss"
    assert identity.has_name() == False, "Should have no name"

    # Test 2: Set name
    r = identity.set_name("Pappu")
    assert r["ok"] == True, "Set should work"
    assert identity.get_name() == "Pappu"

    # Test 3: Change name without confirm -> pending
    r = identity.set_name("Rahul")
    assert r["ok"] == False
    assert r.get("pending") == True
    assert identity.get_name() == "Pappu", "Should not change"

    # Test 4: Change with confirm
    r = identity.set_name("Rahul", confirmed=True)
    assert r["ok"] == True
    assert identity.get_name() == "Rahul"

    # Test 5: Clear
    r = identity.clear_name()
    assert r["ok"] == True
    assert identity.get_name() == "Boss"

    # Restore
    if backup:
        with open("identity.json", "w") as f:
            f.write(backup)

    print("identity: PASS")


def test_memory():
    """Test memory module."""
    import memory
    from memory import save_fact, get_fact, forget_fact

    # Test 1: Save
    save_fact("test_key_xyz", "test_value")
    assert get_fact("test_key_xyz") == "test_value"

    # Test 2: Update
    save_fact("test_key_xyz", "new_value")
    assert get_fact("test_key_xyz") == "new_value"

    # Test 3: Forget
    forget_fact("test_key_xyz")
    assert get_fact("test_key_xyz") is None

    print("memory: PASS")


def test_fallback():
    """Test main.py get_user_name fallback."""
    import identity
    # Ensure no name
    identity.clear_name()
    import main
    assert main.get_user_name() == "Boss", "Fallback should be Boss"

    # Set name
    identity.set_name("Pappu", confirmed=True)
    assert main.get_user_name() == "Pappu", "Should read set name"

    print("fallback: PASS")


if __name__ == "__main__":
    test_identity()
    test_memory()
    test_fallback()
    print()
    print("ALL TESTS PASSED")
