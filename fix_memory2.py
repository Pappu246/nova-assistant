with open("memory.py", "r", encoding="utf-8") as f:
    src = f.read()

old = '''def list_facts(limit=30):
    with _conn() as c:
        rows = c.execute(
            "SELECT key, value FROM facts ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        if not rows:
            return "Abhi tak kuch yaad nahi hai."
        out = ["Ye sab yaad hai mujhe:"]
        for r in rows:
            out.append(f"  - {r['key']}: {r['value']}")
        return "\\n".join(out)'''

new = '''def list_facts(limit=30):
    with _conn() as c:
        rows = c.execute(
            "SELECT key, value FROM facts ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        if not rows:
            return "Abhi tak kuch yaad nahi hai."

        user_facts = []
        other_facts = []
        for r in rows:
            k, v = r["key"], r["value"]
            if k == "user_name":
                user_facts.append(f"Tumhara naam {v} hai")
            elif k == "friend_name":
                user_facts.append(f"Tumhare dost ka naam {v} hai")
            elif k == "brother_name":
                user_facts.append(f"Tumhare bhai ka naam {v} hai")
            elif k == "sister_name":
                user_facts.append(f"Tumhari behen ka naam {v} hai")
            elif k == "mother_name":
                user_facts.append(f"Tumhari maa ka naam {v} hai")
            elif k == "father_name":
                user_facts.append(f"Tumhare papa ka naam {v} hai")
            elif k == "gf_name":
                user_facts.append(f"Tumhari girlfriend ka naam {v} hai")
            elif k == "wife_name":
                user_facts.append(f"Tumhari wife ka naam {v} hai")
            elif k == "user_age":
                user_facts.append(f"Tumhari umar {v} hai")
            elif k == "user_city":
                user_facts.append(f"Tum {v} mein rehte ho")
            elif k == "user_birthday":
                user_facts.append(f"Tumhara birthday {v} hai")
            elif k.startswith("like_"):
                user_facts.append(f"Tumhe {k[5:]} pasand hai")
            elif k.startswith("dislike_"):
                user_facts.append(f"Tumhe {k[8:]} pasand nahi")
            else:
                other_facts.append(f"{k}: {v}")

        parts = []
        if user_facts:
            parts.append(". ".join(user_facts) + ".")
        if other_facts:
            parts.append("Aur: " + ", ".join(other_facts))
        return " ".join(parts) if parts else "Abhi tak kuch yaad nahi hai."'''

if old in src:
    src = src.replace(old, new)
    with open("memory.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("list_facts updated")
else:
    print("Old list_facts not found")
