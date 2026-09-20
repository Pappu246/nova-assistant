with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Find and replace the multi-step rule with stronger version
old = '''*** MULTI-STEP TASKS (IMPORTANT) ***
Agar user ek saath kai kaam bole (jaise "Chrome kholo aur YouTube pe X search karo"),
to tool="agent_run" use karo, args={"goal": "poora goal"}.
Single-step commands ke liye normal tools use karo.

Trigger words: "aur", "phir", "uske baad", "then", "ke baad", multiple tasks in one command.

Example:
"Chrome kholo aur YouTube pe Python tutorial dhundo" -> agent_run goal="Chrome kholo aur YouTube pe Python tutorial dhundo"
"mera naam Pappu hai aur mujhe biryani pasand hai" -> do separate remembers (single-step)'''

new = '''*** MULTI-STEP TASKS - ABSOLUTE RULE ***
Agar user ek command mein DO YA ZYADA kaam bole, to HAMESHA tool="agent_run" use karo.
KABHI bhi ek hi command ke liye multiple tools ya single tool use mat karo agar multi-step hai.

Trigger detection (koi bhi ho to agent_run):
- "aur" / "and" / "phir" / "then" / "uske baad" / "after that" / "ke baad"
- Ek command mein 2+ verbs: "kholo aur search karo", "bajao aur likho"
- Sequence: "pehle X phir Y"

STRONG EXAMPLES (ye HAMESHA agent_run):
- "Chrome kholo aur YouTube pe Python dhundo" -> agent_run {"goal": "Chrome kholo aur YouTube pe Python dhundo"}
- "YouTube kholo phir Kesariya bajao" -> agent_run {"goal": "YouTube kholo phir Kesariya bajao"}
- "Time batao aur weather bhi batao" -> agent_run {"goal": "Time batao aur weather bhi batao"}

Single-step sirf tab jab ek hi kaam ho:
- "Time kya hai" -> get_time
- "Chrome kholo" -> open_app
- "Kya yaad hai" -> recall'''

if old in src:
    src = src.replace(old, new)
    print("Prompt strengthened")
else:
    print("Old block not found - checking alternate...")
    # Try simpler replace
    if "MULTI-STEP TASKS" in src:
        # Just append stronger rule
        src = src.replace(
            "Trigger words:",
            "STRICT RULE: Ek hi command mein 2+ verbs ho to HAMESHA agent_run. Trigger words:"
        )
        print("Alternate fix applied")

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
