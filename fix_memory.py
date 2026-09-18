with open("memory.py", "r", encoding="utf-8") as f:
    src = f.read()

# Natural responses for recall
old_recall = '''def tool_recall(args):
    key = args.get("key", "").strip()
    if not key:
        return list_facts()
    val = get_fact(key)
    if val:
        return f"{key} = {val}"
    # conversation search fallback
    return search_conversations(key)'''

new_recall = '''# Natural language mapping for keys
_KEY_LABELS = {
    "user_name": "Tumhara naam",
    "friend_name": "Tumhare dost ka naam",
    "brother_name": "Tumhare bhai ka naam",
    "sister_name": "Tumhari behen ka naam",
    "mother_name": "Tumhari maa ka naam",
    "father_name": "Tumhare papa ka naam",
    "gf_name": "Tumhari girlfriend ka naam",
    "wife_name": "Tumhari wife ka naam",
    "user_age": "Tumhari umar",
    "user_city": "Tum rehte ho",
    "user_birthday": "Tumhara birthday",
    "user_job": "Tumhara kaam",
}


def _natural(key, value):
    """Raw key=value ko natural sentence banao."""
    if key in _KEY_LABELS:
        return f"{_KEY_LABELS[key]} {value} hai."
    if key.startswith("like_"):
        thing = key[5:].replace("_", " ")
        return f"Tumhe {thing} pasand hai."
    if key.startswith("dislike_"):
        thing = key[8:].replace("_", " ")
        return f"Tumhe {thing} pasand nahi hai."
    return f"Yaad hai: {key} - {value}"


def tool_recall(args):
    key = args.get("key", "").strip()
    if not key:
        return list_facts()

    # Agar key match nahi karta to synonyms try karo
    synonyms = {
        "name": "user_name",
        "my_name": "user_name",
        "friend": "friend_name",
        "dost": "friend_name",
        "brother": "brother_name",
        "bhai": "brother_name",
        "sister": "sister_name",
        "behen": "sister_name",
        "mother": "mother_name",
        "maa": "mother_name",
        "father": "father_name",
        "papa": "father_name",
    }
    key = synonyms.get(key.lower(), key)

    val = get_fact(key)
    if val:
        return _natural(key, val)

    # Natural search - key naam se similar kuch bhi dhundo
    with _conn() as c:
        rows = c.execute(
            "SELECT key, value FROM facts WHERE key LIKE ?",
            (f"%{key.lower()}%",)
        ).fetchall()
        if rows:
            return " ".join(_natural(r["key"], r["value"]) for r in rows)

    return search_conversations(key)'''

if old_recall in src:
    src = src.replace(old_recall, new_recall)
    with open("memory.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("memory.py updated - natural recall")
else:
    print("Old recall not found, check manually")
