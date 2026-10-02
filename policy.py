"""
NOVA Policy - sirf DANGEROUS actions pe confirmation.
Baaki sab auto-execute.
"""
import re
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
    "live_data", "live_news", "live_crypto", "live_stock", "live_weather",
    # Comms - WhatsApp message bhejना SAFE hai (user ne khud bola hota hai)
    "whatsapp_send", "whatsapp_reply",
    "calendar_add", "calendar_list", "calendar_delete", "save_contact",
    # Semantic memory + mood
    "semantic_remember", "semantic_recall",
    "mood_history", "get_mood_history",
}

# ---- ui_* tools (Phase 2 App Control) - sab SAFE ----
_UI_TOOL_BASE = [
    "list_windows", "get_active_window", "focus_window", "list_controls",
    "find_element", "click_element", "double_click_element", "right_click_element",
    "type_in_field", "set_text", "get_text", "get_window_text",
    "press_key", "hotkey", "menu_click", "select_dropdown",
    "check_checkbox", "get_checkbox_state", "scroll", "drag_drop",
    "wait_for_window", "wait_for_element", "close_window",
    "minimize_window", "maximize_window", "get_element_info",
    "highlight_element", "screenshot_window",
    "read_window_text", "click_text", "read_screen", "find_text", "focus_app",
]
SAFE_TOOLS.update("ui_" + n for n in _UI_TOOL_BASE)

# ---- ASK: needs confirmation (system + app control + typing) ----
ASK_TOOLS = {
    "lock_pc",
    "shutdown_pc",
    "open_app",
    "type_text",
    "send_email",   # email bhejne se pehle confirm karo
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
    # ui_* UI-automation tools hamesha safe (read/click/type in UI)
    if tool_name.startswith("ui_"):
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


def _clean_yesno_text(text):
    """Punctuation hatao taaki 'haan!', 'yes.', 'okey?' bhi match ho."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def is_yes(text):
    text = _clean_yesno_text(text)
    if not text:
        return False
    words = set(text.split())
    exact_yes = {"haan", "han", "yes", "yep", "ok", "okay", "theek",
                 "ha", "haa", "chalega", "sure", "okey"}
    if words & exact_yes:
        return True
    phrases = ["kar do", "go ahead", "haan bolo", "haan kar", "theek hai"]
    return any(p in text for p in phrases)


def is_no(text):
    text = _clean_yesno_text(text)
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
