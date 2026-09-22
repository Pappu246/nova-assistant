"""
NOVA Policy Layer - risk classification before tool execution.

Rules:
- SAFE tools: auto-execute
- ASK tools: require user confirmation
- BLOCK tools: never execute
"""
import threading

# ---- Risk Levels ----
SAFE = "safe"
ASK = "ask"
BLOCK = "block"

# ---- Tool Classification ----
TOOL_POLICY = {
    # SAFE - reading info, non-destructive
    "get_time": SAFE,
    "get_weather": SAFE,
    "recall": SAFE,
    "list_notes": SAFE,
    "list_reminders": SAFE,
    "list_facts": SAFE,
    "take_screenshot": SAFE,
    "open_screenshots": SAFE,
    "web_search": SAFE,
    "search_file": SAFE,
    "volume_up": SAFE,
    "volume_down": SAFE,
    "volume_mute": SAFE,
    "play_pause": SAFE,
    "next_track": SAFE,
    "prev_track": SAFE,
    "play_youtube": SAFE,
    "play_spotify": SAFE,
    "remember": SAFE,
    "note": SAFE,

    # ASK - sensitive but reversible
    "open_app": ASK,
    "vision_click": ASK,   # Clicks on screen, needs confirm        # Could open anything
    "browse": ASK,          # Browser automation may fill forms
    "type_text": ASK,       # Types into apps
    "copy_to_clipboard": ASK,
    "lock_pc": ASK,
    "forget": ASK,          # Memory deletion
    "clear_reminders": ASK,
    "close_browser": ASK,
    "set_reminder": SAFE,   # Safe - just schedules

    # ASK - system level
    "shutdown_pc": ASK,
}

# ---- Blocked patterns (hard block) ----
BLOCK_PATTERNS = [
    "rm -rf",
    "format c:",
    "del /f /s /q c:",
    "wipe",
    "delete_all",
]

# ---- Pending confirmations ----
_pending = {}
_lock = threading.Lock()


def classify(tool_name, args=None):
    """Return risk level for a tool call."""
    tool_name = (tool_name or "").strip().lower()

    # Check block patterns in args
    if args:
        args_str = str(args).lower()
        for pattern in BLOCK_PATTERNS:
            if pattern in args_str:
                return BLOCK

    return TOOL_POLICY.get(tool_name, ASK)  # Unknown tools = ASK


def requires_confirmation(tool_name, args=None):
    """Return True if tool needs user confirmation."""
    level = classify(tool_name, args)
    return level == ASK


def is_blocked(tool_name, args=None):
    """Return True if tool is hard-blocked."""
    level = classify(tool_name, args)
    return level == BLOCK


def make_confirmation_message(tool_name, args):
    """Human-readable confirmation prompt."""
    friendly = {
        "open_app": f"'{args.get('app_name', 'app')}' kholna hai?",
        "vision_click": f"Screen pe '{args.get('target', 'kya')}' pe click karna hai?",
        "browse": f"Browser automation chalayein? Task: {args.get('task', 'unknown')}",
        "type_text": f"Type karna hai: '{args.get('text', '')[:30]}'?",
        "lock_pc": "PC lock karna hai?",
        "shutdown_pc": f"{'restart' if 'restart' in str(args).lower() else 'shutdown' if 'shutdown' in str(args).lower() or 'band' in str(args).lower() else 'PC band ya restart'} karna hai?",
        "forget": f"'{args.get('key', 'kya')}' bhoolna hai?",
        "clear_reminders": "Saare reminders hata denge?",
        "close_browser": "Browser band karna hai?",
        "copy_to_clipboard": f"Clipboard mein copy karna hai?",
    }
    return friendly.get(tool_name, f"{tool_name} chalana hai?")


def set_pending(tool_name, args):
    """Store pending confirmation."""
    with _lock:
        _pending["tool"] = tool_name
        _pending["args"] = args


def get_pending():
    """Get pending confirmation."""
    with _lock:
        return dict(_pending) if _pending else None


def clear_pending():
    """Clear pending confirmation."""
    with _lock:
        _pending.clear()


def is_yes(text):
    """Check if user confirmed."""
    text = (text or "").lower().strip()
    yes_words = ["haan", "han", "yes", "yep", "ya", "ok", "okay", "theek",
                 "ha", "chalega", "kar do", "kar", "go ahead", "sure"]
    return any(w in text for w in yes_words)


def is_no(text):
    """Check if user declined."""
    text = (text or "").lower().strip()
    no_words = ["nahi", "nah", "no", "nope", "cancel", "mat karo", "ruko",
                "band karo", "chhodo", "rehne do"]
    return any(w in text for w in no_words)


if __name__ == "__main__":
    # Tests
    print("get_time:", classify("get_time"))
    print("shutdown_pc:", classify("shutdown_pc"))
    print("open_app chrome:", classify("open_app", {"app_name": "chrome"}))
    print()
    print("requires_confirmation get_time:", requires_confirmation("get_time"))
    print("requires_confirmation shutdown_pc:", requires_confirmation("shutdown_pc"))
    print()
    print("is_blocked rm -rf:", is_blocked("type_text", {"text": "rm -rf /"}))
    print()
    print("Message:", make_confirmation_message("open_app", {"app_name": "chrome"}))
    print("Message:", make_confirmation_message("shutdown_pc", {"mode": "shutdown"}))
    print()
    print("is_yes 'haan':", is_yes("haan"))
    print("is_no 'nahi':", is_no("nahi"))
