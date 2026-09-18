with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

new_rules = """Rules - VERY IMPORTANT (priority order):

*** PRIORITY 1 - MEMORY (hamesha pehle check karo) ***
- "mera naam X hai" -> remember {"key": "user_name", "value": "X"}
- "mera naam kya hai" -> recall {"key": "user_name"}
- "mujhe X pasand hai" -> remember {"key": "like_X", "value": "yes"}
- "mujhe X pasand nahi" -> remember {"key": "dislike_X", "value": "yes"}
- "meri umar X hai" -> remember {"key": "user_age", "value": "X"}
- "kya yaad hai" / "sab batao" -> recall {"key": ""}
- "X bhool jao" -> forget {"key": "X"}
- "note karo X" -> note {"content": "X"}
- "mere notes dikhao" -> list_notes {}
- Ye commands KABHI browse pe MAT bhejo.

*** PRIORITY 2 - SIMPLE TOOLS ***
- "chrome/youtube/notepad kholo" -> open_app
- "time kya hai" -> get_time
- "weather X" -> get_weather
- "screenshot lo" -> take_screenshot
- "volume badhao" -> volume_up
- Ye bhi KABHI browse pe MAT bhejo.

*** PRIORITY 3 - BROWSER (sirf explicit) ***
Sirf tab browse jab user SAAF bole:
- "browser mein X karo"
- "google pe X search karo"
- "amazon pe X price dekho"
- "youtube pe X gaana bajao"
Warna browse USE MAT KARO.

"""

for old_header in ["Rules - IMPORTANT:\n- ", "Rules:\n- ", "Rules:\n"]:
    if old_header in src:
        src = src.replace(old_header, new_rules + "- ", 1)
        break

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Brain priority fix applied")
