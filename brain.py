import json
import os

try:
    from groq import Groq
    _GROQ = True
except Exception:
    _GROQ = False

try:
    import ollama
    _OLLAMA = True
except Exception:
    _OLLAMA = False

from tools import TOOLS

GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"
OLLAMA_MODEL = "llama3.1"


def _get_system_prompt():
    return """Tum NOVA ho, ek personal assistant.

HAMESHA sirf ek JSON object return karo:
{"tool": "<tool_name ya none>", "args": {}, "reply": "<text>"}

Tools:
1. get_time - {}
2. get_weather - {"city": "Jaipur"}
3. open_app - {"app_name": "chrome"}
4. take_screenshot - {}
5. open_screenshots - {}
6. play_youtube - {"query": "song name"}
7. browse - {"task": "user ki poori command"}
8. close_browser - {}
9. play_spotify - {"query": "song name"}
10. volume_up - {"steps": 5}
11. volume_down - {"steps": 5}
12. volume_mute - {}
13. next_track - {}
14. prev_track - {}
15. play_pause - {}
16. lock_pc - {}
17. shutdown_pc - {"mode": "shutdown" / "restart" / "cancel"}
18. copy_to_clipboard - {"text": "..."}
19. type_text - {"text": "..."}
20. search_file - {"name": "photo", "where": "downloads"}
21. web_search - {"query": "..."}
22. remember - {"key": "user_name", "value": "Pappu"}
23. recall - {"key": "user_name"}
24. forget - {"key": "user_name"}
25. note - {"content": "..."}
26. list_notes - {}

PRIORITY 1 - MEMORY (hamesha pehle check karo):
- "mera naam X hai" -> remember user_name=X
- "mera naam kya hai" -> recall user_name
- "mere dost ka naam X hai" -> remember friend_name=X
- "mere bhai ka naam X hai" -> remember brother_name=X
- "meri behen ka naam X hai" -> remember sister_name=X
- "meri maa ka naam X hai" -> remember mother_name=X
- "mere papa ka naam X hai" -> remember father_name=X
- "mujhe X pasand hai" -> remember like_X=yes
- "meri umar X hai" -> remember user_age=X
- "kya yaad hai" -> recall ""
- "X bhool jao" -> forget X
- "note karo X" -> note content=X
- "mere notes dikhao" -> list_notes

PRIORITY 2 - SIMPLE:
- "chrome/youtube/notepad kholo" -> open_app
- "time kya hai" -> get_time
- "weather X" -> get_weather
- "screenshot lo" -> take_screenshot
- "volume badhao" -> volume_up

PRIORITY 3 - BROWSER (sirf explicit):
- "browser mein X" / "google pe X" / "youtube pe X bajao" -> browse
- "browser band karo" -> close_browser

Reply rules:
- Reply SIRF Hinglish mein, chhota 1-2 sentence (15 words max).
- "Boss" use karo.
- Natural tone: "Ho gaya Boss", "Chrome khol raha hoon".
"""


def _safe_parse(text):
    try:
        p = json.loads(text)
        if isinstance(p, dict):
            return p
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _extract_json(text):
    """Text se JSON object nikalo, chahe markdown ho ya extra text."""
    if not text:
        return None
    text = text.strip()
    # Markdown code fence hatao
    if "```" in text:
        import re
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    # Pehla { aur last } ke beech ka content
    if "{" in text and "}" in text:
        start = text.index("{")
        end = text.rindex("}") + 1
        text = text[start:end]
    try:
        return text
    except Exception:
        return None


def _call_groq(messages):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    client = Groq(api_key=key)

    # System prompt ke saath ek extra nudge
    messages = list(messages)
    messages[0] = {
        "role": "system",
        "content": messages[0]["content"] + "\n\nIMPORTANT: Reply with ONLY a valid JSON object. No markdown, no code fence, no explanation."
    }

    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=200,
            )
            raw = resp.choices[0].message.content.strip()
            clean = _extract_json(raw)
            if clean:
                # JSON valid hai? Verify karo
                try:
                    parsed = json.loads(clean)
                    if isinstance(parsed, dict) and "tool" in parsed:
                        return clean
                    else:
                        print(f"[groq {model}] JSON mein 'tool' key nahi, fallback")
                        continue
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[groq {model}] invalid JSON: {str(e)[:50]}")
                    continue
        except Exception as e:
            print(f"[groq {model} fail] {str(e)[:80]}")
            continue
    return None


def _call_ollama(messages):
    if not _OLLAMA:
        return None
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format="json",
        )
        return response["message"]["content"].strip()
    except Exception as e:
        print(f"[ollama fail] {str(e)[:80]}")
        return None


def ask_nova(user_message, history=None):
    if history is None:
        history = []

    messages = [{"role": "system", "content": _get_system_prompt()}]
    messages.extend(history[-6:])   # sirf recent 6
    messages.append({"role": "user", "content": user_message})

    # Groq pehle (fast), fail to Ollama
    raw = _call_groq(messages)
    if not raw:
        raw = _call_ollama(messages)
    if not raw:
        return "Brain load nahi hui. Groq ya Ollama check karo."

    parsed = _safe_parse(raw)
    if parsed is None:
        return raw

    tool_name = parsed.get("tool", "none")
    if tool_name and tool_name != "none" and tool_name in TOOLS:
        args = parsed.get("args", {}) or {}
        try:
            return TOOLS[tool_name](args)
        except Exception as e:
            return f"Tool {tool_name} fail: {e}"

    reply = parsed.get("reply", "").strip()
    return reply if reply else "Samajh nahi paya, dobara bolo."
