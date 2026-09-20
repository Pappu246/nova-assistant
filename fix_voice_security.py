with open("voice_id.py", "r", encoding="utf-8") as f:
    src = f.read()

# Fix 1: is_boss - fail closed if no voice print
old_is_boss = '''def is_boss(audio_np, threshold=0.50):
    if not os.path.exists(VOICE_DB):
        return True
    emb = _embed(audio_np)
    if emb is None:
        return True'''

new_is_boss = '''def is_boss(audio_np, threshold=0.50):
    """Return True only if voice matches stored print.
    FAIL CLOSED: missing print or embed error -> False."""
    if not os.path.exists(VOICE_DB):
        print("[voice_id] SECURITY: no voice print. Fail closed.")
        return False

    emb = _embed(audio_np)
    if emb is None:
        print("[voice_id] SECURITY: embed failed. Fail closed.")
        return False'''

if old_is_boss in src:
    src = src.replace(old_is_boss, new_is_boss)
    print("is_boss -> fail-closed")
else:
    # Try alternate patterns
    src = src.replace(
        '''    if not os.path.exists(VOICE_DB):
        return True''',
        '''    if not os.path.exists(VOICE_DB):
        print("[voice_id] SECURITY: no voice print. Fail closed.")
        return False'''
    )
    src = src.replace(
        '''    emb = _embed(audio_np)
    if emb is None:
        return True''',
        '''    emb = _embed(audio_np)
    if emb is None:
        print("[voice_id] SECURITY: embed failed. Fail closed.")
        return False'''
    )
    print("Applied alternate fail-closed fix")

# Fix 2: Add allow-any env override for development
if "NOVA_ALLOW_ANY" not in src:
    src = src.replace(
        "def is_boss(audio_np, threshold=0.50):",
        '''def is_boss(audio_np, threshold=0.50):
    # Development override (use only for testing)
    if os.environ.get("NOVA_ALLOW_ANY") == "1":
        return True
'''
    )
    print("Env override added")

# Fix 3: Add helper to check if voice is enrolled
if "def is_enrolled" not in src:
    src = src.replace(
        "def has_voice():",
        '''def is_enrolled():
    """Check if user voice is registered."""
    return os.path.exists(VOICE_DB)


def has_voice():'''
    )

with open("voice_id.py", "w", encoding="utf-8") as f:
    f.write(src)
print("voice_id.py updated")
