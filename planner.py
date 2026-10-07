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
    "open_app": {"app_name": "str (whatsapp, telegram, spotify, chrome, notepad, calculator, vscode, vlc, discord, word, excel, paint, explorer)"},
    "take_screenshot": {},
    "open_screenshots": {},
    "play_youtube": {"query": "str - plays FIRST video directly"},
    "browse": {"task": "str (full English instruction for browser automation - ONLY for websites/web-scraping like Amazon/Wikipedia, NEVER for installed desktop apps like WhatsApp, Telegram, Spotify, Notepad)"},
    "close_browser": {},
    "play_spotify": {"query": "str"},
    "volume_up": {"steps": "int"},
    "volume_down": {"steps": "int"},
    "volume_mute": {},
    "volume_unmute": {},
    "toggle_mute": {},
    "is_muted": {},
    "mute": {},
    "unmute": {},
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
    "clear_reminders": {},
    # Vision - active window by default (FIXES terminal bug)
    "vision_click": {"target": "str (visual element description)", "dry_run": "bool"},
    "click_text": {"target": "str", "nth": "int"},
    "double_click_text": {"target": "str", "nth": "int"},
    "right_click_text": {"target": "str", "nth": "int"},
    "read_screen": {"region_mode": "str (active/full)"},
    "find_on_screen": {"target": "str"},
    "close_app": {"name": "str"},
    "focus_window": {"title": "str"},
    "list_windows": {},
    "press_key": {"key": "str (e.g. enter, ctrl+s)"},
    "youtube_search": {"query": "str - plays first video"},
    "google_search": {"query": "str"},
    "open_url": {"url": "str"},
    "screenshot": {"path": "str (optional)"},
    "smart_action": {"intent": "str", "target": "str (optional)"},
    "live_data": {"query": "str"},
    "live_news": {"topic": "str", "limit": "int"},
    "live_crypto": {"coin": "str"},
    "live_stock": {"symbol": "str"},
    # Comms calls (WhatsApp voice/video)
    "whatsapp_call": {"contact": "str", "video": "bool (true = video call, false/omit = voice call)"},
    "whatsapp_send": {"contact": "str", "message": "str"},
    "whatsapp_reply": {"message": "str"},
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
- open_app tool: args = {"app_name": "whatsapp"}  (NOT "name")

RULES:
- Har step ek tool call hoga
- Sirf available tools use karo
- Steps ko sequence mein rakho (step 1, step 2, ...)
- Max 6 steps
- Agar goal single-step hai to 1 step do

CRITICAL - Desktop Apps vs Browser:
- Installed desktop applications (WhatsApp, Telegram, Spotify, Discord, VS Code, Notepad, Calc, Word, Excel, VLC, File Explorer, etc.) MUST ALWAYS be opened using open_app (e.g. open_app(app_name="whatsapp")).
- NEVER use browse tool for desktop apps like WhatsApp, Telegram, Spotify, Discord! The browse tool opens an isolated clean browser without user login sessions/cookies.
- Use browse tool ONLY when the user explicitly asks to automate/scrape a website in the web browser (e.g. 'Amazon pe search karo', 'Wikipedia article padho').
- If user asks to interact with an installed desktop app (e.g. 'WhatsApp kholke contacts dikhao' or 'WhatsApp kholke screenshot lo'):
  Step 1: open_app {"app_name": "whatsapp"}
  Step 2: read_screen {} OR take_screenshot {} OR click_text {"target": "..."}
- Agar goal mein "browse" tool use hoga (web search, website visit), to open_app se chrome ALAG se MAT kholo. browse apna browser khud kholta hai.
- open_app sirf tab use karo jab browser automation NA ho (jaise whatsapp kholo, notepad kholo, calculator kholo)
- Har step mein ye JSON format: {"step": 1, "tool": "tool_name", "args": {...}, "description": "short hint"}

CRITICAL - WhatsApp / MESSAGING FLOW (SEND STEP KABHI MAT BHOOLNA):
- Message sirf TYPE karna kaafi NAHI hai - type karne ke BAAD
  press_key {"key": "enter"} se SEND karna ZAROORI hai!
- "X ko message karo Y" / "X ko whatsapp pe Y bhejo" ka plan:
  Step 1: open_app {"app_name": "whatsapp"}
  Step 2: vision_click {"target": "search box"}      (contact search box)
  Step 3: type_text {"text": "X"}                    (contact ka naam type)
  Step 4: press_key {"key": "enter"}                 (contact ki chat kholo)
  Step 5: type_text {"text": "Y"}                    (message box me message type)
  Step 6: press_key {"key": "enter"}                 (MESSAGE SEND - FINAL STEP, kabhi skip mat karo!)
- Chat me message type karne ke baad plan ka AAKHRI step HAMESHA
  press_key {"key": "enter"} hona chahiye, warna message type hoke reh jayega, SEND nahi hoga.
- Note: enter DO baar alag-alag jagah aa sakta hai (contact select + message send) - dono valid steps hain.

CRITICAL - WHATSAPP CALL FLOW (CALL ka plan - message flow se ALAG):
- "X ko call karo" / "X ko phone karo" / "X se baat karni hai" / "X ko video call karo" ka plan:
  Step 1: whatsapp_call {"contact": "X", "video": false}   (VOICE call)
  ya:     whatsapp_call {"contact": "X", "video": true}    (VIDEO call jab user video bole)
- whatsapp_call khud WhatsApp kholta hai, naam se chat search karta hai aur
  upar-right wala call button dabata hai - isliye is plan me ALAG se
  open_app / vision_click / type_text / press_key jaise steps MAT banao.
- Call me koi message/send step NAHI hota - call button click hi final step hai.
  Isliye call goals me press_key {"key": "enter"} add MAT karo.

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


# ---- SEND FIX (NOVA): WhatsApp/message goals me final send-step ensure karo ----
_MSG_GOAL_HINTS = ("message", "msg", "bhej", "send", "whatsapp", "likh")
# ---- CALL FIX (NOVA): call goals me send-step append NAHI karna ----
# ("Pinkesh ko whatsapp call karo" me 'whatsapp' hai par ye messaging nahi hai)
_CALL_GOAL_HINTS = ("call karo", "call lagao", "call kar do", "call laga",
                    "video call", "voice call", "phone karo", "phone lagao",
                    "call karna", "call kar")
_TYPE_TOOLS = {"type_text", "type_in_field", "ui_type_in_field", "ui_set_text", "set_text"}


def _is_enter_step(step):
    if step.get("tool") not in ("press_key", "ui_press_key"):
        return False
    key = str((step.get("args") or {}).get("key", "")).lower()
    return "enter" in key or "return" in key


def _is_call_goal(goal):
    """Goal WhatsApp call/message me se kya hai? Call goal me send-step
    (press_key enter) append nahi hota - call button click hi final hai."""
    g = (goal or "").lower()
    if not any(h in g for h in _CALL_GOAL_HINTS):
        return False
    # Mixed goal (call + message) me message flow important hai
    return not any(h in g for h in ("message", "msg bhej", "bhejo"))


def _ensure_send_step(goal, steps):
    """
    SEND FIX (NOVA): 'X ko message karo Y' jaise goals me LLM aksar message
    TYPE karwa deta hai par SEND (press_key enter) bhool jata hai.
    Agar aakhri typing step ke baad koi enter/send step nahi hai,
    to final press_key enter step append karo.
    CALL FIX (NOVA): call goals me koi send/enter step nahi hota.
    """
    g = (goal or "").lower()
    if not steps or _is_call_goal(g):
        return steps
    if not any(h in g for h in _MSG_GOAL_HINTS):
        return steps

    last_type_idx = None
    for i, s in enumerate(steps):
        if s.get("tool") in _TYPE_TOOLS:
            last_type_idx = i
    if last_type_idx is None:
        return steps

    # Kya last typing ke BAAD koi enter (send) step hai?
    for s in steps[last_type_idx + 1:]:
        if _is_enter_step(s):
            return steps

    print("[planner] SEND FIX: message type ke baad send-step missing tha - press_key enter add kiya")
    steps.append({
        "step": len(steps) + 1,
        "tool": "press_key",
        "args": {"key": "enter"},
        "description": "Message SEND karo (Enter)",
        "status": "pending",
    })
    for i, s in enumerate(steps, 1):
        s["step"] = i
    return steps


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

    # SEND FIX (NOVA): messaging goals me final send (enter) step ensure karo
    valid = _ensure_send_step(goal, valid)

    return valid


if __name__ == "__main__":
    # Test
    print("Testing planner...")
    plan = create_plan("Chrome kholo aur YouTube pe Python tutorial search karo")
    print("Plan:")
    for step in plan:
        print("  Step " + str(step["step"]) + ": " + step["tool"] + " " + str(step["args"]))
        print("    " + step["description"])
