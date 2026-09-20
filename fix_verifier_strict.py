with open("verifier.py", "r", encoding="utf-8") as f:
    src = f.read()

# Make verify stricter - no length-based auto-success
old = '''    # No hint matched but also no failure - be lenient
    if len(result_str) > 3:
        return True, "Result kaafi lamba hai, assume success"

    return False, "Koi success hint nahi mila"'''

new = '''    # Strict mode: require success hint
    return False, "Koi success hint nahi mila (result: " + result_str[:60] + ")"'''

if old in src:
    src = src.replace(old, new)
    with open("verifier.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("verifier.py stricter")
else:
    print("Pattern not found")
