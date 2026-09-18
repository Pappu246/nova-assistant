import json
import ollama
from tools import TOOLS

MODEL_NAME = "llama3.1"

SYSTEM_PROMPT = """Tum NOVA ho, Iron Man ke Jarvis jaisa personal assistant.

HAMESHA sirf ek JSON object return karo:
{"tool": "<tool_name ya none>", "args": {}, "reply": "<text>"}

Tools:
1. get_time - Args: {}
2. get_weather - Args: {"city": "Jaipur"}
3. open_app - Args: {"app_name": "chrome"}
4. take_screenshot - Args: {}
5. open_screenshots - Args: {}
6. play_youtube - Args: {"query": "song name"}
7. volume_up - Args: {"steps": 5}
8. volume_down - Args: {"steps": 5}
9. volume_mute - Args: {}
10. lock_pc - Args: {}
11. shutdown_pc - Args: {"mode": "shutdown" or "restart" or "cancel"}
12. copy_to_clipboard - Args: {"text": "..."}
13. type_text - Args: {"text": "..."}
14. search_file - Args: {"name": "photo", "where": "downloads"}
15. web_search - Args: {"query": "..."}

Rules:
- Command match kare to tool mein naam, args bharo, reply khaali rakho.
- Normal baat-cheet ho to tool none, args {}, reply mein Hinglish jawab.
- screenshot lo - take_screenshot
- screenshot dikhao - open_screenshots
- X gaana bajao - play_youtube
- volume badhao kam mute - volume_up down mute
- PC band restart lock - shutdown_pc lock_pc
- downloads mein X dhundho - search_file
- google pe X search - web_search
- Hinglish mein chhota jawab.
"""


def ask_nova(user_message, history=None):
    if history is None:
        history = []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            format="json",
        )
        raw = response["message"]["content"].strip()
    except Exception as e:
        return f"Ollama se baat nahi ho paayi: {e}"

    parsed = _safe_parse(raw)
    if parsed is None:
        return raw

    tool_name = parsed.get("tool", "none")
    if tool_name and tool_name != "none" and tool_name in TOOLS:
        args = parsed.get("args", {}) or {}
        try:
            return TOOLS[tool_name](args)
        except Exception as e:
            return f"Tool {tool_name} fail hua: {e}"

    reply = parsed.get("reply", "").strip()
    return reply if reply else "Samajh nahi paya, dobara bolo."


def _safe_parse(text):
    try:
        p = json.loads(text)
        if isinstance(p, dict):
            return p
    except (json.JSONDecodeError, ValueError):
        pass
    return None
