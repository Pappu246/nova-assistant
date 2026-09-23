"""
NOVA Thinking Layer - LLM decides WHAT to do.
No rules. LLM sees tools + user intent, decides: chat / tool / agent.
"""
import os
import json
import re

try:
    from groq import Groq
    _GROQ = True
except Exception:
    _GROQ = False

try:
    from tools import TOOLS
except Exception:
    TOOLS = {}

GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"


# ============ TOOL DESCRIPTIONS ============
# Only descriptions - LLM figures out when to use what.

TOOL_SPECS = {
    "live_data": "Get CURRENT/LIVE info - news, prices, who is X, current events, latest anything. Args: {query: str}. USE FOR: 'kaun hai', 'aaj', 'latest', 'current', 'abhi', 'news', 'price of X', 'kya hua'.",
    "live_news": "Get news headlines. Args: {topic: str (top/cricket/tech/business), limit: int}",
    "live_crypto": "Get crypto price (bitcoin, eth, doge). Args: {coin: str}",
    "live_stock": "Get stock price (tesla, apple, reliance). Args: {symbol: str}",
    "get_time": "Return current time. Args: {}",
    "get_weather": "Get weather. Args: {city: str}",
    "open_app": "Open application/folder/website. Args: {app_name: str}. Examples: chrome, notepad, calculator, downloads, youtube, gmail",
    "take_screenshot": "Take screen screenshot. Args: {}",
    "open_screenshots": "Open screenshots folder. Args: {}",
    "play_youtube": "Play a song/video on YouTube - OPENS FIRST VIDEO DIRECTLY. Args: {query: str}. USE FOR 'gaana bajao', 'song chalao', 'youtube pe X chalao'",
    "browse": "Browser automation - search web, click, fill forms, extract info. Args: {task: str}. Use for multi-step web tasks.",
    "close_browser": "Close the automation browser. Args: {}",
    "volume_up": "Increase system volume. Args: {steps: int}",
    "volume_down": "Decrease system volume. Args: {steps: int}",
    "volume_mute": "EXPLICIT mute (not toggle). Args: {}. Use ONLY for 'mute karo'.",
    "volume_unmute": "EXPLICIT unmute. Args: {}. Use ONLY for 'unmute karo', 'awaaz wapas lao'.",
    "toggle_mute": "Toggle mute/unmute. Args: {}. Use for 'mute toggle karo'.",
    "mute": "Explicit mute. Args: {}. Same as volume_mute.",
    "unmute": "Explicit unmute. Args: {}. Same as volume_unmute.",
    "is_muted": "Check if muted. Args: {}",
    "play_pause": "Toggle play/pause on active media. Args: {}",
    "next_track": "Next media track. Args: {}",
    "prev_track": "Previous media track. Args: {}",
    "lock_pc": "Lock Windows. Args: {}",
    "shutdown_pc": "Shutdown/restart PC. Args: {mode: 'shutdown'|'restart'|'cancel'}",
    "copy_to_clipboard": "Copy text to clipboard. Args: {text: str}",
    "type_text": "Type text into active window. Args: {text: str}",
    "search_file": "Search for file. Args: {name: str, where: 'downloads'|'documents'|'desktop'}",
    "web_search": "Open Google search. Args: {query: str}",
    "remember": "Store a fact. Args: {key: str, value: str}. Example: {key: 'user_name', value: 'Pappu'}",
    "recall": "Retrieve stored fact. Args: {key: str}. Empty key returns all.",
    "forget": "Delete a fact. Args: {key: str}",
    "note": "Save a note. Args: {content: str}",
    "list_notes": "List all notes. Args: {}",
    "set_reminder": "Schedule a reminder. Args: {text: str, when: str}. Example: {text: 'chai peena', when: '5 minute baad'}",
    "list_reminders": "List active reminders. Args: {}",
    "clear_reminders": "Delete all reminders. Args: {}",
    "vision_click": "Find a UI element on screen (ACTIVE WINDOW) and click it. Uses VLM (Groq Vision). Args: {target: str, dry_run: bool}. Use when user says 'X pe click karo', 'play button dabao'.",
    "click_text": "OCR-based click text in ACTIVE WINDOW (not whole screen). Args: {target: str, nth: int}. Faster than vision_click for text.",
    "read_screen": "OCR read ACTIVE WINDOW text. Args: {}",
    "find_on_screen": "Find text in ACTIVE WINDOW. Args: {target: str}",
    "smart_action": "Keyboard shortcuts for common tasks (save, copy, paste, undo, fullscreen). Args: {intent: str}",
}


def _build_tool_list():
    lines = []
    for name, desc in TOOL_SPECS.items():
        if name in TOOLS:
            lines.append("- " + name + ": " + desc)
    return "\n".join(lines)


# ============ SYSTEM PROMPT ============
# ONLY tools + instructions. NO rules. LLM thinks.

SYSTEM_PROMPT_TEMPLATE = """You are NOVA - a smart, loyal AI assistant for Boss (Pappu).

YOUR JOB: Understand what Boss wants, then decide the BEST way to help.



*** LIVE DATA - VERY IMPORTANT ***
- "Bihar CM kaun hai", "Modi ji kaun hai", "aaj ka PM kaun hai"
  -> live_data {"query": "<full question>"}
- "aaj ki news", "latest news", "cricket news"
  -> live_news {"topic": "top"} or {"topic": "cricket"}
- "bitcoin price", "ethereum ka rate", "doge coin"
  -> live_crypto {"coin": "bitcoin"}
- "tesla stock", "apple share price", "reliance stock"
  -> live_stock {"symbol": "tesla"}
- "latest iPhone price", "aaj ka mausam", "current events"
  -> live_data {"query": "<full question>"}

RULE: Agar user "kaun hai", "aaj", "latest", "current", "abhi",
"news", "price", "rate", "score", "kya hua" jaise words bole,
to LIVE DATA tools use karo - apne training data se mat bolo.

NEVER answer current events from training data - it's outdated.

Reply in Hinglish (Hindi + English mix). You are MALE - use "kar raha hoon", "bol raha hoon", "sun raha hoon" (never "rahi"). Keep replies SHORT (1-2 sentences) unless Boss asks for detail.

You have THREE ways to respond. Choose ONE:

1. CHAT - casual conversation, questions, opinions, explanations.
   Output: {"mode": "chat", "reply": "<your Hinglish reply>"}

2. TOOL - single specific action needed.
   Output: {"mode": "tool", "tool": "<tool_name>", "args": {...}}

3. AGENT - complex goal needing MULTIPLE steps (website banao, multi-search karo, plan karo).
   Output: {"mode": "agent", "goal": "<the full goal>"}

AVAILABLE TOOLS:
{tool_list}



*** STATIC vs LIVE - SABSE ZAROORI RULE ***

Tumhare paas apna KNOWLEDGE hai (training data). Aur "live_data" tool hai.

LIVE_DATA tool SIRF in cases mein:
- "aaj ki news", "latest news"       -> live_news
- "bitcoin/ethereum/crypto price"     -> live_crypto
- "tesla/apple/reliance stock price"  -> live_stock
- "aaj ka mausam / weather"           -> get_weather (already have)
- "aaj ka cricket score", "match score" -> live_news
- "latest iPhone 16 price"            -> live_data
- "Bihar CM kaun hai ABHI / 2026"     -> live_data (recently changed)
- "America ka president kaun hai ABHI" -> live_data

STATIC (apni knowledge se bolo - tool mat use karo):
- "America ka president kaun hai"     -> CHAT reply: "Joe Biden/Trump" (apna data)
- "Taj Mahal kahan hai"                -> CHAT reply
- "Java kya hai"                       -> CHAT reply
- "Bharat ka PM kaun hai"              -> CHAT reply: "Narendra Modi"
- "2+2 kitna hai"                      -> CHAT reply
- "Python seekhne ka tarika"           -> CHAT reply

DECISION:
1. Agar sawal TIME-SENSITIVE hai (aaj, abhi, latest, price, score, breaking) -> LIVE
2. Agar sawal GENERAL knowledge hai (kaun hai, kya hai, kahan hai, history) -> CHAT
3. Kabhi bhi general sawal pe live_data tool mat use karo - tumhe already pata hai

EXAMPLE:
User: "america ke president kaun hai"
NOVA: {"mode": "chat", "reply": "America ke current President Donald Trump hain (2025 se)."}

User: "aaj america ki news batao"
NOVA: {"mode": "tool", "tool": "live_news", "args": {"topic": "world"}}

User: "bitcoin price kya hai"
NOVA: {"mode": "tool", "tool": "live_crypto", "args": {"coin": "bitcoin"}}

User: "bharat ke PM kaun hai"
NOVA: {"mode": "chat", "reply": "Bharat ke Prime Minister Narendra Modi hain."}


DECISION EXAMPLES:

User: "kya kar rahe ho"          -> {{"mode": "chat", "reply": "Yahin hoon Boss, kya karna hai?"}}
User: "time kya hai"             -> {{"mode": "tool", "tool": "get_time", "args": {{}}}}
User: "chrome kholo"             -> {{"mode": "tool", "tool": "open_app", "args": {{"app_name": "chrome"}}}}
User: "mera naam kya hai"        -> {{"mode": "tool", "tool": "recall", "args": {{"key": "user_name"}}}}
User: "mera naam Pappu hai"      -> {{"mode": "tool", "tool": "remember", "args": {{"key": "user_name", "value": "Pappu"}}}}
User: "screen dekh sakte ho?"    -> {{"mode": "chat", "reply": "Nahi Boss, main live screen nahi dekh sakta. Sirf commands sun sakta hoon."}}
User: "screenshot lo"            -> {{"mode": "tool", "tool": "take_screenshot", "args": {{}}}}
User: "portfolio website banao"  -> {{"mode": "agent", "goal": "Create a portfolio website with dark theme, about section, projects, contact"}}
User: "youtube pe python dhundo aur pehla video chalao" -> {{"mode": "agent", "goal": "Open YouTube, search python, play first video"}}
User: "5 minute baad chai yaad dilana" -> {{"mode": "tool", "tool": "set_reminder", "args": {{"text": "chai", "when": "5 minute baad"}}}}
User: "java kya hai"             -> {{"mode": "chat", "reply": "Java ek programming language hai jo 1995 mein aayi. Android apps aur enterprise software mein use hoti hai."}}
User: "save karo"                -> {{"mode": "tool", "tool": "smart_action", "args": {{"intent": "save"}}}}

CRITICAL RULES FOR OUTPUT:
- Reply MUST be valid JSON only. No markdown, no extra text.
- Use ONLY tool names from the list above.
- If unsure between chat and tool - prefer chat first, don't force tool calls.
- Boss might speak Hindi, English, Hinglish, or mix - understand all.

Now respond to Boss's message with a single JSON object."""


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
    try:
        return json.loads(text)
    except Exception:
        return None


def _get_memory_snippet():
    try:
        import memory
        ctx = memory.get_memory_context(max_facts=8, max_convos=2)
        if ctx:
            return "\n\n[Memory about Boss]:\n" + ctx
    except Exception:
        pass
    return ""


def think(user_message, history=None, strict_json=True):
    """
    Main thinking function. Returns decision dict.
    Returns: {"mode": "chat", "reply": "..."}
          or {"mode": "tool", "tool": "...", "args": {...}}
          or {"mode": "agent", "goal": "..."}
          or {"mode": "error", "reply": "..."}
    """
    if not _GROQ:
        return {"mode": "error", "reply": "Groq not available"}

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return {"mode": "error", "reply": "GROQ_API_KEY missing"}

    tool_list = _build_tool_list()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{tool_list}", tool_list)
    # Inject long-term memory (Issue 2 fix)
    mem = _get_memory_snippet()
    if mem:
        system_prompt += mem

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for h in history[-6:]:
            messages.append(h)
    messages.append({"role": "user", "content": user_message})

    client = Groq(api_key=key)

    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"} if strict_json else None,
                timeout=20,
            )
            raw = resp.choices[0].message.content.strip()
            decision = _extract_json(raw)

            if decision is None:
                # LLM ne text diya, JSON nahi - usko chat reply maan lo
                return {"mode": "chat", "reply": raw[:400]}

            mode = decision.get("mode", "chat")
            if mode not in ("chat", "tool", "agent"):
                mode = "chat"

            if mode == "tool":
                tool = decision.get("tool", "")
                if tool not in TOOLS:
                    # Invalid tool - fallback to chat
                    return {
                        "mode": "chat",
                        "reply": decision.get("reply", "Samajh nahi aaya, dobara bolo."),
                    }
                return {
                    "mode": "tool",
                    "tool": tool,
                    "args": decision.get("args", {}) or {},
                }

            if mode == "agent":
                return {
                    "mode": "agent",
                    "goal": decision.get("goal", user_message),
                }

            return {
                "mode": "chat",
                "reply": decision.get("reply", "Samajh nahi aaya."),
            }

        except Exception as e:
            err = str(e)[:100]
            print("[think] " + model + " fail: " + err)
            continue

    return {"mode": "error", "reply": "Brain fail, thodi der baad try karo."}


if __name__ == "__main__":
    # Tests
    tests = [
        "time kya hai",
        "kya kar rahe ho",
        "mera naam kya hai",
        "chrome kholo",
        "screen dekh sakte ho?",
        "youtube pe python dhundo aur pehla video chalao",
        "java kya hai",
        "screenshot lo",
        "save karo",
    ]

    for t in tests:
        print("\n>>> " + t)
        r = think(t, history=[])
        print("   " + str(r))
