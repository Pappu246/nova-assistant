import json
import ollama
from tools import TOOLS

MODEL_NAME = "llama3.1"

SYSTEM_PROMPT = """Tum NOVA ho, ek personal assistant.

HAMESHA sirf ek JSON object return karo:
{"tool": "<tool_name ya none>", "args": {}, "reply": "<text>"}

Tools:
1. get_time - {}
2. get_weather - {"city": "Jaipur"}
3. open_app - {"app_name": "chrome"}
4. take_screenshot - {}
5. open_screenshots - {}
6. play_youtube - {"query": "song name"}  (fast, sirf video URL kholta hai)
7. browse - {"task": "user ki poori command"}  (SMART browser agent - search karta hai, click karta hai, gaana bajata hai, form bharta hai)
8. play_spotify - {"query": "song name"}
9. volume_up - {"steps": 5}
10. volume_down - {"steps": 5}
11. volume_mute - {}
12. next_track - {}
13. prev_track - {}
14. play_pause - {}
15. lock_pc - {}
16. shutdown_pc - {"mode": "shutdown" / "restart" / "cancel"}
17. copy_to_clipboard - {"text": "..."}
18. type_text - {"text": "..."}
19. search_file - {"name": "photo", "where": "downloads"}
20. web_search - {"query": "..."}

Rules - IMPORTANT:
- Agar user bolta hai "browser mein X karo", "X click karo", "X play karo", "gaana bajao", "YouTube pe X bajao", "Amazon pe X dhundho", "form bharo", "Gmail kholo aur unread dikhao", "X search karo aur batao" - to **browse** tool use karo task mein poori command daal ke.
- Simple gaana bajana (fast) -> play_youtube
- Complex task (click karna, scroll karna, form bharo, multiple steps) -> browse

Examples:
- "kesariya gaana bajao" -> browse task="YouTube pe Kesariya gaana bajao"
- "browser mein amazon pe iphone ka price dekho" -> browse task="amazon.in pe iphone ka price dekho aur batao"
- "gmail kholo unread dikhao" -> browse task="gmail.com kholo aur unread emails dikhao"
- "youtube pe lofi music chalao" -> browse task="YouTube pe lofi music play karo"

Reply rules:
- Reply SIRF Hinglish mein.
- Chhota 1-2 sentence.
- "Boss" use karo.
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
