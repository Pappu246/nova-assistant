"""
NOVA Identity Manager - reliable user identity storage.

Rules:
- Never invent a name
- Never silently replace existing name
- If no name, return "Boss"
- Explicit confirm required for changes
"""
import os
import json
import datetime

IDENTITY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "identity.json"
)


def _load():
    if os.path.exists(IDENTITY_PATH):
        try:
            with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save(data):
    try:
        with open(IDENTITY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print("[identity] save fail: " + str(e))
        return False


def get_name():
    """Return verified user name or 'Boss'."""
    data = _load()
    name = data.get("verified_name")
    if name and isinstance(name, str) and name.strip():
        return name.strip()
    return "Boss"


def has_name():
    """Check if user has a verified name."""
    data = _load()
    return bool(data.get("verified_name"))


def set_name(name, confirmed=False):
    """Set user name. Existing name change requires confirmed=True."""
    name = (name or "").strip()
    if not name or len(name) > 50:
        return {"ok": False, "error": "Invalid name"}

    data = _load()
    existing = data.get("verified_name")

    if existing and existing.lower() != name.lower() and not confirmed:
        return {
            "ok": False,
            "pending": True,
            "old": existing,
            "new": name,
            "message": "Tumhara naam pehle '" + existing + "' tha. Naya naam '" + name + "' karna hai? 'haan' bolo confirm ke liye."
        }

    data["verified_name"] = name
    data["updated_at"] = datetime.datetime.now().isoformat()
    if _save(data):
        return {"ok": True, "name": name, "message": "Naam save: " + name}
    return {"ok": False, "error": "Save failed"}


def clear_name():
    data = _load()
    data["verified_name"] = None
    data["updated_at"] = datetime.datetime.now().isoformat()
    if _save(data):
        return {"ok": True, "message": "Naam clear ho gaya. Ab Boss bulaoonga."}
    return {"ok": False, "error": "Save failed"}


def get_pending():
    """Check if there is a pending identity change."""
    data = _load()
    return data.get("pending_name")


def set_pending(new_name, old_name):
    data = _load()
    data["pending_name"] = {"new": new_name, "old": old_name}
    data["pending_at"] = datetime.datetime.now().isoformat()
    _save(data)


def clear_pending():
    data = _load()
    data.pop("pending_name", None)
    data.pop("pending_at", None)
    _save(data)


if __name__ == "__main__":
    print("Name:", get_name())
    print("Has name:", has_name())
    print("Set 'Test':", set_name("Test"))
    print("Now:", get_name())
    print("Change to 'Other':", set_name("Other"))  # should be pending
    print("Confirm:", set_name("Other", confirmed=True))
    print("Clear:", clear_name())
    print("After clear:", get_name())
