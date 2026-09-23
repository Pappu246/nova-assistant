"""
NOVA UI Control - Windows accessibility API (pywinauto).
Real app control: buttons, fields, menus, forms - naam se dhundho, click/type karo.
"""
import time
import platform

IS_WIN = platform.system() == "Windows"

_pwa = None
_Desktop = None


def _get_pwa():
    global _pwa, _Desktop
    if _pwa is None:
        try:
            import pywinauto
            from pywinauto import Desktop
            _pwa = pywinauto
            _Desktop = Desktop
        except Exception as e:
            print("[ui_control] pywinauto fail:", str(e)[:80])
    return _pwa


def _get_window(title_substr):
    """Find window. Exact match first, then substring. Visible only."""
    if not IS_WIN or _get_pwa() is None:
        return None

    needle = title_substr.lower().strip()
    candidates = []

    for backend in ("uia", "win32"):
        try:
            desktop = _Desktop(backend=backend)
            for w in desktop.windows():
                try:
                    title = (w.window_text() or "").strip()
                    if not title:
                        continue
                    if not w.is_visible():
                        continue
                    tl = title.lower()
                    if tl == needle:
                        score = 100
                    elif tl.endswith(" - " + needle):
                        score = 90
                    elif tl.startswith(needle + " "):
                        score = 80
                    elif needle in tl:
                        score = 50
                    else:
                        continue
                    candidates.append((score, w, title, backend))
                except Exception:
                    continue
        except Exception:
            continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: -x[0])
    best = candidates[0]
    print("[ui_control] matched: '" + best[2] + "' (" + best[3] + ", score " + str(best[0]) + ")")
    return best[1]


def debug_windows():
    """Show all visible windows - for debugging match failures."""
    if not IS_WIN or _get_pwa() is None:
        return "pywinauto nahi hai."
    out = []
    for backend in ("uia",):
        try:
            desktop = _Desktop(backend=backend)
            for w in desktop.windows():
                try:
                    if w.is_visible():
                        t = (w.window_text() or "").strip()
                        if t:
                            out.append(t)
                except Exception:
                    continue
        except Exception:
            continue
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return "Visible windows (" + str(len(uniq)) + "):\n" + "\n".join(uniq[:30])


def list_controls(window_title):
    """List all buttons/fields/menus in a window."""
    if not IS_WIN:
        return "Sirf Windows pe."
    w = _get_window(window_title)
    if w is None:
        return "Window nahi mili: " + window_title
    try:
        # Get all descendants with control identifiers
        ctrls = w.descendants()
        out = []
        for c in ctrls[:80]:
            try:
                info = c.element_info
                name = (info.name or "").strip()
                ctype = info.control_type or "?"
                if name:
                    out.append(ctype + ": " + name)
            except Exception:
                continue
        if not out:
            return "Koi control nahi mila is window mein."
        return "Controls (" + str(len(out)) + "):\n" + "\n".join(out[:40])
    except Exception as e:
        return "List fail: " + str(e)[:80]


def click_element(window_title, element_name, element_type=None):
    """Click a button/menu/checkbox by its name."""
    if not IS_WIN:
        return "Sirf Windows pe."
    w = _get_window(window_title)
    if w is None:
        return "Window nahi mili: " + window_title
    try:
        # Try by title (works for buttons)
        try:
            ctrl = w.child_window(title=element_name)
            ctrl.wait("exists visible", timeout=2)
            ctrl.click_input()
            return "'" + element_name + "' click kar diya."
        except Exception:
            pass

        # Try by control_type + title
        if element_type:
            try:
                ctrl = w.child_window(title=element_name, control_type=element_type)
                ctrl.click_input()
                return "'" + element_name + "' click kiya (" + element_type + ")"
            except Exception:
                pass

        # Fallback: search descendants
        for c in w.descendants():
            try:
                if element_name.lower() in (c.element_info.name or "").lower():
                    c.click_input()
                    return "'" + element_name + "' click kiya (fuzzy match)"
            except Exception:
                continue
        return "Element nahi mila: " + element_name
    except Exception as e:
        return "Click fail: " + str(e)[:80]


def type_in_field(window_title, field_name, text):
    """Type text into a named input field."""
    if not IS_WIN:
        return "Sirf Windows pe."
    w = _get_window(window_title)
    if w is None:
        return "Window nahi mili: " + window_title
    try:
        # Try Edit control
        try:
            field = w.child_window(title=field_name, control_type="Edit")
            field.click_input()
            field.type_keys(text, with_spaces=True)
            return "'" + field_name + "' mein type kar diya."
        except Exception:
            pass

        # Try any control with that name
        for c in w.descendants():
            try:
                if field_name.lower() in (c.element_info.name or "").lower():
                    c.click_input()
                    c.type_keys(text, with_spaces=True)
                    return "'" + field_name + "' mein type kiya (fuzzy)"
            except Exception:
                continue
        return "Field nahi mila: " + field_name
    except Exception as e:
        return "Type fail: " + str(e)[:80]


def menu_click(window_title, menu_path):
    """Click menu item like 'File->Save' or 'File->Open'."""
    if not IS_WIN:
        return "Sirf Windows pe."
    w = _get_window(window_title)
    if w is None:
        return "Window nahi mili: " + window_title
    try:
        parts = [p.strip() for p in menu_path.split("->")]
        m = w.menu_select(" -> ".join(parts))
        return "Menu click: " + menu_path
    except Exception as e:
        # Fallback: try clicking menu bar items one by one
        try:
            parts = [p.strip() for p in menu_path.split("->")]
            for p in parts:
                ctrl = w.child_window(title=p)
                ctrl.click_input()
                time.sleep(0.3)
            return "Menu path click: " + menu_path
        except Exception:
            return "Menu fail: " + str(e)[:80]


def read_window_text(window_title):
    """Read all visible text from a window (for reading dialogs/errors)."""
    if not IS_WIN:
        return "Sirf Windows pe."
    w = _get_window(window_title)
    if w is None:
        return "Window nahi mili: " + window_title
    try:
        texts = []
        for c in w.descendants():
            try:
                info = c.element_info
                t = (info.name or "").strip()
                if t and len(t) > 1:
                    texts.append(t)
            except Exception:
                continue
        # unique preserving order
        seen = set()
        uniq = []
        for t in texts:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        return "Window text:\n" + "\n".join(uniq[:50])
    except Exception as e:
        return "Read fail: " + str(e)[:80]


def get_active_window():
    """Get title of currently focused window."""
    if not IS_WIN:
        return ""
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        return w.title if w else ""
    except Exception:
        return ""


# ---------- TEST ----------
if __name__ == "__main__":
    print("=" * 55)
    print("  ui_control.py TEST")
    print("=" * 55)
    print()
    print("Active window:", get_active_window())
    print()
    print("--- Opening notepad ---")
    import subprocess, time as t
    subprocess.Popen(["notepad"])
    t.sleep(2)
    print()
    print("--- Listing controls ---")
    print(list_controls("Notepad")[:400])
    print()
    print("--- Reading window text ---")
    print(read_window_text("Notepad")[:300])
    print()
    print("Done. Notepad manually close karo.")
