with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add agent_run tool description AND strong rule to system prompt
agent_rule = """

*** CRITICAL: MULTI-STEP COMMANDS ***

Agar ek hi command mein 2+ kaam hain (jaise "X karo aur Y karo", "X kholo phir Y bajao"),
to HAMESHA tool = "agent_run" use karo, args = {"goal": "poori command"}.

KABHI bhi multi-step command ke liye single tool (jaise open_app) use mat karo.

MULTI-STEP TRIGGERS:
- "aur" / "and"
- "phir" / "then" / "uske baad"
- 2+ verbs ek hi command mein

EXAMPLES:
- "Chrome kholo aur YouTube pe Python dhundo" -> {"tool": "agent_run", "args": {"goal": "Chrome kholo aur YouTube pe Python dhundo"}}
- "YouTube kholo phir Kesariya bajao" -> {"tool": "agent_run", "args": {"goal": "YouTube kholo phir Kesariya bajao"}}
- "Time batao aur weather batao" -> {"tool": "agent_run", "args": {"goal": "Time batao aur weather batao"}}

SINGLE STEP (normal tools):
- "Time kya hai" -> get_time
- "Chrome kholo" -> open_app
- "Kya yaad hai" -> recall

---

"""

# Insert before "Rules (priority order):" or at start of system prompt rules
if "MULTI-STEP COMMANDS" not in src:
    # Find a good insertion point
    markers = [
        "Rules (priority order):",
        "*** GENDER",
        "*** PRIORITY 1",
        "1. MEMORY:",
        "1. IDENTITY",
    ]
    inserted = False
    for marker in markers:
        if marker in src:
            src = src.replace(marker, agent_rule + marker, 1)
            inserted = True
            print("Rule inserted before: " + marker)
            break

    if not inserted:
        # Insert after first triple-quote start
        idx = src.find('return """')
        if idx > 0:
            src = src[:idx+10] + agent_rule + src[idx+10:]
            print("Rule inserted after return-docstring start")

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("brain.py saved")
