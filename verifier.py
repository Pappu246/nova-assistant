"""
NOVA Verifier - verify if a step succeeded based on result/observation.
"""
import os


# Heuristic keywords per tool
_SUCCESS_HINTS = {
    "open_app": ["khol", "open", "khul", "launch", "start"],
    "get_time": ["time", ":", "baje"],
    "get_weather": ["degree", "temperature", "temp", "celsius"],
    "play_youtube": ["youtube", "baja", "search", "play", "video", "chala"],
    "youtube_search": ["youtube", "search", "video", "chala", "pehla"],
    "browse": ["success", "playing", "opened", "complete", "khul",
               "search", "youtube", "google", "play", "video",
               "kar liya", "kar diya", "baja diya", "search kar",
               "successfully", "now open", "now playing"],
    "take_screenshot": ["screenshot", "le liya", "capture"],
    "screenshot": ["screenshot", "save", "capture"],
    "volume_up": ["volume", "badha", "increase"],
    "volume_down": ["volume", "kam", "decrease"],
    "volume_mute": ["mute", "band"],
    "volume_unmute": ["unmute", "wapas", "awaaz"],
    "toggle_mute": ["mute", "toggle"],
    "mute": ["mute", "band"],
    "unmute": ["unmute", "wapas"],
    "is_muted": ["muted", "unmuted", "awaaz"],
    "vision_click": ["click", "mil gaya", "kar diya", "activate", "khol diya"],
    "click_text": ["click", "kiya"],
    "read_screen": [],  # Always success if returns text
    "find_on_screen": [],  # Always success if returns
    "smart_action": ["ho gaya", "shortcut", "media", "key"],
    "remember": ["yaad", "save", "rakh"],
    "recall": [],  # Always succeeds if it returns something
    "note": ["note", "save"],
    "list_notes": ["note"],
    "set_reminder": ["reminder", "yaad dila", "set"],
    "list_reminders": ["reminder"],
    "clear_reminders": ["clear", "delete", "hata"],
    "agent_run": ["complete", "success", "done", "ok"],
    "close_app": ["band"],
    "focus_window": ["focus"],
    "type_text": ["type", "kar diya"],
    "press_key": ["key", "bheja"],
    "open_url": ["khol"],
    "web_search": ["search"],
    "google_search": ["search", "google"],
    "live_data": ["live", "price", "news", "result", ":"],
    "live_news": ["news"],
    "live_crypto": ["price", "$", "rs"],
    "live_stock": ["price", "$", "("],
}

_FAILURE_HINTS = [
    "fail", "error", "nahi mila", "not found", "exception",
    "nahi hua", "nahi khul", "could not", "cannot",
]




def _llm_verify(step, result_str):
    """Fallback LLM verification for ambiguous cases."""
    try:
        from groq import Groq
    except Exception:
        return None

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None

    prompt = """You are a strict verifier. Did this tool call succeed?

Tool: """ + str(step.get("tool", "")) + """
Args: """ + str(step.get("args", {})) + """
Result: """ + result_str[:300] + """

Reply EXACTLY one of:
VERDICT: YES
REASON: <one short line>

VERDICT: NO
REASON: <one short line>

Rules:
- Failure keywords (error, fail, nahi mila, exception, cannot, not found) -> NO
- Success (khol diya, ho gaya, search kar liya, opened, launched, playing, complete) -> YES
- Empty/vague/uncertain -> NO
"""

    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=80,
            timeout=12,
        )
        text = (resp.choices[0].message.content or "").strip().upper()
        if "VERDICT: YES" in text or "VERDICT:YES" in text:
            return (True, "LLM verdict: YES")
        if "VERDICT: NO" in text or "VERDICT:NO" in text:
            return (False, "LLM verdict: NO")
    except Exception as e:
        print("[verifier] LLM error: " + str(e)[:60])
    return None


def verify(step, result, use_llm=True):
    """Return (success: bool, reason: str)."""
    if result is None:
        return False, "Koi result nahi aaya"

    result_str = str(result).strip().lower()

    if not result_str:
        return False, "Result khaali hai"

    # Hard failure hints
    for hint in _FAILURE_HINTS:
        if hint in result_str:
            return False, "Result mein failure mila: '" + hint + "'"

    # Tool-specific success hints
    tool = step.get("tool", "")
    hints = _SUCCESS_HINTS.get(tool, [])

    # Special: browse with "successfully" in result - browser-use reports success
    if tool == "browse" and "successfully" in result_str:
        return True, "Browser-use reported success"

    if not hints:
        # Unknown tool - assume success if no failure
        return True, "Result mila"

    for hint in hints:
        if hint in result_str:
            return True, "Success hint mila: '" + hint + "'"

    # No keyword match. Try LLM fallback.
    if use_llm:
        llm_result = _llm_verify(step, result_str)
        if llm_result is not None:
            return llm_result

    # LLM unavailable - lenient default (avoid blocking agent)
    if not hints:
        return True, "No hints, assume success (LLM unavailable)"

    return False, "No success hint (LLM unavailable)"


if __name__ == "__main__":
    # Tests
    tests = [
        ({"tool": "open_app"}, "chrome khol raha hoon", True),
        ({"tool": "open_app"}, "nahi mila", False),
        ({"tool": "get_time"}, "Abhi time hai 5:00 PM", True),
        ({"tool": "get_time"}, "fail hua", False),
        ({"tool": "unknown"}, "kuch bhi", True),
    ]
    for step, result, expected in tests:
        ok, reason = verify(step, result)
        status = "PASS" if ok == expected else "FAIL"
        print(f"  {status}  tool={step['tool']:15}  ok={ok}  reason={reason[:40]}")
    print()
    print("Verifier tests done")
