with open("planner.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add tool schema function
schema_fn = '''

# Tool argument schemas - CRITICAL for correct planning
TOOL_SCHEMAS = {
    "get_time": {},
    "get_weather": {"city": "str"},
    "open_app": {"app_name": "str (chrome, notepad, calculator, vscode, vlc)"},
    "take_screenshot": {},
    "open_screenshots": {},
    "play_youtube": {"query": "str"},
    "browse": {"task": "str (full English instruction for browser)"},
    "close_browser": {},
    "play_spotify": {"query": "str"},
    "volume_up": {"steps": "int"},
    "volume_down": {"steps": "int"},
    "volume_mute": {},
    "next_track": {},
    "prev_track": {},
    "play_pause": {},
    "lock_pc": {},
    "shutdown_pc": {"mode": "shutdown|restart|cancel"},
    "copy_to_clipboard": {"text": "str"},
    "type_text": {"text": "str"},
    "search_file": {"name": "str", "where": "downloads|documents|desktop"},
    "web_search": {"query": "str"},
    "remember": {"key": "str", "value": "str"},
    "recall": {"key": "str"},
    "forget": {"key": "str"},
    "note": {"content": "str"},
    "list_notes": {},
    "set_reminder": {"text": "str", "when": "str"},
    "list_reminders": {},
}


def _get_schema_text():
    """Human-readable tool schema for the LLM prompt."""
    lines = []
    for tool, args in TOOL_SCHEMAS.items():
        if not args:
            lines.append("- " + tool + ": args = {}")
        else:
            arg_str = ", ".join('"' + k + '": ' + v for k, v in args.items())
            lines.append("- " + tool + ": args = {" + arg_str + "}")
    return "\\n".join(lines)

'''

if "TOOL_SCHEMAS" not in src:
    # Insert before _call_groq_for_plan
    src = src.replace("def _call_groq_for_plan", schema_fn + "\ndef _call_groq_for_plan", 1)

# Update prompt to use schema
old_prompt_line = 'Available tools: """ + ", ".join(tools_list) + """'
new_prompt_line = 'Available tools with ARG SCHEMAS:\\n""" + _get_schema_text() + """'

src = src.replace(old_prompt_line, new_prompt_line)

# Add explicit browse example
src = src.replace(
    "RULES:",
    '''CRITICAL - Use EXACT arg names from schema:
- browse tool: args = {"task": "English instruction"}  (NOT "url")
- open_app tool: args = {"app_name": "chrome"}  (NOT "name")

RULES:''',
    1
)

with open("planner.py", "w", encoding="utf-8") as f:
    f.write(src)
print("planner.py - tool schemas added")
