with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add multi-step detection rule to prompt
if "MULTI-STEP TASKS" not in src:
    src = src.replace(
        "Rules (priority order):",
        '''*** MULTI-STEP TASKS (IMPORTANT) ***
Agar user ek saath kai kaam bole (jaise "Chrome kholo aur YouTube pe X search karo"),
to tool="agent_run" use karo, args={"goal": "poora goal"}.
Single-step commands ke liye normal tools use karo.

Trigger words: "aur", "phir", "uske baad", "then", "ke baad", multiple tasks in one command.

Example:
"Chrome kholo aur YouTube pe Python tutorial dhundo" -> agent_run goal="Chrome kholo aur YouTube pe Python tutorial dhundo"
"mera naam Pappu hai aur mujhe biryani pasand hai" -> do separate remembers (single-step)

Rules (priority order):'''
    )

# Add agent_run handler BEFORE tool execution
old_tool_check = '''    tool_name = parsed.get("tool", "none")
    if tool_name and tool_name != "none" and tool_name in TOOLS:'''

new_tool_check = '''    tool_name = parsed.get("tool", "none")

    # ---- Agent multi-step mode ----
    if tool_name == "agent_run":
        args = parsed.get("args", {}) or {}
        goal = args.get("goal", "").strip()
        if not goal:
            return "Boss, kya karna hai bolo."
        try:
            import agent_loop
            result = agent_loop.run_task(goal)
            return result
        except Exception as e:
            return "Boss, agent fail: " + str(e)[:100]

    if tool_name and tool_name != "none" and tool_name in TOOLS:'''

if old_tool_check in src:
    src = src.replace(old_tool_check, new_tool_check)
    print("agent_run handler added")
else:
    print("Tool check pattern not found")

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("brain.py updated")
