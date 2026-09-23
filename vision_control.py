"""
NOVA Vision Control - screen pe text dhundho, click karo.
RapidOCR (ONNX) - no admin, no tesseract, pip-only.
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


def _ocr_screen():
    """OCR the whole screen. Returns list of (text, x, y, w, h)."""
    if not _init():
        return []
    try:
        import numpy as np
        img = _pag.screenshot()
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
            x = int(min(xs))
            y = int(min(ys))
            w = int(max(xs) - x)
            h = int(max(ys) - y)
            out.append((str(text).strip(), x, y, w, h))
        return out
    except Exception as e:
        print("[vision] ocr fail:", str(e)[:80])
        return []


def find_text_on_screen(target, partial=True):
    needle = target.lower().strip()
    results = []
    for (text, x, y, w, h) in _ocr_screen():
        tl = text.lower()
        match = (needle in tl) if partial else (tl == needle)
        if match:
            results.append((text, x, y, w, h))
    return results


def click_text(target, nth=0):
    matches = find_text_on_screen(target)
    if not matches:
        return "Screen pe '" + target + "' nahi mila."
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


def double_click_text(target, nth=0):
    matches = find_text_on_screen(target)
    if not matches:
        return "Nahi mila: " + target
    text, x, y, w, h = matches[nth]
    _pag.doubleClick(x + w // 2, y + h // 2)
    return "Double click: " + text


def right_click_text(target, nth=0):
    matches = find_text_on_screen(target)
    if not matches:
        return "Nahi mila: " + target
    text, x, y, w, h = matches[nth]
    _pag.rightClick(x + w // 2, y + h // 2)
    return "Right click: " + text


def read_screen():
    items = _ocr_screen()
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


def find_all_text():
    items = _ocr_screen()
    seen = set()
    out = []
    for (t, *_ ) in items:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


# ---------- TEST ----------
if __name__ == "__main__":
    print("=" * 55)
    print("  vision_control.py TEST (RapidOCR)")
    print("=" * 55)
    print()
    print("1. OCR current screen...")
    t0 = time.time()
    words = find_all_text()
    dt = time.time() - t0
    print("Found " + str(len(words)) + " text items in " + str(round(dt, 2)) + "s")
    print(", ".join(words[:30]))
    print()
    print("2. Search 'File'...")
    m = find_text_on_screen("File")
    print("Matches:", m[:3])
    print()
    print("Done.")
