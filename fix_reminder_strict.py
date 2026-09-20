with open("reminders.py", "r", encoding="utf-8") as f:
    src = f.read()

old_add = '''def add_reminder(text, when_text):
    """Reminder add karo. Return message."""
    target = _parse_time(when_text)
    if not target:
        # Fallback: 10 minutes baad
        target = datetime.datetime.now() + datetime.timedelta(minutes=10)
        note = " (10 min default)"
    else:
        note = ""

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
    return f"Theek hai Boss, {date_str} ko {time_str} pe yaad dilaunga: {text}{note}"'''

new_add = '''def add_reminder(text, when_text):
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
    return f"Theek hai Boss, {date_str} ko {time_str} pe yaad dilaunga: {text}"'''

if old_add in src:
    src = src.replace(old_add, new_add)
    print("add_reminder - no silent default")
else:
    print("Old add_reminder not found")

with open("reminders.py", "w", encoding="utf-8") as f:
    f.write(src)
print("reminders.py updated")
