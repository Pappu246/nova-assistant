with open("planner.py", "r", encoding="utf-8") as f:
    src = f.read()

# Ensure create_plan handles context well
old_create = '''def create_plan(goal, context=None):
    """Return list of steps for the goal."""
    goal = (goal or "").strip()
    if not goal:
        return []

    tools_list = _get_available_tools()
    if not tools_list:
        return []

    plan = _call_groq_for_plan(goal, tools_list, context)'''

new_create = '''def create_plan(goal, context=None):
    """Return list of steps. context may contain replan info."""
    goal = (goal or "").strip()
    if not goal:
        return []

    tools_list = _get_available_tools()
    if not tools_list:
        return []

    # If this is a replan, prepend REPLAN mode instruction
    if context:
        replan_header = """REPLAN MODE - the previous plan failed partway.
Follow the instructions in the context below VERY CAREFULLY.
Do NOT repeat steps that already succeeded.
Try a DIFFERENT approach for the failed step.

"""
        context = replan_header + str(context)

    plan = _call_groq_for_plan(goal, tools_list, context)'''

if old_create in src:
    src = src.replace(old_create, new_create)
    print("planner.py - replan context handling")
else:
    print("Pattern not found")

with open("planner.py", "w", encoding="utf-8") as f:
    f.write(src)
print("planner.py updated")
