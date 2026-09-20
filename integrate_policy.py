with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add policy import at top
if "import policy" not in src:
    src = src.replace(
        "import json\nimport os\nimport re",
        "import json\nimport os\nimport re\nimport policy"
    )

# Update ask_nova to add policy checks
old_start = '''def ask_nova(user_message, history=None):
    if history is None:
        history = []

    messages = [{"role": "system", "content": _get_system_prompt()}]'''

new_start = '''def ask_nova(user_message, history=None):
    if history is None:
        history = []

    # ---- STEP 1: Check for pending confirmation ----
    pending = policy.get_pending()
    if pending:
        if policy.is_yes(user_message):
            policy.clear_pending()
            tool_name = pending["tool"]
            args = pending["args"]
            try:
                result = TOOLS[tool_name](args)
                return str(result)
            except Exception as e:
                return f"Boss, tool fail: {str(e)[:100]}"
        elif policy.is_no(user_message):
            policy.clear_pending()
            return "Theek hai Boss, cancel kiya."
        else:
            # User said something else - clear pending and continue
            policy.clear_pending()

    # ---- STEP 2: Normal flow ----
    messages = [{"role": "system", "content": _get_system_prompt()}]'''

if old_start in src:
    src = src.replace(old_start, new_start)
    print("ask_nova start updated with policy check")
else:
    print("Pattern not found - checking...")

# Now update tool execution block
old_exec = '''    tool_name = parsed.get("tool", "none")
    if tool_name and tool_name != "none" and tool_name in TOOLS:
        args = parsed.get("args", {}) or {}
        try:
            result = TOOLS[tool_name](args)
            return str(result)
        except Exception as e:
            return f"Tool {tool_name} fail: {str(e)[:100]}"'''

new_exec = '''    tool_name = parsed.get("tool", "none")
    if tool_name and tool_name != "none" and tool_name in TOOLS:
        args = parsed.get("args", {}) or {}

        # ---- POLICY CHECK ----
        # Blocked?
        if policy.is_blocked(tool_name, args):
            return "Boss, ye kaam blocked hai - nahi kar sakta."

        # Requires confirmation?
        if policy.requires_confirmation(tool_name, args):
            policy.set_pending(tool_name, args)
            msg = policy.make_confirmation_message(tool_name, args)
            return f"{msg} Haan ya nahi bolo."

        # Safe - execute immediately
        try:
            result = TOOLS[tool_name](args)
            return str(result)
        except Exception as e:
            return f"Tool {tool_name} fail: {str(e)[:100]}"'''

if old_exec in src:
    src = src.replace(old_exec, new_exec)
    print("Tool execution updated with policy check")
else:
    print("Tool exec pattern not found")

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("brain.py updated")
