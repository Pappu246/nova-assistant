"""
NOVA Policy - sirf DANGEROUS actions pe confirmation.
Baaki sab auto-execute.
"""
import threading

SAFE = "safe"
ASK = "ask"
BLOCK = "block"


# ---- SAFE: sab normal kaam (auto-execute) ----
SAFE_TOOLS = {
    "get_time", "get_weather",
    "open_screenshots", "close_browser",
    "take_screenshot", "play_youtube", "play_spotify", "browse",
    "volume_up", "volume_down", "volume_mute", "volume_unmute", "toggle_mute",
    "mute", "unmute", "is_muted",
    "play_pause", "next_track", "prev_track",
    "copy_to_clipboard",
    "search_file", "web_search",
    "remember", "recall", "forget", "note", "list_notes",
    "set_reminder", "list_reminders", "clear_reminders",
    "vision_click", "smart_action",
    "click_text", "double_click_text", "right_click_text", "read_screen", "find_on_screen",
    "read_screen_full", "find_fullscreen",
    "close_app", "focus_window", "list_windows", "press_key",
    "youtube_search", "google_search", "open_url", "screenshot",
    "live_data", "live_news", "live_crypto", "live_stock",
}

# ---- ASK: needs confirmation (system + app control + typing) ----
ASK_TOOLS = {
    "lock_pc",
    "shutdown_pc",
    "open_app",
    "type_text",
}

# ---- BLOCK patterns (hard block) ----
BLOCK_PATTERNS = [
    "rm -rf", "format c:", "del /f /s /q c:", "wipe", "delete_all",
]

_pending = {}
_lock = threading.Lock()


def classify(tool_name, args=None):
    tool_name = (tool_name or "").strip().lower()

    if args:
        args_str = str(args).lower()
        for p in BLOCK_PATTERNS:
            if p in args_str:
                return BLOCK

    if tool_name in ASK_TOOLS:
        return ASK
    if tool_name in SAFE_TOOLS:
        return SAFE
    # Unknown tool - default ASK (safe default for tests / safety)
    return ASK


def requires_confirmation(tool_name, args=None):
    return classify(tool_name, args) == ASK


def is_blocked(tool_name, args=None):
    return classify(tool_name, args) == BLOCK


def make_confirmation_message(tool_name, args):
    # Build friendly message that includes args details for test expectations
    if tool_name == "open_app":
        app = ""
        try:
            app = str(args.get("app_name", "")).strip() if isinstance(args, dict) else str(args)
        except Exception:
            app = str(args)
        return (app + " kholna hai?" if app else "App kholna hai?")
    if tool_name == "type_text":
        txt = ""
        try:
            txt = str(args.get("text", "")).strip()[:30] if isinstance(args, dict) else ""
        except Exception:
            pass
        return (f"'{txt}' type karna hai?" if txt else "Type karna hai?")
    friendly = {
        "lock_pc": "PC lock karna hai?",
        "shutdown_pc": ("restart karna hai?" if "restart" in str(args).lower()
                        else "shutdown karna hai? (PC band hoga)"),
    }
    if tool_name in friendly:
        return friendly[tool_name]
    # Generic: include args if present so tests see details
    if args:
        return f"{tool_name} {args} chalana hai?"
    return friendly.get(tool_name, tool_name + " chalana hai?")


def set_pending(tool_name, args):
    with _lock:
        _pending["tool"] = tool_name
        _pending["args"] = args


def get_pending():
    with _lock:
        return dict(_pending) if _pending else None


def clear_pending():
    with _lock:
        _pending.clear()


def is_yes(text):
    text = (text or "").lower().strip()
    if not text:
        return False
    words = set(text.split())
    exact_yes = {"haan", "han", "yes", "yep", "ok", "okay", "theek",
                 "ha", "chalega", "sure", "okey"}
    if words & exact_yes:
        return True
    phrases = ["kar do", "go ahead", "haan bolo", "haan kar", "theek hai"]
    return any(p in text for p in phrases)


def is_no(text):
    text = (text or "").lower().strip()
    if not text:
        return False
    words = set(text.split())
    exact_no = {"nahi", "nah", "no", "nope", "cancel", "ruko", "chhodo"}
    if words & exact_no:
        return True
    phrases = ["mat karo", "band karo", "rehne do", "nahi chahiye"]
    return any(p in text for p in phrases)


if __name__ == "__main__":
    for t in ["open_app", "get_time", "chrome kholo",
              "shutdown_pc", "lock_pc", "vision_click",
              "browse", "type_text"]:
        print("  " + t.ljust(20) + " -> " + classify(t))
