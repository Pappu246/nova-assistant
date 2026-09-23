"""
NOVA Vision Agent - screen dekh ke click karo.
Workflow: Screenshot -> Gemini Vision -> Click -> Screenshot verify
"""
import os
import io
import time

try:
    from pywinauto import Desktop
    _PYWINAUTO = True
except Exception:
    _PYWINAUTO = False

try:
    import mss
    _MSS = True
except Exception:
    _MSS = False

try:
    from PIL import Image
    _PIL = True
except Exception:
    _PIL = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    _PYAUTO = True
except Exception:
    _PYAUTO = False

try:
    from google import genai
    from google.genai import types as gtypes
    _GENAI = True
except Exception:
    _GENAI = False


GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
]

# Cache last screenshot for verification
_last_screenshot_hash = None


def _capture():
    """Capture screen and return (PIL_image, bytes_for_gemini, small_size)."""
    if not _MSS or not _PIL:
        return None, None, None
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            # Small copy for Gemini
            small = img.copy()
            small.thumbnail((1280, 720))
            small_size = small.size  # ACTUAL size after thumbnail
            buf = io.BytesIO()
            small.save(buf, format="JPEG", quality=75)
            return img, buf.getvalue(), small_size
    except Exception as e:
        print("[vision] capture fail: " + str(e)[:60])
        return None, None, None


def _find_target_gemini(target_desc, img_bytes, region_hint=None):
    """Ask Gemini Vision to locate target. Returns (x, y) or None."""
    if not _GENAI or not img_bytes:
        return None

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("[vision] GEMINI_API_KEY missing")
        return None

    region_text = ""
    if region_hint:
        region_text = "\nRegion focus: " + region_hint + " (look ONLY in this region)"

    prompt = """Find this UI element on screen: """ + target_desc + region_text + """

Return coordinates as JSON:
{"x_norm": <int 0-1000>, "y_norm": <int 0-1000>, "found": true, "confidence": 0.0-1.0, "reason": "short"}

IMPORTANT: x_norm and y_norm are NORMALIZED coordinates from 0 to 1000.
- x_norm=0 means left edge, x_norm=1000 means right edge
- y_norm=0 means top edge, y_norm=1000 means bottom edge
- Example: element at center of screen -> x_norm=500, y_norm=500
- Example: element at top-left corner -> x_norm=50, y_norm=50
- Example: element in taskbar (bottom) -> y_norm=950

If not found: {"x_norm": 0, "y_norm": 0, "found": false, "reason": "why"}
Return ONLY JSON, nothing else."""

    for model in GEMINI_MODELS:
        try:
            client = genai.Client(api_key=key)
            image_part = gtypes.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            resp = client.models.generate_content(
                model=model,
                contents=[prompt, image_part],
                config=gtypes.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            text = (resp.text or "").strip()
            import json
            # Strip markdown fences if any
            if "```" in text:
                import re
                m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                if m:
                    text = m.group(1)
            data = json.loads(text)
            if data.get("found"):
                return {
                    "x_norm": int(data.get("x_norm", 0)),
                    "y_norm": int(data.get("y_norm", 0)),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reason": str(data.get("reason", "")),
                    "model": model,
                }
            else:
                print("[vision] not found: " + str(data.get("reason", ""))[:60])
                return None
        except Exception as e:
            err = str(e)[:80]
            if any(x in err for x in ["503", "UNAVAILABLE", "429", "overload"]):
                continue
            print("[vision " + model + "] " + err)
            continue
    return None


def _scale_coords(x_small, y_small, small_size, original_size):
    """Scale coords from small image to original screen size."""
    sw, sh = small_size
    ow, oh = original_size
    x = int(x_small * (ow / sw))
    y = int(y_small * (oh / sh))
    return x, y


def _hash_image(img):
    """Quick hash to detect screen change."""
    try:
        small = img.resize((100, 60))
        return hash(small.tobytes())
    except Exception:
        return None






def _activate_taskbar_app(app_name):
    """Find app window by name and activate (bring to front). No clicking needed."""
    if not _PYWINAUTO:
        return False
    try:
        desktop = Desktop(backend="uia")
        windows = desktop.windows()
        for w in windows:
            try:
                title = w.window_text() or ""
                if app_name.lower() in title.lower():
                    if w.is_minimized():
                        w.restore()
                    w.set_focus()
                    print("[pywinauto] Activated: " + title)
                    return True
            except Exception:
                continue
    except Exception as e:
        print("[pywinauto] error: " + str(e)[:60])
    return False


def _capture_taskbar():
    """Capture taskbar region (bottom strip) and upscale 4x for better icon recognition.
    Returns (full_img, upscaled_bytes, crop_box, upscaled_size).
    crop_box = (left, top, right, bottom) in original screen coords.
    """
    if not _MSS or not _PIL:
        return None, None, None, None
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            full_img = Image.frombytes("RGB", shot.size, shot.rgb)

            w, h = full_img.size
            taskbar_h = 90  # capture bottom 90px
            crop_box = (0, h - taskbar_h, w, h)
            crop = full_img.crop(crop_box)

            # Upscale 4x for Gemini to see icons clearly
            upscaled = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)

            buf = io.BytesIO()
            upscaled.save(buf, format="JPEG", quality=85)
            return full_img, buf.getvalue(), crop_box, upscaled.size
    except Exception as e:
        print("[vision] taskbar capture fail: " + str(e)[:60])
        return None, None, None, None


def vision_click(target_desc, dry_run=False):
    """
    Main function: Find target on screen and click it.

    Args:
        target_desc: English description (e.g. "YouTube icon in taskbar")
        dry_run: If True, only find, don't click.

    Returns: dict with {ok, x, y, reason, verified}
    """
    global _last_screenshot_hash

    print("[vision] Looking for: " + target_desc)

    tlow = target_desc.lower()
    use_taskbar_mode = "taskbar" in tlow

    if use_taskbar_mode:
        # Taskbar mode: crop + upscale 4x
        img, img_bytes, crop_box, upscaled_size = _capture_taskbar()
        if not img:
            return {"ok": False, "reason": "taskbar capture failed"}
        print("[vision] Taskbar mode: crop=" + str(crop_box) + " upscaled=" + str(upscaled_size))
    else:
        # Full screen mode
        img, img_bytes, small_size = _capture()
        if not img:
            return {"ok": False, "reason": "screen capture failed"}
        crop_box = None
        upscaled_size = None

    before_hash = _hash_image(img)

    # 2. Find target
    region = "bottom strip of screen (Windows taskbar)" if use_taskbar_mode else None
    found = _find_target_gemini(target_desc, img_bytes, region_hint=region)
    if not found:
        return {"ok": False, "reason": "target not found"}

    # Scale coords based on mode
    if use_taskbar_mode and crop_box:
        # Taskbar mode: normalized (0-1000) -> upscaled coords -> crop coords -> screen coords
        left, top, right, bottom = crop_box
        crop_w = right - left
        crop_h = bottom - top

        # Normalized -> crop-relative pixel (upscaled is 4x)
        x_crop = found["x_norm"] * crop_w / 1000
        y_crop = found["y_norm"] * crop_h / 1000

        # Crop-relative -> screen coords
        x = int(left + x_crop)
        y = int(top + y_crop)

        print("[vision] Taskbar normalized=(" + str(found["x_norm"]) + "," + str(found["y_norm"]) + ")"
              + " -> Screen=(" + str(x) + "," + str(y) + ")")
    elif _PYAUTO:
        # Full screen mode: normalized -> logical screen coords
        try:
            logical_w, logical_h = pyautogui.size()
            x = int(found["x_norm"] * logical_w / 1000)
            y = int(found["y_norm"] * logical_h / 1000)
            print("[vision] Normalized=(" + str(found["x_norm"]) + "," + str(found["y_norm"]) + ")"
                  + " -> Logical=(" + str(x) + "," + str(y) + ") on " + str(logical_w) + "x" + str(logical_h))
        except Exception as e:
            return {"ok": False, "reason": "scaling fail: " + str(e)[:60]}
    else:
        # Fallback: use physical
        x = int(found["x_norm"] * img.size[0] / 1000)
        y = int(found["y_norm"] * img.size[1] / 1000)

    # Sanity check: coords inside screen?
    if _PYAUTO:
        sw, sh = pyautogui.size()
        if x < 0 or x >= sw or y < 0 or y >= sh:
            return {"ok": False, "reason": "coords out of screen: (" + str(x) + "," + str(y) + ")"}

    print("[vision] Found at (" + str(x) + ", " + str(y) + ") conf=" + str(found["confidence"]))

    if dry_run:
        return {"ok": True, "x": x, "y": y, "reason": "dry run", "verified": False}

    if not _PYAUTO:
        return {"ok": False, "x": x, "y": y, "reason": "pyautogui unavailable"}

    # 3. Click
    try:
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        print("[vision] Clicked at (" + str(x) + ", " + str(y) + ")")
    except Exception as e:
        return {"ok": False, "x": x, "y": y, "reason": "click fail: " + str(e)[:60]}

    # 4. Wait and verify (screen should change)
    time.sleep(1.5)
    img_after, _, _ = _capture()
    verified = False
    if img_after:
        after_hash = _hash_image(img_after)
        if before_hash != after_hash:
            verified = True
            print("[vision] Screen changed - verified")
        else:
            print("[vision] Screen unchanged - click may have failed")

    return {
        "ok": True,
        "x": x,
        "y": y,
        "reason": found.get("reason", ""),
        "verified": verified,
        "confidence": found.get("confidence", 0),
    }


# ---- Tool wrapper ----
def tool_vision_click(args):
    """args: {target: str, dry_run: bool}

    Fallback chain for taskbar/app targets:
      1. pywinauto (running app -> activate) - 100% accurate
      2. open_app tool (launch by name) - 100% reliable
      3. Vision click (visual) - last resort
    """
    target = (args.get("target") or "").strip()
    if not target:
        return "Boss, kya click karna hai bolo."
    dry = bool(args.get("dry_run", False))

    tlow = target.lower()

    # --- Layer 1 + 2: Taskbar/App mode ---
    if ("taskbar" in tlow or "icon" in tlow) and not dry:
        import re
        app_name = tlow
        for phrase in [" icon in taskbar", " icon on taskbar", " in taskbar",
                       " on taskbar", " icon in the taskbar", " taskbar icon",
                       " icon", " button", " taskbar"]:
            app_name = app_name.replace(phrase, "")
        app_name = app_name.strip()

        if app_name:
            print("[vision] Layer 1: pywinauto for '" + app_name + "'")
            if _activate_taskbar_app(app_name):
                return "Boss, " + app_name + " activate kar diya (was running)."

            print("[vision] Layer 2: open_app tool for '" + app_name + "'")
            try:
                from tools import open_app
                result = open_app({"app_name": app_name})
                if "nahi mila" not in result.lower() and "fail" not in result.lower():
                    return "Boss, " + app_name + " khol diya (via launcher)."
            except Exception as e:
                print("[vision] open_app fail: " + str(e)[:60])

    # Layer 3: Vision click (last resort)
    print("[vision] Layer 3: Vision click for '" + target + "'")
    result = vision_click(target, dry_run=dry)

    if not result.get("ok"):
        return "Boss, nahi mila: " + result.get("reason", "unknown")

    if dry:
        return "Mil gaya Boss: (" + str(result["x"]) + ", " + str(result["y"]) + ")"

    if result.get("verified"):
        return "Click kar diya Boss, screen change hui."
    return "Click kar diya Boss, par screen same hai."


if __name__ == "__main__":
    print("Testing vision_agent imports...")
    print("  mss:", _MSS)
    print("  PIL:", _PIL)
    print("  pyautogui:", _PYAUTO)
    print("  genai:", _GENAI)
    print()
    print("All ready. Use: vision_click('YouTube icon')")
