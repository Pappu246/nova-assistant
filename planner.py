"""
NOVA Planner - decompose a goal into executable steps using LLM.
"""
import os
import json
import re


def _get_available_tools():
    """Get list of tools available for planning."""
    try:
        from tools import TOOLS
        return list(TOOLS.keys())
    except Exception:
        return []




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
    return "\n".join(lines)


def _call_groq_for_plan(goal, tools_list, context):
    """Ask Groq to create a step-by-step plan."""
    try:
        from groq import Groq
    except Exception:
        return None

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None

    prompt = """Tum ek planner ho. User ke goal ko chhote executable steps mein todo.

Goal: """ + goal + """

Available tools with ARG SCHEMAS:\n""" + _get_schema_text() + """

""" + (context or "") + """

CRITICAL - Use EXACT arg names from schema:
- browse tool: args = {"task": "English instruction"}  (NOT "url")
- open_app tool: args = {"app_name": "chrome"}  (NOT "name")

RULES:
- Har step ek tool call hoga
- Sirf available tools use karo
- Steps ko sequence mein rakho (step 1, step 2, ...)
- Max 6 steps
- Agar goal single-step hai to 1 step do

CRITICAL - Browser rules:
- Agar goal mein "browse" tool use hoga (YouTube search, Google search, website visit), to open_app se chrome ALAG se MAT kholo. browse apna browser khud kholta hai.
- open_app sirf tab use karo jab browser automation NA ho (jaise notepad kholo, calculator kholo)
- "YouTube pe X dhundo" -> sirf browse tool (open_app mat do)
- "Chrome kholo aur YouTube pe X dhundo" -> sirf browse tool, open_app skip karo
- Har step mein ye JSON format: {"step": 1, "tool": "tool_name", "args": {...}, "description": "short hint"}

Return SIRF JSON array, aur kuch nahi:
[
  {"step": 1, "tool": "...", "args": {...}, "description": "..."},
  {"step": 2, "tool": "...", "args": {...}, "description": "..."}
]"""

    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "Tum sirf JSON array return karte ho. Kabhi text nahi."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=800,
            timeout=20,
        )
        raw = resp.choices[0].message.content.strip()
        return _extract_json_array(raw)
    except Exception as e:
        print("[planner] groq fail: " + str(e)[:80])
        return None


def _extract_json_array(text):
    """Parse JSON array from LLM output, tolerate markdown fences."""
    if not text:
        return None
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    if "[" in text and "]" in text:
        start = text.index("[")
        end = text.rindex("]") + 1
        text = text[start:end]
    try:
        arr = json.loads(text)
        if isinstance(arr, list):
            return arr
    except Exception:
        pass
    return None


def create_plan(goal, context=None):
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

    plan = _call_groq_for_plan(goal, tools_list, context)

    if not plan:
        return []

    # Validate each step
    valid = []
    for i, step in enumerate(plan, 1):
        if not isinstance(step, dict):
            continue
        tool = step.get("tool", "").strip()
        if tool not in tools_list:
            print("[planner] invalid tool skipped: " + tool)
            continue
        valid.append({
            "step": i,
            "tool": tool,
            "args": step.get("args", {}) or {},
            "description": step.get("description", ""),
            "status": "pending",
        })

    return valid


if __name__ == "__main__":
    # Test
    print("Testing planner...")
    plan = create_plan("Chrome kholo aur YouTube pe Python tutorial search karo")
    print("Plan:")
    for step in plan:
        print("  Step " + str(step["step"]) + ": " + step["tool"] + " " + str(step["args"]))
        print("    " + step["description"])
