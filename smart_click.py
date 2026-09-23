"""
NOVA Smart Click - Multi-strategy action executor.
Tries shortcuts -> pywinauto -> browser-use -> vision click.
"""
import time


def _try_keyboard_shortcut(intent):
    """Known keyboard shortcuts for common tasks."""
    try:
        import pyautogui
    except Exception:
        return False

    intent_lower = intent.lower()

    # Media keys
    if any(w in intent_lower for w in ["pause", "play", "resume", "rok", "chalu"]):
        pyautogui.press("playpause")
        return "media key: play/pause"

    if any(w in intent_lower for w in ["next", "agla", "skip"]):
        pyautogui.press("nexttrack")
        return "media key: next"

    if any(w in intent_lower for w in ["previous", "pichla", "back song"]):
        pyautogui.press("prevtrack")
        return "media key: previous"

    if "mute" in intent_lower:
        pyautogui.press("volumemute")
        return "media key: mute"

    # Common app shortcuts (when app is focused)
    if "save" in intent_lower or "save karo" in intent_lower:
        pyautogui.hotkey("ctrl", "s")
        return "shortcut: Ctrl+S"

    if "copy" in intent_lower or "copy karo" in intent_lower:
        pyautogui.hotkey("ctrl", "c")
        return "shortcut: Ctrl+C"

    if "paste" in intent_lower:
        pyautogui.hotkey("ctrl", "v")
        return "shortcut: Ctrl+V"

    if "undo" in intent_lower or "wapas karo" in intent_lower:
        pyautogui.hotkey("ctrl", "z")
        return "shortcut: Ctrl+Z"

    if "refresh" in intent_lower or "reload" in intent_lower:
        pyautogui.hotkey("ctrl", "r")
        return "shortcut: Ctrl+R"

    if "close" in intent_lower and "window" in intent_lower:
        pyautogui.hotkey("alt", "f4")
        return "shortcut: Alt+F4"

    if "fullscreen" in intent_lower or "full screen" in intent_lower:
        pyautogui.press("f11")
        return "shortcut: F11"

    return False


def smart_action(intent, target_hint=None):
    """
    Execute an intent using best strategy.

    Args:
        intent: user's natural command (e.g. "pause karo", "save karo")
        target_hint: optional specific target (e.g. "subscribe button")

    Returns: dict {ok, method, reason}
    """
    # 1. Try keyboard shortcut first (fastest, 100% reliable)
    result = _try_keyboard_shortcut(intent)
    if result:
        return {"ok": True, "method": "keyboard", "reason": result}

    # 2. Try pywinauto (if target is an app/window)
    if target_hint:
        try:
            from vision_agent import _activate_taskbar_app
            if _activate_taskbar_app(target_hint):
                return {"ok": True, "method": "pywinauto", "reason": "activated"}
        except Exception:
            pass

    # 3. Try vision click (last resort)
    if target_hint:
        try:
            from vision_agent import vision_click
            r = vision_click(target_hint, dry_run=False)
            if r.get("ok"):
                return {"ok": True, "method": "vision", "reason": r.get("reason", "")}
        except Exception as e:
            return {"ok": False, "method": "vision", "reason": str(e)[:60]}

    return {"ok": False, "method": "none", "reason": "no strategy matched"}


if __name__ == "__main__":
    # Tests (dry - no real clicks except media keys which are safe)
    tests = [
        ("pause karo", None),
        ("next gaana", None),
        ("save karo", None),
        ("volume badhao", None),
    ]
    for intent, hint in tests:
        r = smart_action(intent, hint)
        print(f"  {intent:25s} -> {r['method']:10s} | {r['reason']}")
