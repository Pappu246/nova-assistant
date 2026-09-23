"""
NOVA Smart Click - Multi-strategy action executor.
Tries shortcuts -> pywinauto -> OCR (active window) -> VLM vision (active window).
FIXED: uses active window OCR first (not whole screen) to avoid terminal clicks.
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

    if "mute" in intent_lower and "unmute" not in intent_lower:
        # Use proper mute via app_control if available
        try:
            import app_control
            app_control.mute()
            return "app_control: mute"
        except Exception:
            pyautogui.press("volumemute")
            return "media key: mute"

    if "unmute" in intent_lower:
        try:
            import app_control
            app_control.unmute()
            return "app_control: unmute"
        except Exception:
            pyautogui.press("volumemute")
            return "media key: unmute (toggle)"

    # Common app shortcuts (when app is focused)
    if "save" in intent_lower:
        pyautogui.hotkey("ctrl", "s")
        return "shortcut: Ctrl+S"

    if "copy" in intent_lower:
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
    Execute an intent using best strategy (cascade).

    Args:
        intent: user's natural command (e.g. "pause karo", "save karo")
        target_hint: optional specific target (e.g. "subscribe button", "Play")

    Returns: dict {ok, method, reason}
    Cascade:
      1. Keyboard shortcuts (fastest)
      2. pywinauto window activation
      3. OCR text click in ACTIVE WINDOW (rapid, avoids terminal)
      4. VLM vision click in ACTIVE WINDOW (handles icons/graphics)
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
                return {"ok": True, "method": "pywinauto", "reason": "activated " + target_hint}
        except Exception:
            pass

    # 3. Try OCR in ACTIVE WINDOW (fixes terminal-scan bug)
    if target_hint:
        try:
            import vision_control
            # Quick OCR check in active window only
            matches = vision_control.find_text_on_screen(target_hint, region_mode="active")
            if matches:
                r = vision_control.click_text(target_hint, region_mode="active")
                if "click kiya" in r.lower():
                    return {"ok": True, "method": "ocr_active", "reason": r}
        except Exception as e:
            print(f"[smart_click] ocr_active fail: {e}")

    # 4. Try VLM vision click in ACTIVE WINDOW (last resort, handles icons)
    if target_hint:
        try:
            from vision_agent import vision_click
            r = vision_click(target_hint, dry_run=False, use_active_window=True)
            if r.get("ok"):
                return {"ok": True, "method": "vision_active", "reason": r.get("reason", "")}
            # Fallback: try fullscreen if active window failed
            r2 = vision_click(target_hint, dry_run=False, use_active_window=False)
            if r2.get("ok"):
                return {"ok": True, "method": "vision_full", "reason": r2.get("reason", "")}
            return {"ok": False, "method": "vision", "reason": r.get("reason", "not found")}
        except Exception as e:
            return {"ok": False, "method": "vision", "reason": str(e)[:60]}

    return {"ok": False, "method": "none", "reason": "no strategy matched"}


if __name__ == "__main__":
    tests = [
        ("pause karo", None),
        ("next gaana", None),
        ("save karo", None),
        ("volume badhao", None),
        ("play button dabao", "Play"),
    ]
    for intent, hint in tests:
        r = smart_action(intent, hint)
        print(f"  {intent:25s} -> {r['method']:12s} | {r['reason']}")
