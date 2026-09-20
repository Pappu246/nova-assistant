with open("planner.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add critical rule about browse
old_rules = '''RULES:
- Har step ek tool call hoga
- Sirf available tools use karo
- Steps ko sequence mein rakho (step 1, step 2, ...)
- Max 6 steps
- Agar goal single-step hai to 1 step do'''

new_rules = '''RULES:
- Har step ek tool call hoga
- Sirf available tools use karo
- Steps ko sequence mein rakho (step 1, step 2, ...)
- Max 6 steps
- Agar goal single-step hai to 1 step do

CRITICAL - Browser rules:
- Agar goal mein "browse" tool use hoga (YouTube search, Google search, website visit), to open_app se chrome ALAG se MAT kholo. browse apna browser khud kholta hai.
- open_app sirf tab use karo jab browser automation NA ho (jaise notepad kholo, calculator kholo)
- "YouTube pe X dhundo" -> sirf browse tool (open_app mat do)
- "Chrome kholo aur YouTube pe X dhundo" -> sirf browse tool, open_app skip karo'''

if old_rules in src:
    src = src.replace(old_rules, new_rules)
    with open("planner.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("planner.py rules updated")
else:
    print("Rules pattern not found")
