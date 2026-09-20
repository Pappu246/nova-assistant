"""
NOVA brain - Groq LLM + 26 tools + gender fix.
"""
import json
import os
import re
import policy

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

try:
    from tools import TOOLS
except Exception as e:
    print(f"[brain] tools import fail: {e}")
    TOOLS = {}

GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"
OLLAMA_MODEL = "llama3.2"


_FEMALE_TO_MALE = [
    (r"\bkar rahi hoon\b", "kar raha hoon"),
    (r"\bkar rahi thi\b", "kar raha tha"),
    (r"\bkar rahi\b", "kar raha"),
    (r"\bbol rahi hoon\b", "bol raha hoon"),
    (r"\bbol rahi\b", "bol raha"),
    (r"\bsun rahi hoon\b", "sun raha hoon"),
    (r"\bsun rahi\b", "sun raha"),
    (r"\bsoch rahi hoon\b", "soch raha hoon"),
    (r"\bsoch rahi\b", "soch raha"),
    (r"\bso rahi\b", "so raha"),
    (r"\bja rahi\b", "ja raha"),
    (r"\baa rahi\b", "aa raha"),
    (r"\bsamajh gayi\b", "samajh gaya"),
    (r"\bkar gayi\b", "kar gaya"),
    (r"\bbool gayi\b", "bhool gaya"),
    (r"\bso gayi\b", "so gaya"),
    (r"\baa gayi\b", "aa gaya"),
    (r"\bja gayi\b", "ja gaya"),
    (r"\bho gayi\b", "ho gaya"),
    (r"\bban gayi\b", "ban gaya"),
    (r"\bde gayi\b", "de gaya"),
    (r"\ble gayi\b", "le gaya"),
    (r"\bbaithi hoon\b", "baitha hoon"),
    (r"\bbaithi thi\b", "baitha tha"),
    (r"\bbaithi\b", "baitha"),
    (r"\bkhadi hoon\b", "khada hoon"),
    (r"\bkhadi\b", "khada"),
    (r"\btaiyaar thi\b", "taiyaar tha"),
    (r"\bmadad karungi\b", "madad karunga"),
    (r"\bkarungi\b", "karunga"),
    (r"\bbolungi\b", "bolunga"),
    (r"\bsunungi\b", "sununga"),
    (r"\bjaungi\b", "jaunga"),
    (r"\baungi\b", "aaunga"),
    (r"\bsakungi\b", "sakunga"),
    (r"\brahungi\b", "rahunga"),
    (r"\bgayi\b", "gaya"),
    (r"\brahi\b", "raha"),
    (r"\bthi\b", "tha"),
    (r"\bhui\b", "hua"),
    (r"\bboli\b", "bola"),
    (r"\bsuni\b", "suna"),
    (r"\bkari\b", "kara"),
    (r"\bjaayi\b", "jaaya"),
]


def _fix_gender(text):
    if not text:
        return text
    t = text
    for pattern, replacement in _FEMALE_TO_MALE:
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
    return t


def _get_system_prompt():
    return """Tum NOVA ho - Boss ka personal AI assistant. Tum LADKA ho (male).

Bahut important:
- Tum MALE ho. Apne baare mein HAMESHA "kar raha hoon", "bol raha hoon", "sun raha hoon" use karo. Kabhi "rahi" nahi.
- Reply SIRF Hinglish mein (Hindi + English mix, Roman letters).
- Reply SHORT rakho - 1-2 sentences max, 15 words tak.
- Zaroori na ho to lamba essay MAT do.
- "Boss" use karo.

HAMESHA sirf ek JSON return karo:
{"tool": "<name ya none>", "args": {}, "reply": "<text>"}

Tools:
get_time, get_weather(city), open_app(app_name), take_screenshot, open_screenshots,
play_youtube(query), browse(task), close_browser,
volume_up, volume_down, volume_mute, next_track, prev_track, play_pause,
lock_pc, shutdown_pc(mode: STRICT 'shutdown'/'restart'/'cancel'), copy_to_clipboard(text), type_text(text),
search_file(name, where), web_search(query),
remember(key, value), recall(key), forget(key), note(content), list_notes,
set_reminder(text, when), list_reminders, clear_reminders

Rules:


*** CRITICAL: MULTI-STEP COMMANDS ***

Agar ek hi command mein 2+ kaam hain (jaise "X karo aur Y karo", "X kholo phir Y bajao"),
to HAMESHA tool = "agent_run" use karo, args = {"goal": "poori command"}.

KABHI bhi multi-step command ke liye single tool (jaise open_app) use mat karo.

MULTI-STEP TRIGGERS:
- "aur" / "and"
- "phir" / "then" / "uske baad"
- 2+ verbs ek hi command mein

EXAMPLES:
- "Chrome kholo aur YouTube pe Python dhundo" -> {"tool": "agent_run", "args": {"goal": "Chrome kholo aur YouTube pe Python dhundo"}}
- "YouTube kholo phir Kesariya bajao" -> {"tool": "agent_run", "args": {"goal": "YouTube kholo phir Kesariya bajao"}}
- "Time batao aur weather batao" -> {"tool": "agent_run", "args": {"goal": "Time batao aur weather batao"}}

SINGLE STEP (normal tools):
- "Time kya hai" -> get_time
- "Chrome kholo" -> open_app
- "Kya yaad hai" -> recall

---

1. IDENTITY (VERY IMPORTANT):
   - "mera naam X hai" -> remember {"key": "user_name", "value": "X"}
   - Never invent a name
   - Never change user_name without user saying so
   - If user asks "mera naam kya hai" and no name -> reply "Boss"

2. MEMORY:
   - "mera naam X hai" -> remember user_name=X
   - "mera naam kya hai" -> recall user_name
   - "mere dost ka naam X" -> remember friend_name=X
   - "mere bhai ka naam X" -> remember brother_name=X
   - "meri behen ka naam X" -> remember sister_name=X
   - "kya yaad hai" -> recall ""
   - "X bhool jao" -> forget X
2. SIMPLE:
   - "time kya hai" -> get_time
   - "chrome kholo" -> open_app chrome
   - "weather X" -> get_weather
   - "screenshot lo" -> take_screenshot
   - "volume badhao" -> volume_up
REMINDERS:
   - "X baje yaad dilana Y" -> set_reminder {"text":"Y","when":"X baje"}
   - "Y minute baad yaad dilana X" -> set_reminder {"text":"X","when":"Y minute baad"}
   - "kal X baje meeting" -> set_reminder {"text":"meeting","when":"kal X baje"}
   - "mere reminders" / "reminders dikhao" -> list_reminders
   - "sab reminders hatao" -> clear_reminders

3. BROWSER (sirf explicit "browser mein", "google pe"):
   - "google pe X" -> browse
4. NORMAL SAWAAL -> tool="none", reply mein jawab

Examples:
"kya kar rahe ho" -> {"tool":"none","args":{},"reply":"Yahin hoon Boss, kya karna hai?"}
"time kya hai" -> {"tool":"get_time","args":{},"reply":""}
"java kya hai" -> {"tool":"none","args":{},"reply":"Java ek programming language hai jo 1995 mein aayi. Android aur enterprise apps mein use hoti hai."}
"mera mood kharab hai" -> {"tool":"none","args":{},"reply":"Kya hua Boss? Share karo, sun raha hoon."}
"""


def _extract_json(text):
    if not text:
        return None
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    if "{" in text and "}" in text:
        start = text.index("{")
        end = text.rindex("}") + 1
        text = text[start:end]
    return text


def _safe_parse(text):
    if not text:
        return None
    try:
        p = json.loads(text)
        if isinstance(p, dict):
            return p
    except Exception:
        pass
    cleaned = _extract_json(text)
    if cleaned and cleaned != text:
        try:
            p = json.loads(cleaned)
            if isinstance(p, dict):
                return p
        except Exception:
            pass
    return None


def _call_groq(messages):
    if not _GROQ:
        return None
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    client = Groq(api_key=key)
    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6,
                max_tokens=500,
                timeout=15,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[groq {model}] {str(e)[:80]}")
            continue
    return None


def _call_ollama(messages):
    if not _OLLAMA:
        return None
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            options={"temperature": 0.6, "num_predict": 500},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        print(f"[ollama] {str(e)[:80]}")
        return None


def ask_nova(user_message, history=None):
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
    messages = [{"role": "system", "content": _get_system_prompt()}]
    for h in history[-8:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_message})

    raw = _call_groq(messages)
    if not raw:
        raw = _call_ollama(messages)
    if not raw:
        return "Boss, dimaag load nahi hua. Thodi der baad try karo."

    parsed = _safe_parse(raw)

    if parsed is None:
        clean = _fix_gender(raw)
        clean = re.sub(r"\[TOOL:\w+\]", "", clean).strip()
        return clean if clean else "Samajh nahi paya."

    tool_name = parsed.get("tool", "none")

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
            return f"Tool {tool_name} fail: {str(e)[:100]}"

    reply = parsed.get("reply", "").strip()
    if reply:
        reply = _fix_gender(reply)
    return reply if reply else "Samajh nahi paya, dobara bolo."
