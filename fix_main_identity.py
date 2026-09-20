with open("main.py", "r", encoding="utf-8-sig") as f:
    src = f.read()

# Replace get_user_name function
old_fn = '''def get_user_name():
    if memory:
        try:
            n = memory.get_fact("user_name")
            if n:
                return n
        except Exception:
            pass
    return "Boss"'''

new_fn = '''def get_user_name():
    """Get verified identity or fallback to 'Boss'."""
    try:
        import identity
        return identity.get_name()
    except Exception:
        # Fallback: memory module
        if memory:
            try:
                n = memory.get_fact("user_name")
                if n:
                    return n
            except Exception:
                pass
    return "Boss"'''

if old_fn in src:
    src = src.replace(old_fn, new_fn)
    print("get_user_name updated to use identity module")
else:
    print("Old function not found")

# Also fix the other memory.get_fact call around line 133
old_second = '''        import memory
        n = memory.get_fact("user_name")
        if n:
            name = n'''
new_second = '''        import identity
        name = identity.get_name()'''
if old_second in src:
    src = src.replace(old_second, new_second)
    print("Second memory read updated")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(src)
