with open("voice_id.py", "r", encoding="utf-8") as f:
    src = f.read()

# Check current is_boss signature
if "NOVA_ALLOW_ANY" not in src:
    # Find the is_boss def and add override line right after
    import re
    pattern = re.compile(r"(def is_boss\(audio_np, threshold=[\d.]+\):)\n")
    match = pattern.search(src)
    if match:
        # Insert override
        idx = match.end()
        insert = "    # Development override\n    if os.environ.get(\"NOVA_ALLOW_ANY\") == \"1\":\n        return True\n\n"
        src = src[:idx] + insert + src[idx:]
        print("Override inserted after is_boss def")
    else:
        print("is_boss def not found")
else:
    print("Override already exists")

with open("voice_id.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Done")
