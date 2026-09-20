"""
Phase 8 tests - Voice ID security.
"""
import os
import shutil
import numpy as np

DB = "boss_voice.pkl"
BACKUP = "boss_voice.pkl.bak"


def backup():
    if os.path.exists(DB):
        shutil.copy2(DB, BACKUP)
        os.remove(DB)


def restore():
    if os.path.exists(BACKUP):
        shutil.copy2(BACKUP, DB)
        os.remove(BACKUP)


def test_no_voice_fails_closed():
    """Without voice print, is_boss must return False (fail closed)."""
    backup()
    try:
        import importlib
        import voice_id
        importlib.reload(voice_id)

        # Create fake audio
        audio = (np.random.randn(16000 * 2) * 3000).astype(np.int16)
        result = voice_id.is_boss(audio)
        print("  no-voice -> is_boss:", result)
        assert result == False, "Should fail closed"
        print("  no-voice fails closed: PASS")
    finally:
        restore()


def test_env_override():
    """NOVA_ALLOW_ANY=1 should bypass check."""
    backup()
    try:
        os.environ["NOVA_ALLOW_ANY"] = "1"
        import importlib
        import voice_id
        importlib.reload(voice_id)

        audio = (np.random.randn(16000 * 2) * 3000).astype(np.int16)
        result = voice_id.is_boss(audio)
        print("  NOVA_ALLOW_ANY=1 -> is_boss:", result)
        assert result == True, "Override should allow"
        print("  env override: PASS")
    finally:
        os.environ.pop("NOVA_ALLOW_ANY", None)
        restore()


def test_is_enrolled():
    """is_enrolled should reflect voice print existence."""
    backup()
    try:
        import importlib
        import voice_id
        importlib.reload(voice_id)
        assert voice_id.is_enrolled() == False, "No print = not enrolled"
        print("  is_enrolled (no print): PASS")
    finally:
        restore()

    import importlib
    import voice_id
    importlib.reload(voice_id)
    if os.path.exists(DB):
        assert voice_id.is_enrolled() == True, "Print exists = enrolled"
        print("  is_enrolled (with print): PASS")


if __name__ == "__main__":
    print("=" * 50)
    print("  PHASE 8 TESTS")
    print("=" * 50)
    test_no_voice_fails_closed()
    test_env_override()
    test_is_enrolled()
    print()
    print("ALL PHASE 8 TESTS PASSED")
