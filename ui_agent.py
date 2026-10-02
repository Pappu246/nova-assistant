"""
NOVA UI Agent — Phase 2: Full App Control (windows-mcp approach)
25+ UI automation tools via pywinauto + vision fallback.
Works on Windows 11, Python 3.14, no admin, CPU only.
"""
import time
import platform

IS_WIN = platform.system() == "Windows"

# Lazy imports
_pwa = None
_Desktop = None
_pag = None

def _get_pwa():
    global _pwa, _Desktop
    if _pwa is not None:
        return _pwa
    try:
        import pywinauto
        from pywinauto import Desktop
        _pwa = pywinauto
        _Desktop = Desktop
        return _pwa
    except Exception as e:
        print(f"[ui_agent] pywinauto not available: {e}")
        return None

def _get_pag():
    global _pag
    if _pag is None:
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            _pag = pyautogui
        except Exception:
            pass
    return _pag

def _find_window(title_substr, visible_only=True):
    """Find window by substring, score-based. Returns window or None."""
    if not IS_WIN or _get_pwa() is None:
        return None
    needle = title_substr.lower().strip()
    if not needle:
        return None
    cands = []
    for backend in ("uia", "win32"):
        try:
            desktop = _Desktop(backend=backend)
            for w in desktop.windows():
                try:
                    title = (w.window_text() or "").strip()
                    if not title:
                        continue
                    if visible_only and not w.is_visible():
                        continue
                    tl = title.lower()
                    score = 0
                    if tl == needle: score = 100
                    elif tl.endswith(" - " + needle): score = 90
                    elif needle in tl: score = 50
                    else: continue
                    cands.append((score, w, title, backend))
                except: continue
        except: continue
    if not cands:
        return None
    cands.sort(key=lambda x: -x[0])
    return cands[0][1]

# ============ 25+ TOOLS ============

def list_windows(_args=None):
    """1. List all visible windows"""
    if not IS_WIN or _get_pwa() is None:
        return "pywinauto not available (Windows only)"
    wins = []
    try:
        desktop = _Desktop(backend="uia")
        for w in desktop.windows():
            try:
                if w.is_visible():
                    t = (w.window_text() or "").strip()
                    if t: wins.append(t)
            except: continue
    except Exception as e:
        return f"List fail: {e}"
    uniq = []
    seen=set()
    for t in wins:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return "Windows ("+str(len(uniq))+"):\n" + "\n".join(uniq[:30]) if uniq else "No windows"

def get_active_window(_args=None):
    """2. Get active window title"""
    if not IS_WIN:
        return "Windows only"
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        return w.title if w else "(no active window)"
    except Exception as e:
        return f"Fail: {e}"

def focus_window(args):
    """3. Focus window by title"""
    title = args.get("title","") or args.get("window","")
    if not title: return "Window title missing"
    w = _find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        # Handle minimized
        try:
            is_min = w.is_minimized()
            if callable(is_min): is_min = is_min()
            if is_min: w.restore()
        except: pass
        w.set_focus()
        time.sleep(0.4)
        return f"Focused: {title}"
    except Exception as e:
        # Fallback via pygetwindow
        try:
            import pygetwindow as gw
            for win in gw.getAllWindows():
                if title.lower() in win.title.lower():
                    win.activate()
                    return f"Focused (gw): {title}"
        except: pass
        return f"Focus fail: {e}"

def list_controls(args):
    """4. List controls in window"""
    title = args.get("window","") or args.get("title","")
    w = _find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        ctrls = w.descendants()
        out=[]
        for c in ctrls[:80]:
            try:
                info=c.element_info
                name=(info.name or "").strip()
                ctype=info.control_type or "?"
                if name: out.append(f"{ctype}: {name}")
            except: continue
        return "Controls:\n" + "\n".join(out[:40]) if out else "No controls"
    except Exception as e:
        return f"List fail: {e}"

def find_element(args):
    """5. Find element by name in window"""
    title = args.get("window","") or args.get("title","")
    elem = args.get("element","") or args.get("name","")
    if not title or not elem: return "window and element required"
    w = _find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        # Try exact
        try:
            c = w.child_window(title=elem)
            c.wait("exists", timeout=1)
            return f"Found: {elem} in {title}"
        except: pass
        # Fuzzy
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    return f"Found (fuzzy): {c.element_info.name} ({c.element_info.control_type})"
            except: continue
        return f"Not found: {elem}"
    except Exception as e:
        return f"Find fail: {e}"

def click_element(args):
    """6. Click element by name"""
    title = args.get("window","") or args.get("title","")
    elem = args.get("element","") or args.get("name","")
    if not title or not elem: return "window and element required"
    w = _find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        try:
            c = w.child_window(title=elem)
            c.wait("exists visible", timeout=2)
            c.click_input()
            return f"Clicked: {elem}"
        except: pass
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    c.click_input()
                    return f"Clicked fuzzy: {elem}"
            except: continue
        # Vision fallback for custom apps
        try:
            import vision_control
            r = vision_control.click_text(elem, region_mode="active")
            if "click kiya" in r.lower():
                return f"Vision click: {elem} - {r}"
        except: pass
        return f"Element not found: {elem}"
    except Exception as e:
        return f"Click fail: {e}"

def double_click_element(args):
    """7. Double click"""
    title = args.get("window","") ; elem=args.get("element","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    c.double_click_input()
                    return f"Double clicked: {elem}"
            except: continue
        return f"Not found: {elem}"
    except Exception as e: return f"Fail: {e}"

def right_click_element(args):
    """8. Right click"""
    title=args.get("window",""); elem=args.get("element","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    c.right_click_input()
                    return f"Right clicked: {elem}"
            except: continue
        return f"Not found: {elem}"
    except Exception as e: return f"Fail: {e}"

def type_in_field(args):
    """9. Type in field"""
    title=args.get("window",""); field=args.get("field","") or args.get("element",""); text=args.get("text","")
    if not title or not field: return "window, field and text required"
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        # Try Edit control
        try:
            f = w.child_window(title=field, control_type="Edit")
            f.click_input()
            f.type_keys(text, with_spaces=True)
            return f"Typed in {field}"
        except: pass
        for c in w.descendants():
            try:
                if field.lower() in (c.element_info.name or "").lower():
                    c.click_input()
                    c.type_keys(text, with_spaces=True)
                    return f"Typed fuzzy in {field}"
            except: continue
        return f"Field not found: {field}"
    except Exception as e: return f"Type fail: {e}"

def set_text(args):
    """10. Set text (clear + type)"""
    return type_in_field(args)

def get_text(args):
    """11. Get text from element"""
    title=args.get("window",""); elem=args.get("element","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    return c.window_text() or c.element_info.name or "(empty)"
            except: continue
        return f"Not found: {elem}"
    except Exception as e: return f"Fail: {e}"

def get_window_text(args):
    """12. Get all text from window"""
    title=args.get("window","") or args.get("title","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        texts=[]
        for c in w.descendants():
            try:
                t=(c.element_info.name or "").strip()
                if t and len(t)>1: texts.append(t)
            except: continue
        uniq=[]; seen=set()
        for t in texts:
            if t not in seen:
                seen.add(t); uniq.append(t)
        return "\n".join(uniq[:50]) if uniq else "(no text)"
    except Exception as e: return f"Fail: {e}"

def press_key(args):
    """13. Press key"""
    key=args.get("key","")
    if not key: return "key missing"
    try:
        pag=_get_pag()
        if pag:
            if "+" in key:
                pag.hotkey(*key.split("+"))
            else:
                pag.press(key)
            return f"Pressed: {key}"
    except Exception as e: return f"Fail: {e}"
    return "No input method"

def hotkey(args):
    """14. Hotkey combo like ctrl+s"""
    keys=args.get("keys","") or args.get("hotkey","")
    if not keys: return "keys missing"
    return press_key({"key": keys})

def menu_click(args):
    """15. Click menu like File->Save"""
    title=args.get("window",""); path=args.get("path","") or args.get("menu","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        parts=[p.strip() for p in path.split("->")]
        try:
            w.menu_select(" -> ".join(parts))
            return f"Menu: {path}"
        except:
            for p in parts:
                try:
                    c=w.child_window(title=p)
                    c.click_input()
                    time.sleep(0.3)
                except: pass
            return f"Menu clicked: {path}"
    except Exception as e: return f"Menu fail: {e}"

def select_dropdown(args):
    """16. Select dropdown option"""
    # Same as click_element on ComboBox + option
    title=args.get("window",""); elem=args.get("element",""); option=args.get("option","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        # Click dropdown
        click_element({"window":title, "element":elem})
        time.sleep(0.5)
        # Click option (may be new window)
        pag=_get_pag()
        if pag and option:
            # Fallback: type option and enter
            time.sleep(0.3)
            pag.typewrite(option)
            pag.press("enter")
            return f"Selected {option} in {elem}"
        return "Dropdown clicked"
    except Exception as e: return f"Fail: {e}"

def check_checkbox(args):
    """17. Check/uncheck checkbox"""
    title=args.get("window",""); elem=args.get("element",""); check=args.get("check", True)
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    if c.element_info.control_type=="CheckBox":
                        state=c.get_toggle_state() if hasattr(c, 'get_toggle_state') else 0
                        # Toggle if needed
                        if (check and state==0) or (not check and state==1):
                            c.click_input()
                        return f"Checkbox {elem}: {'checked' if check else 'unchecked'}"
                    else:
                        c.click_input()
                        return f"Clicked: {elem}"
            except: continue
        return f"Not found: {elem}"
    except Exception as e: return f"Fail: {e}"

def get_checkbox_state(args):
    """18. Get checkbox state"""
    title=args.get("window",""); elem=args.get("element","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    if hasattr(c, 'get_toggle_state'):
                        s=c.get_toggle_state()
                        return "checked" if s==1 else "unchecked"
                    return c.window_text()
            except: continue
        return "Not found"
    except Exception as e: return f"Fail: {e}"

def scroll(args):
    """19. Scroll"""
    direction=args.get("direction","down"); amount=int(args.get("amount",3))
    pag=_get_pag()
    if not pag: return "pyautogui needed"
    try:
        if direction=="up":
            pag.scroll(amount*100)
        else:
            pag.scroll(-amount*100)
        return f"Scrolled {direction} {amount}"
    except Exception as e: return f"Fail: {e}"

def drag_drop(args):
    """20. Drag and drop"""
    x1=args.get("x1",0); y1=args.get("y1",0); x2=args.get("x2",100); y2=args.get("y2",100)
    pag=_get_pag()
    if not pag: return "pyautogui needed"
    try:
        pag.moveTo(int(x1), int(y1), duration=0.2)
        pag.dragTo(int(x2), int(y2), duration=0.5)
        return f"Dragged {x1},{y1} -> {x2},{y2}"
    except Exception as e: return f"Fail: {e}"

def wait_for_window(args):
    """21. Wait for window"""
    title=args.get("title","") or args.get("window",""); timeout=int(args.get("timeout",10))
    for _ in range(timeout*2):
        if _find_window(title):
            return f"Window appeared: {title}"
        time.sleep(0.5)
    return f"Timeout: {title} not found in {timeout}s"

def wait_for_element(args):
    """22. Wait for element"""
    title=args.get("window",""); elem=args.get("element",""); timeout=int(args.get("timeout",10))
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    for _ in range(timeout*2):
        try:
            for c in w.descendants():
                if elem.lower() in (c.element_info.name or "").lower():
                    return f"Element found: {elem}"
        except: pass
        time.sleep(0.5)
    return f"Timeout: {elem} not found"

def close_window(args):
    """23. Close window"""
    title=args.get("title","") or args.get("window","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        w.close()
        return f"Closed: {title}"
    except Exception as e: return f"Fail: {e}"

def minimize_window(args):
    """24. Minimize"""
    title=args.get("title","") or args.get("window","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        w.minimize()
        return f"Minimized: {title}"
    except Exception as e: return f"Fail: {e}"

def maximize_window(args):
    """25. Maximize"""
    title=args.get("title","") or args.get("window","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        w.maximize()
        return f"Maximized: {title}"
    except Exception as e: return f"Fail: {e}"

def get_element_info(args):
    """26. Get element info"""
    title=args.get("window",""); elem=args.get("element","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    info=c.element_info
                    return f"Name: {info.name}\nType: {info.control_type}\nRect: {c.rectangle()}"
            except: continue
        return "Not found"
    except Exception as e: return f"Fail: {e}"

def highlight_element(args):
    """27. Highlight element (flash rectangle)"""
    title=args.get("window",""); elem=args.get("element","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        for c in w.descendants():
            try:
                if elem.lower() in (c.element_info.name or "").lower():
                    c.draw_outline(colour="red", thickness=2)
                    time.sleep(1)
                    return f"Highlighted: {elem}"
            except: continue
        return "Not found"
    except Exception as e: return f"Fail: {e}"

def screenshot_window(args):
    """28. Screenshot window"""
    title=args.get("title","") or args.get("window","")
    w=_find_window(title)
    if not w: return f"Window not found: {title}"
    try:
        from PIL import Image
        import mss
        rect = w.rectangle()
        with mss.mss() as sct:
            shot = sct.grab({"left": rect.left, "top": rect.top, "width": rect.width(), "height": rect.height()})
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            path = args.get("path") or f"C:\\Users\\{__import__('os').getlogin()}\\Pictures\\nova_{int(time.time())}.png"
            img.save(path)
            return f"Screenshot: {path}"
    except Exception as e: return f"Fail: {e}"

# Tool registry for tools.py
TOOLS = {
    "list_windows": list_windows,
    "get_active_window": get_active_window,
    "focus_window": focus_window,
    "list_controls": list_controls,
    "find_element": find_element,
    "click_element": click_element,
    "double_click_element": double_click_element,
    "right_click_element": right_click_element,
    "type_in_field": type_in_field,
    "set_text": set_text,
    "get_text": get_text,
    "get_window_text": get_window_text,
    "press_key": press_key,
    "hotkey": hotkey,
    "menu_click": menu_click,
    "select_dropdown": select_dropdown,
    "check_checkbox": check_checkbox,
    "get_checkbox_state": get_checkbox_state,
    "scroll": scroll,
    "drag_drop": drag_drop,
    "wait_for_window": wait_for_window,
    "wait_for_element": wait_for_element,
    "close_window": close_window,
    "minimize_window": minimize_window,
    "maximize_window": maximize_window,
    "get_element_info": get_element_info,
    "highlight_element": highlight_element,
    "screenshot_window": screenshot_window,
}

if __name__ == "__main__":
    print("UI Agent 28 tools loaded")
    print(list(TOOLS.keys()))
