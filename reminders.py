"""
NOVA Reminders - time-based yaad dilana.
"""
import os
import json
import datetime
import threading
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.json")
_lock = threading.Lock()
_reminders = []
_stop = False


def _load():
    global _reminders
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                _reminders = json.load(f)
        except Exception:
            _reminders = []
    else:
        _reminders = []


def _save():
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(_reminders, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[reminders] save fail: {e}")


def _parse_time(when_text):
    """Natural text se datetime nikalo. Return datetime or None."""
    now = datetime.datetime.now()
    t = when_text.lower().strip()

    # "in X minutes/hours/seconds"
    import re
    m = re.search(r"in\s+(\d+)\s*(sec|second|min|minute|hour|ghante|ghanta|minute)", t)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if "sec" in unit:
            return now + datetime.timedelta(seconds=num)
        if "min" in unit:
            return now + datetime.timedelta(minutes=num)
        if "hour" in unit or "ghant" in unit:
            return now + datetime.timedelta(hours=num)

    # "X minutes/hours baad" ya "X minute baad"
    m = re.search(r"(\d+)\s*(sec|second|min|minute|hour|ghante|ghanta)\s*(baad|mein|me)", t)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if "sec" in unit:
            return now + datetime.timedelta(seconds=num)
        if "min" in unit:
            return now + datetime.timedelta(minutes=num)
        if "hour" in unit or "ghant" in unit:
            return now + datetime.timedelta(hours=num)

    # "at X baje" / "X baje" (24h ya 12h)
    m = re.search(r"(\d{1,2})[:.]?(\d{2})?\s*(baje|am|pm|o.clock|oclock)?", t)
    if m and ("baje" in t or "am" in t or "pm" in t or ":" in t):
        h = int(m.group(1))
        mn = int(m.group(2)) if m.group(2) else 0
        if "pm" in t and h < 12:
            h += 12
        elif "am" in t and h == 12:
            h = 0
        elif "baje" in t and h < 12 and now.hour >= 12:
            h += 12
        target = now.replace(hour=h, minute=mn, second=0, microsecond=0)
        if target < now:
            target += datetime.timedelta(days=1)
        return target

    # "tomorrow" / "kal"
    if "tomorrow" in t or "kal" in t:
        # If time not specified, use 9am tomorrow
        return (now + datetime.timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

    return None


def add_reminder(text, when_text):
    """Reminder add karo. Parse fail ho to clarification maango."""
    target = _parse_time(when_text)

    if not target:
        return ("Boss, samay samajh nahi aaya. Aise bolo: "
                "'5 baje', '10 minute baad', 'kal subah 9 baje', "
                "'2 ghante baad'. Dobara try karo.")

    with _lock:
        _reminders.append({
            "text": text,
            "when": target.isoformat(),
            "created": datetime.datetime.now().isoformat(),
            "done": False,
        })
        _save()

    time_str = target.strftime("%I:%M %p")
    date_str = target.strftime("%d %b")
    return f"Theek hai Boss, {date_str} ko {time_str} pe yaad dilaunga: {text}"


def list_reminders():
    with _lock:
        pending = [r for r in _reminders if not r.get("done")]
    if not pending:
        return "Koi reminder nahi hai."
    out = ["Tumhare reminders:"]
    for r in pending:
        t = datetime.datetime.fromisoformat(r["when"])
        out.append(f"  {t.strftime('%d %b %I:%M %p')} - {r['text']}")
    return "\n".join(out)


def clear_reminders():
    global _reminders
    with _lock:
        count = len([r for r in _reminders if not r.get("done")])
        _reminders = []
        _save()
    return f"{count} reminders saaf kar diye."


def _check_loop(on_fire):
    """Background loop - check karo reminders."""
    global _stop
    while not _stop:
        try:
            now = datetime.datetime.now()
            with _lock:
                changed = False
                for r in _reminders:
                    if r.get("done"):
                        continue
                    t = datetime.datetime.fromisoformat(r["when"])
                    if now >= t:
                        r["done"] = True
                        changed = True
                        print(f"[reminder] Fire: {r['text']}")
                        try:
                            on_fire(r["text"])
                        except Exception as e:
                            print(f"[reminder] fire fail: {e}")
                if changed:
                    _save()
        except Exception as e:
            print(f"[reminder] loop fail: {e}")
        time.sleep(15)


def start_watcher(on_fire):
    _load()
    t = threading.Thread(target=_check_loop, args=(on_fire,), daemon=True)
    t.start()
    print("[reminders] Watcher started")


def stop_watcher():
    global _stop
    _stop = True


# ---------- TOOL WRAPPERS ----------
def tool_set_reminder(args):
    text = args.get("text", "").strip()
    when = args.get("when", "").strip()
    if not text:
        return "Kya yaad dilana hai?"
    if not when:
        return "Kab yaad dilana hai? Jaise '5 baje' ya '10 minute baad'"
    return add_reminder(text, when)


def tool_list_reminders(_args=None):
    return list_reminders()


def tool_clear_reminders(_args=None):
    return clear_reminders()


_load()

if __name__ == "__main__":
    # Test
    print(add_reminder("Chai peena", "in 1 minute"))
    print(add_reminder("Meeting", "5 baje"))
    print(list_reminders())
