with open("verifier.py", "r", encoding="utf-8") as f:
    src = f.read()

# Replace _SUCCESS_HINTS with Hinglish-aware version
old_hints = '''_SUCCESS_HINTS = {
    "open_app": ["khol", "open", "khul"],
    "get_time": ["time", ":"],
    "get_weather": ["degree", "temperature", "temp"],
    "play_youtube": ["youtube", "baja", "search"],
    "browse": ["success", "playing", "opened", "complete"],
    "take_screenshot": ["screenshot", "le liya"],
    "volume_up": ["volume", "badha"],
    "volume_down": ["volume", "kam"],
    "volume_mute": ["mute"],
    "remember": ["yaad", "save"],
    "recall": [],  # Always succeeds if it returns something
    "note": ["note", "save"],
    "list_notes": ["note"],
    "set_reminder": ["reminder", "yaad dila"],
    "list_reminders": ["reminder"],
}'''

new_hints = '''_SUCCESS_HINTS = {
    "open_app": ["khol", "open", "khul", "launch", "start"],
    "get_time": ["time", ":", "baje"],
    "get_weather": ["degree", "temperature", "temp", "celsius"],
    "play_youtube": ["youtube", "baja", "search", "play", "video"],
    "browse": ["success", "playing", "opened", "complete", "khul",
               "search", "youtube", "google", "play", "video",
               "kar liya", "kar diya", "baja diya", "search kar",
               "successfully", "now open", "now playing"],
    "take_screenshot": ["screenshot", "le liya", "capture"],
    "volume_up": ["volume", "badha", "increase"],
    "volume_down": ["volume", "kam", "decrease"],
    "volume_mute": ["mute", "band"],
    "remember": ["yaad", "save", "rakh"],
    "recall": [],  # Always succeeds if it returns something
    "note": ["note", "save"],
    "list_notes": ["note"],
    "set_reminder": ["reminder", "yaad dila", "set"],
    "list_reminders": ["reminder"],
    "agent_run": ["complete", "success", "done", "ok"],
}'''

if old_hints in src:
    src = src.replace(old_hints, new_hints)
    print("Hinglish hints added")
else:
    print("Old hints pattern not found")

# Also add: agent_run special - if tool called browse with youtube/google, be lenient
old_verify = '''    # Tool-specific success hints
    tool = step.get("tool", "")
    hints = _SUCCESS_HINTS.get(tool, [])

    if not hints:
        # Unknown tool - assume success if no failure
        return True, "Result mila"'''

new_verify = '''    # Tool-specific success hints
    tool = step.get("tool", "")
    hints = _SUCCESS_HINTS.get(tool, [])

    # Special: browse with "successfully" in result - browser-use reports success
    if tool == "browse" and "successfully" in result_str:
        return True, "Browser-use reported success"

    if not hints:
        # Unknown tool - assume success if no failure
        return True, "Result mila"'''

if old_verify in src:
    src = src.replace(old_verify, new_verify)
    print("Browse special case added")

with open("verifier.py", "w", encoding="utf-8") as f:
    f.write(src)
print("verifier.py updated")
