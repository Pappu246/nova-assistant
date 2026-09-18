"""
NOVA ki yaad - SQLite based memory system.
Do tarah ki yaad:
  1. Facts - "mera naam Pappu hai", "mujhe coffee pasand hai"
  2. Conversations - purani baatein
"""
import os
import sqlite3
import datetime
import re

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nova_memory.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_text TEXT,
                nova_text TEXT,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                created_at TEXT
            )
        """)


def _now():
    return datetime.datetime.now().isoformat()


# ---------- FACTS ----------
def save_fact(key, value, category="general"):
    key = key.lower().strip()
    with _conn() as c:
        c.execute("""
            INSERT INTO facts (key, value, category, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                          category=excluded.category,
                                          created_at=excluded.created_at
        """, (key, value, category, _now()))
    return f"Yaad rakh liya: {key} = {value}"


def get_fact(key):
    key = key.lower().strip()
    with _conn() as c:
        row = c.execute("SELECT value FROM facts WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def list_facts(limit=30):
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
        return " ".join(parts) if parts else "Abhi tak kuch yaad nahi hai."


def forget_fact(key):
    key = key.lower().strip()
    with _conn() as c:
        cur = c.execute("DELETE FROM facts WHERE key = ?", (key,))
        if cur.rowcount:
            return f"Bhool gaya: {key}"
    return f"'{key}' yaad hi nahi tha."


# ---------- CONVERSATIONS ----------
def log_conversation(user_text, nova_text):
    with _conn() as c:
        c.execute("""
            INSERT INTO conversations (user_text, nova_text, created_at)
            VALUES (?, ?, ?)
        """, (user_text, nova_text, _now()))


def recent_conversations(limit=5):
    with _conn() as c:
        rows = c.execute("""
            SELECT user_text, nova_text FROM conversations
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows][::-1]


def search_conversations(query, limit=5):
    q = f"%{query.lower()}%"
    with _conn() as c:
        rows = c.execute("""
            SELECT user_text, nova_text, created_at FROM conversations
            WHERE LOWER(user_text) LIKE ? OR LOWER(nova_text) LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (q, q, limit)).fetchall()
        if not rows:
            return f"'{query}' ke baare mein kuch yaad nahi."
        out = [f"'{query}' ke baare mein ye mila:"]
        for r in rows:
            out.append(f"  [{r['created_at'][:10]}] Tum: {r['user_text']}")
            out.append(f"           NOVA: {r['nova_text']}")
        return "\n".join(out)


# ---------- NOTES ----------
def save_note(content):
    with _conn() as c:
        c.execute(
            "INSERT INTO notes (content, created_at) VALUES (?, ?)",
            (content, _now())
        )
    return f"Note save kar liya: {content}"


def list_notes():
    with _conn() as c:
        rows = c.execute(
            "SELECT content, created_at FROM notes ORDER BY id DESC LIMIT 20"
        ).fetchall()
        if not rows:
            return "Koi note nahi hai."
        out = ["Tumhare notes:"]
        for r in rows:
            out.append(f"  [{r['created_at'][:10]}] {r['content']}")
        return "\n".join(out)


# ---------- AUTO EXTRACT ----------
_AUTO_PATTERNS = [
    (r"\bmer[ae] naam\s+([a-zA-Z]+)\s+(?:hai|h)\b", "name", "user_name"),
    (r"\bmer[ae] umar\s+(\d+)\b", "age", "user_age"),
    (r"\bmain\s+([a-zA-Z]+)\s+mein\s+reht[ae]\s+(?:hoon|hu)\b", "city", "user_city"),
    (r"\bmujhe\s+(.+?)\s+pasand\s+(?:hai|h)\b", "like", None),
    (r"\bmujhe\s+(.+?)\s+pasand\s+n[ah]i\b", "dislike", None),
    (r"\bmera\s+job\s+(.+?)\s+hai\b", "job", "user_job"),
]


def auto_extract(text):
    """Simple patterns se facts nikaalo."""
    found = []
    low = text.lower()
    for pat, category, key in _AUTO_PATTERNS:
        m = re.search(pat, low)
        if m:
            val = m.group(1).strip()
            if key:
                save_fact(key, val, category)
                found.append(f"{key}={val}")
            else:
                # dynamic key
                k = f"{category}_{val[:20]}"
                save_fact(k, val, category)
                found.append(f"{category}={val}")
    return found


init_db()


# ---------- TOOL WRAPPERS ----------
def tool_remember(args):
    key = args.get("key", "").strip()
    value = args.get("value", "").strip()
    if not key or not value:
        return "Kya yaad rakhna hai? Key aur value dono bolo."
    return save_fact(key, value)


# Natural language mapping for keys
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

    return search_conversations(key)


def tool_forget(args):
    key = args.get("key", "").strip()
    if not key:
        return "Kya bhoolna hai?"
    return forget_fact(key)


def tool_note(args):
    content = args.get("content", "").strip()
    if not content:
        return "Kya note karna hai?"
    return save_note(content)


def tool_list_notes(_args=None):
    return list_notes()


if __name__ == "__main__":
    init_db()
    print("Memory DB ready:", DB_PATH)
    save_fact("test_key", "test_value")
    print(get_fact("test_key"))
    forget_fact("test_key")
    print("Test complete.")