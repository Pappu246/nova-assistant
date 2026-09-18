with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Purane priority 1 block ko naye se replace karo
old_block = """*** PRIORITY 1 - MEMORY (hamesha pehle check karo) ***
- "mera naam X hai" -> remember {"key": "user_name", "value": "X"}
- "mera naam kya hai" -> recall {"key": "user_name"}
- "mujhe X pasand hai" -> remember {"key": "like_X", "value": "yes"}
- "mujhe X pasand nahi" -> remember {"key": "dislike_X", "value": "yes"}
- "meri umar X hai" -> remember {"key": "user_age", "value": "X"}
- "kya yaad hai" / "sab batao" -> recall {"key": ""}
- "X bhool jao" -> forget {"key": "X"}
- "note karo X" -> note {"content": "X"}
- "mere notes dikhao" -> list_notes {}
- Ye commands KABHI browse pe MAT bhejo."""

new_block = """*** PRIORITY 1 - MEMORY (hamesha pehle check karo) ***

Relationship patterns (IMPORTANT - ye sab save karo):
- "mera naam X hai" / "main X hoon" -> remember {"key": "user_name", "value": "X"}
- "mera naam kya hai" -> recall {"key": "user_name"}
- "mere dost ka naam X hai" / "mera dost X hai" -> remember {"key": "friend_name", "value": "X"}
- "mere dost ka naam kya hai" -> recall {"key": "friend_name"}
- "mera bhai ka naam X hai" -> remember {"key": "brother_name", "value": "X"}
- "meri behen ka naam X hai" -> remember {"key": "sister_name", "value": "X"}
- "meri maa ka naam X hai" -> remember {"key": "mother_name", "value": "X"}
- "mere papa ka naam X hai" / "mere pita ka naam X" -> remember {"key": "father_name", "value": "X"}
- "meri girlfriend ka naam X hai" -> remember {"key": "gf_name", "value": "X"}
- "meri wife ka naam X hai" -> remember {"key": "wife_name", "value": "X"}

Personal info:
- "mujhe X pasand hai" -> remember {"key": "like_X", "value": "yes"}
- "mujhe X pasand nahi" -> remember {"key": "dislike_X", "value": "yes"}
- "meri umar X hai" -> remember {"key": "user_age", "value": "X"}
- "main X mein rehta hoon" -> remember {"key": "user_city", "value": "X"}
- "mera birthday X hai" -> remember {"key": "user_birthday", "value": "X"}

Recall/forget/notes:
- "kya yaad hai" / "sab batao" -> recall {"key": ""}
- "X bhool jao" -> forget {"key": "X"}
- "note karo X" -> note {"content": "X"}
- "mere notes dikhao" -> list_notes {}

RULES:
- Jab bhi user "X ka naam Y hai" bole (kisi bhi relationship ka), turant remember call karo
- Jab bhi user "X ka naam kya hai" puche, recall call karo
- Ye commands KABHI browse pe MAT bhejo
- Sirf reply mat do - actual remember tool call karo"""

if old_block in src:
    src = src.replace(old_block, new_block)
    with open("brain.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("Memory patterns updated")
else:
    print("Old block nahi mila. Manually check karo.")
