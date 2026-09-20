with open("agent_loop.py", "r", encoding="utf-8") as f:
    src = f.read()

# Replace ASK skip with auto-allow (agent mode = implicit consent)
old = '''        if policy.requires_confirmation(tool_name, args):
            # For now, in agent mode, skip ASK tools and note them
            # Full confirmation flow not implemented yet
            print("[agent] Step skipped (needs confirmation): " + tool_name)
            results.append({
                "step": step_num,
                "tool": tool_name,
                "status": "skipped",
                "reason": "Needs user confirmation"
            })
            continue'''

new = '''        if policy.requires_confirmation(tool_name, args):
            # In agent mode: user ne already multi-step bola = implicit consent
            # So ASK tools are auto-approved (they are already classified as reversible)
            print("[agent] Step " + str(step_num) + " auto-approved (agent mode): " + tool_name)'''

if old in src:
    src = src.replace(old, new)
    print("ASK auto-allow in agent mode")
else:
    print("Pattern not found")

with open("agent_loop.py", "w", encoding="utf-8") as f:
    f.write(src)
