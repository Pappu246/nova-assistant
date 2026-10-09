"""
NOVA Vision Control - screen pe text dhundho, click karo.
RapidOCR (ONNX) - no admin, no tesseract, pip-only.
FIXED: scans active window only by default (not whole screen + terminal).
"""
import os
import time

_OCR = None
_pag = None


def _init():
    global _OCR, _pag
    if _OCR is not None:
        return True
    try:
        from rapidocr_onnxruntime import RapidOCR
        import pyautogui
        _OCR = RapidOCR()
        _pag = pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        print("[vision] RapidOCR loaded")
        return True
    except Exception as e:
        print("[vision] init fail:", str(e)[:120])
        return False


def _active_region():
    """
    Return bbox of active window as (left, top, width, height).
    Fallback to None (full screen) if unavailable.
    """
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        if w is not None:
            # Validate size - avoid tiny or zero windows
            if hasattr(w, 'width') and hasattr(w, 'height'):
                if w.width > 80 and w.height > 80:
                    # Handle minimized or off-screen
                    if w.left > -10000 and w.top > -10000:
                        return (int(w.left), int(w.top), int(w.width), int(w.height))
    except Exception:
        pass
    # Fallback: try pywinauto getActiveWindow is not reliable, use pyautogui size
    return None


def _clamp_capture(bbox):
    """(left, top, w, h) -> (img, offset_x, offset_y) clipped to the screen, or None.

    The origin is clipped first, then the far edges to the screen size, and the
    width/height are recomputed from the CLIPPED edges. A window at x=-8 keeps its
    width minus 8 visible pixels (the old code kept the full width, too wide).
    """
    left, top, w, h = bbox
    try:
        sw, sh = _pag.size()
    except Exception:
        sw, sh = left + w, top + h
    right, bottom = min(sw, left + w), min(sh, top + h)
    left, top = max(0, left), max(0, top)
    w, h = right - left, bottom - top
    if w < 10 or h < 10:
        return None
    return _pag.screenshot(region=(left, top, w, h)), left, top


def _ocr_screen(region_mode="active", region=None):
    """
    OCR screen/window. Returns list of (text, x, y, w, h) in SCREEN coords.
    region_mode:
      - "active" : OCR active window only (default, FIXES terminal-scan bug)
      - "full"   : OCR whole screen (legacy, for debugging)
      - "custom" : use provided region tuple
    region: tuple (left, top, width, height) when region_mode=="custom"
    """
    if not _init():
        return []
    try:
        import numpy as np

        # Determine screenshot region
        if region_mode == "custom" and region is not None:
            # Custom region is honoured or nothing: a bad region never falls back to
            # the full screen (another app's text would be read as WhatsApp's).
            capture = _clamp_capture(tuple(region))
            if capture is None:
                return []
        else:
            bbox = _active_region() if region_mode == "active" else None
            capture = _clamp_capture(bbox) if bbox is not None else None
            if capture is None:
                capture = (_pag.screenshot(), 0, 0)
        img, offset_x, offset_y = capture

        arr = np.array(img)
        result, _ = _OCR(arr)
        if not result:
            return []
        out = []
        for item in result:
            box, text, score = item[0], item[1], item[2]
            if not text or not str(text).strip():
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x = int(min(xs)) + offset_x
            y = int(min(ys)) + offset_y
            w = int(max(xs) - min(xs))
            h = int(max(ys) - min(ys))
            out.append((str(text).strip(), x, y, w, h))
        return out
    except Exception as e:
        print("[vision] ocr fail:", str(e)[:80])
        return []


def find_text_on_screen(target, partial=True, region_mode="active"):
    """Find text on ACTIVE WINDOW by default."""
    needle = target.lower().strip()
    results = []
    for (text, x, y, w, h) in _ocr_screen(region_mode=region_mode):
        tl = text.lower()
        match = (needle in tl) if partial else (tl == needle)
        if match:
            results.append((text, x, y, w, h))
    return results


def find_text_fullscreen(target, partial=True):
    """Legacy: search whole screen (including terminal). Use only for debugging."""
    return find_text_on_screen(target, partial=partial, region_mode="full")


def click_text(target, nth=0, region_mode="active"):
    """Click text in ACTIVE WINDOW by default (fixes terminal-click bug)."""
    matches = find_text_on_screen(target, region_mode=region_mode)
    if not matches:
        # Helpful hint: mention active window mode
        return "Active window pe '" + target + "' nahi mila. (full screen pe bhi try karo? 'full' mode)"
    if nth >= len(matches):
        return "Sirf " + str(len(matches)) + " match mile."
    text, x, y, w, h = matches[nth]
    cx = x + w // 2
    cy = y + h // 2
    try:
        _pag.click(cx, cy)
        time.sleep(0.2)
        return "'" + text + "' click kiya (" + str(cx) + "," + str(cy) + ")"
    except Exception as e:
        return "Click fail: " + str(e)[:60]


def double_click_text(target, nth=0, region_mode="active"):
    matches = find_text_on_screen(target, region_mode=region_mode)
    if not matches:
        return "Nahi mila: " + target
    text, x, y, w, h = matches[nth]
    _pag.doubleClick(x + w // 2, y + h // 2)
    return "Double click: " + text


def right_click_text(target, nth=0, region_mode="active"):
    matches = find_text_on_screen(target, region_mode=region_mode)
    if not matches:
        return "Nahi mila: " + target
    text, x, y, w, h = matches[nth]
    _pag.rightClick(x + w // 2, y + h // 2)
    return "Right click: " + text


def read_screen(region_mode="active"):
    """Read text from active window (default) - avoids terminal leakage."""
    items = _ocr_screen(region_mode=region_mode)
    if not items:
        return "(kuch text nahi mila)"
    lines = [t for (t, *_ ) in items]
    seen = set()
    uniq = []
    for t in lines:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return "\n".join(uniq)


def find_all_text(region_mode="active"):
    items = _ocr_screen(region_mode=region_mode)
    seen = set()
    out = []
    for (t, *_ ) in items:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def get_active_window_info():
    """Debug helper: return active window title + bbox."""
    region = _active_region()
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        title = w.title if w else "(no window)"
    except Exception:
        title = "(unknown)"
    return {"title": title, "region": region}


# ---------- TEST ----------
if __name__ == "__main__":
    print("=" * 55)
    print("  vision_control.py TEST (RapidOCR + Active Window)")
    print("=" * 55)
    print()
    info = get_active_window_info()
    print("Active window:", info["title"])
    print("Region:", info["region"])
    print()
    print("1. OCR active window...")
    t0 = time.time()
    words = find_all_text(region_mode="active")
    dt = time.time() - t0
    print("Found " + str(len(words)) + " text items in " + str(round(dt, 2)) + "s (active window)")
    print(", ".join(words[:30]))
    print()
    print("2. Search 'File' in active window...")
    m = find_text_on_screen("File", region_mode="active")
    print("Matches:", m[:3])
    print()
    print("3. Fullscreen count (for comparison)...")
    full = find_all_text(region_mode="full")
    print("Fullscreen items:", len(full))
    print()
    print("Done.")
