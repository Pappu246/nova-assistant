"""
NOVA Vision Agent - screen dekh ke click karo.
Workflow: Screenshot -> Vision LLM -> Click -> Verify
FIXED: uses active window region by default (not whole screen + terminal).
Supports Groq Vision + Gemini Vision with fallback.
"""
import os
import io
import time
import base64
import json

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
    pyautogui.FAILSAFE = True
    _PYAUTO = True
except Exception:
    _PYAUTO = False

try:
    from google import genai
    from google.genai import types as gtypes
    _GENAI = True
except Exception:
    _GENAI = False

try:
    from groq import Groq
    _GROQ = True
except Exception:
    _GROQ = False

GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
]

GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.2-90b-vision-preview",
    "llama-3.2-11b-vision-preview",
]

_last_screenshot_hash = None


# ---------- Active window region ----------

def _active_region_mss():
    """Return active window bbox as (left, top, width, height) or None."""
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        if w is not None and hasattr(w, 'width') and hasattr(w, 'height'):
            if w.width > 80 and w.height > 80:
                if w.left > -10000 and w.top > -10000:
                    return (int(w.left), int(w.top), int(w.width), int(w.height))
    except Exception:
        pass
    return None


def _capture_full():
    """Capture full screen (fallback). Returns (PIL_image, bytes_for_llm, small_size)."""
    if not _MSS or not _PIL:
        return None, None, None
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            small = img.copy()
            small.thumbnail((1280, 720))
            small_size = small.size
            buf = io.BytesIO()
            small.save(buf, format="JPEG", quality=75)
            return img, buf.getvalue(), small_size
    except Exception as e:
        print("[vision] capture fail: " + str(e)[:60])
        return None, None, None


def _capture_active():
    """Capture ACTIVE WINDOW only (FIXES terminal-scan bug). Returns (full_img, bytes, small_size, crop_box)."""
    if not _MSS or not _PIL:
        return None, None, None, None
    bbox = _active_region_mss()
    if bbox is None:
        # No active window -> fallback to full
        img, b, s = _capture_full()
        if img is None:
            return None, None, None, None
        # No crop box, full screen
        return img, b, s, None
    left, top, w, h = bbox
    try:
        with mss.mss() as sct:
            # mss grab expects dict with left, top, width, height
            # need to clamp to monitors
            monitor = {"left": left, "top": top, "width": w, "height": h}
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            # Small copy for LLM
            small = img.copy()
            small.thumbnail((1280, 720))
            small_size = small.size
            buf = io.BytesIO()
            small.save(buf, format="JPEG", quality=75)
            # For compatibility, also capture full screen hash? No, we return active crop
            # We'll create a full_img placeholder as active img for hash comparison
            return img, buf.getvalue(), small_size, bbox
    except Exception as e:
        print("[vision] active capture fail: " + str(e)[:60])
        return _capture_full() + (None,)


def _capture():
    """Legacy capture: now defaults to ACTIVE WINDOW if available."""
    # Try active first
    result = _capture_active()
    if result[0] is not None:
        # Unpack: result is (img, bytes, size, bbox) for active, or (img, bytes, size) for full
        if len(result) == 4:
            img, b, s, bbox = result
            if bbox is not None:
                # Return as 3-tuple for legacy callers but store bbox globally? We need to handle.
                # For backward compat, return full-like but we also need bbox for coordinate mapping.
                # We'll store bbox in a global for later use.
                _capture._last_bbox = bbox
                return img, b, s
            else:
                _capture._last_bbox = None
                return img, b, s
        else:
            _capture._last_bbox = None
            return result
    _capture._last_bbox = None
    return _capture_full()
_capture._last_bbox = None


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
            taskbar_h = 90
            crop_box = (0, h - taskbar_h, w, h)
            crop = full_img.crop(crop_box)
            upscaled = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
            buf = io.BytesIO()
            upscaled.save(buf, format="JPEG", quality=85)
            return full_img, buf.getvalue(), crop_box, upscaled.size
    except Exception as e:
        print("[vision] taskbar capture fail: " + str(e)[:60])
        return None, None, None, None


def _hash_image(img):
    try:
        small = img.resize((100, 60))
        return hash(small.tobytes())
    except Exception:
        return None


# ---------- Vision LLM helpers ----------

def _find_target_groq(target_desc, img_bytes, region_hint=None):
    """Ask Groq Vision to locate target. Returns dict or None."""
    if not _GROQ or not img_bytes:
        return None
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        import base64
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        data_url = "data:image/jpeg;base64," + b64
    except Exception:
        return None

    region_text = ""
    if region_hint:
        region_text = "\nRegion focus: " + region_hint + " (look ONLY in this region)"

    prompt = """Find this UI element on screen: """ + target_desc + region_text + """

Return coordinates as JSON:
{"x_norm": <int 0-1000>, "y_norm": <int 0-1000>, "found": true, "confidence": 0.0-1.0, "reason": "short"}

IMPORTANT: x_norm and y_norm are NORMALIZED coordinates from 0 to 1000.
- x_norm=0 left edge, 1000 right edge
- y_norm=0 top edge, 1000 bottom edge
- Example center -> 500,500
If not found: {"x_norm": 0, "y_norm": 0, "found": false, "reason": "why"}
Return ONLY JSON, nothing else."""

    for model in GROQ_VISION_MODELS:
        try:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            text = (resp.choices[0].message.content or "").strip()
            # Strip fences
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
                print("[vision groq] not found: " + str(data.get("reason", ""))[:60])
                return None
        except Exception as e:
            err = str(e)[:100]
            if any(x in err for x in ["503", "UNAVAILABLE", "429", "overload", "404", "NOT_FOUND"]):
                continue
            # If model not found, try next
            if "model" in err.lower() or "decommissioned" in err.lower():
                continue
            print("[vision groq " + model + "] " + err[:80])
            continue
    return None


def _find_target_gemini(target_desc, img_bytes, region_hint=None):
    """Ask Gemini Vision to locate target. Returns dict or None."""
    if not _GENAI or not img_bytes:
        return None
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("[vision] GEMINI_API_KEY missing, trying Groq fallback...")
        return None
    region_text = ""
    if region_hint:
        region_text = "\nRegion focus: " + region_hint + " (look ONLY in this region)"
    prompt = """Find this UI element on screen: """ + target_desc + region_text + """

Return coordinates as JSON:
{"x_norm": <int 0-1000>, "y_norm": <int 0-1000>, "found": true, "confidence": 0.0-1.0, "reason": "short"}

IMPORTANT: x_norm and y_norm are NORMALIZED coordinates from 0 to 1000.
- x_norm=0 left edge, 1000 right edge
- y_norm=0 top edge, 1000 bottom edge
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


def _find_target_vision(target_desc, img_bytes, region_hint=None):
    """
    Unified vision: Try Groq first (free tier), then Gemini.
    Works for ANY UI - icons, buttons, graphics (not just OCR text).
    """
    # Prefer Groq if key exists (no extra billing)
    if os.environ.get("GROQ_API_KEY"):
        found = _find_target_groq(target_desc, img_bytes, region_hint=region_hint)
        if found:
            return found
    # Fallback Gemini
    if os.environ.get("GEMINI_API_KEY"):
        found = _find_target_gemini(target_desc, img_bytes, region_hint=region_hint)
        if found:
            return found
    # If groq failed but gemini not available, try groq again? already did
    # Try groq even if initial fail? already
    if not os.environ.get("GROQ_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        print("[vision] No vision API key (need GROQ_API_KEY or GEMINI_API_KEY)")
    return None


# ---------- Helpers ----------

def _activate_taskbar_app(app_name):
    """Find app window by name and activate (bring to front)."""
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


def vision_click(target_desc, dry_run=False, use_active_window=True):
    """
    Main function: Find target on screen and click it.
    FIXED: by default uses ACTIVE WINDOW only (not full screen + terminal).

    Args:
        target_desc: English description (e.g. "YouTube icon in taskbar", "Play button")
        dry_run: If True, only find, don't click.
        use_active_window: If True (default), capture active window only. Set False for fullscreen fallback.

    Returns: dict with {ok, x, y, reason, verified}
    """
    global _last_screenshot_hash

    print("[vision] Looking for: " + target_desc + (" (active window)" if use_active_window else " (full screen)"))

    tlow = target_desc.lower()
    use_taskbar_mode = "taskbar" in tlow

    if use_taskbar_mode:
        img, img_bytes, crop_box, upscaled_size = _capture_taskbar()
        if not img:
            return {"ok": False, "reason": "taskbar capture failed"}
        print("[vision] Taskbar mode: crop=" + str(crop_box) + " upscaled=" + str(upscaled_size))
        region_hint = "bottom strip of screen (Windows taskbar)"
        before_hash = _hash_image(img)
        found = _find_target_vision(target_desc, img_bytes, region_hint=region_hint)
        if not found:
            return {"ok": False, "reason": "target not found"}
        # Scale normalized -> screen coords via crop_box
        left, top, right, bottom = crop_box
        crop_w = right - left
        crop_h = bottom - top
        x_crop = found["x_norm"] * crop_w / 1000
        y_crop = found["y_norm"] * crop_h / 1000
        x = int(left + x_crop)
        y = int(top + y_crop)
        print("[vision] Taskbar normalized=(" + str(found["x_norm"]) + "," + str(found["y_norm"]) + ") -> Screen=(" + str(x) + "," + str(y) + ")")
    else:
        # Normal mode: active window vs full screen
        if use_active_window:
            # Use new active capture that returns bbox
            result = _capture_active()
            if result[0] is None:
                return {"ok": False, "reason": "screen capture failed"}
            if len(result) == 4 and result[3] is not None:
                img, img_bytes, small_size, bbox = result
                left, top, w, h = bbox
                before_hash = _hash_image(img)
                found = _find_target_vision(target_desc, img_bytes, region_hint="active application window")
                if not found:
                    # Fallback to full screen if not found in active window
                    print("[vision] Not found in active window, trying full screen fallback...")
                    img2, img_bytes2, small_size2 = _capture_full()
                    if img2:
                        found2 = _find_target_vision(target_desc, img_bytes2, region_hint=None)
                        if found2:
                            found = found2
                            img = img2
                            bbox = None
                            before_hash = _hash_image(img)
                            if _PYAUTO:
                                try:
                                    logical_w, logical_h = pyautogui.size()
                                    x = int(found["x_norm"] * logical_w / 1000)
                                    y = int(found["y_norm"] * logical_h / 1000)
                                except Exception as e:
                                    return {"ok": False, "reason": "scaling fail: " + str(e)[:60]}
                            else:
                                x = int(found["x_norm"] * img.size[0] / 1000)
                                y = int(found["y_norm"] * img.size[1] / 1000)
                            print("[vision] Fallback fullscreen Found at (" + str(x) + ", " + str(y) + ") conf=" + str(found["confidence"]))
                            if dry_run:
                                return {"ok": True, "x": x, "y": y, "reason": "dry run (fallback)", "verified": False}
                            if not _PYAUTO:
                                return {"ok": False, "x": x, "y": y, "reason": "pyautogui unavailable"}
                            try:
                                pyautogui.moveTo(x, y, duration=0.3)
                                time.sleep(0.2)
                                pyautogui.click()
                                print("[vision] Clicked at (" + str(x) + "," + str(y) + ")")
                            except Exception as e:
                                return {"ok": False, "x": x, "y": y, "reason": "click fail: " + str(e)[:60]}
                            time.sleep(1.5)
                            img_after, _, _ = _capture_full()
                            verified = False
                            if img_after:
                                after_hash = _hash_image(img_after)
                                if before_hash != after_hash:
                                    verified = True
                                    print("[vision] Screen changed - verified")
                            return {"ok": True, "x": x, "y": y, "reason": found.get("reason", ""), "verified": verified, "confidence": found.get("confidence", 0)}
                    return {"ok": False, "reason": "target not found in active window"}
                # Found in active window - scale normalized to screen via bbox
                x = int(left + found["x_norm"] * w / 1000)
                y = int(top + found["y_norm"] * h / 1000)
                print("[vision] ActiveWindow normalized=(" + str(found["x_norm"]) + "," + str(found["y_norm"]) + ") -> Screen=(" + str(x) + "," + str(y) + ") bbox=" + str(bbox))
            else:
                # No bbox (fallback to full)
                img, img_bytes, small_size = result[0], result[1], result[2]
                before_hash = _hash_image(img)
                found = _find_target_vision(target_desc, img_bytes, region_hint=None)
                if not found:
                    return {"ok": False, "reason": "target not found"}
                if _PYAUTO:
                    try:
                        logical_w, logical_h = pyautogui.size()
                        x = int(found["x_norm"] * logical_w / 1000)
                        y = int(found["y_norm"] * logical_h / 1000)
                        print("[vision] Normalized=(" + str(found["x_norm"]) + "," + str(found["y_norm"]) + ") -> Logical=(" + str(x) + "," + str(y) + ") on " + str(logical_w) + "x" + str(logical_h))
                    except Exception as e:
                        return {"ok": False, "reason": "scaling fail: " + str(e)[:60]}
                else:
                    x = int(found["x_norm"] * img.size[0] / 1000)
                    y = int(found["y_norm"] * img.size[1] / 1000)
        else:
            # Full screen mode (explicit)
            img, img_bytes, small_size = _capture_full()
            if not img:
                return {"ok": False, "reason": "screen capture failed"}
            before_hash = _hash_image(img)
            found = _find_target_vision(target_desc, img_bytes, region_hint=None)
            if not found:
                return {"ok": False, "reason": "target not found"}
            if _PYAUTO:
                try:
                    logical_w, logical_h = pyautogui.size()
                    x = int(found["x_norm"] * logical_w / 1000)
                    y = int(found["y_norm"] * logical_h / 1000)
                    print("[vision] Fullscreen Normalized=(" + str(found["x_norm"]) + "," + str(found["y_norm"]) + ") -> Logical=(" + str(x) + "," + str(y) + ")")
                except Exception as e:
                    return {"ok": False, "reason": "scaling fail: " + str(e)[:60]}
            else:
                x = int(found["x_norm"] * img.size[0] / 1000)
                y = int(found["y_norm"] * img.size[1] / 1000)

    # Sanity check: coords inside screen?
    if _PYAUTO:
        sw, sh = pyautogui.size()
        if x < 0 or x >= sw or y < 0 or y >= sh:
            return {"ok": False, "reason": "coords out of screen: (" + str(x) + "," + str(y) + ")"}

    print("[vision] Found at (" + str(x) + ", " + str(y) + ") conf=" + str(found["confidence"]) + " model=" + found.get("model", ""))

    if dry_run:
        return {"ok": True, "x": x, "y": y, "reason": "dry run", "verified": False}

    if not _PYAUTO:
        return {"ok": False, "x": x, "y": y, "reason": "pyautogui unavailable"}

    try:
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        print("[vision] Clicked at (" + str(x) + "," + str(y) + ")")
    except Exception as e:
        return {"ok": False, "x": x, "y": y, "reason": "click fail: " + str(e)[:60]}

    time.sleep(1.5)
    # Verify: capture same mode
    if use_taskbar_mode:
        img_after, _, _, _ = _capture_taskbar()
    elif use_active_window and not use_taskbar_mode:
        r = _capture_active()
        img_after = r[0] if r and len(r) >= 1 else None
        if img_after is None:
            img_after, _, _ = _capture_full()
    else:
        img_after, _, _ = _capture_full()
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
      3. Vision click (visual - active window by default) - last resort
    """
    target = (args.get("target") or "").strip()
    if not target:
        return "Boss, kya click karna hai bolo."
    dry = bool(args.get("dry_run", False))
    # Allow explicit fullscreen if requested
    use_active = not bool(args.get("fullscreen", False))

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

    # Layer 3: Vision click (active window by default - FIXES terminal bug)
    print("[vision] Layer 3: Vision click for '" + target + "' (active_window=" + str(use_active) + ")")
    result = vision_click(target, dry_run=dry, use_active_window=use_active)

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
    print("  groq:", _GROQ)
    print()
    print("Active region:", _active_region_mss())
    print("All ready. Use: vision_click('YouTube icon')")
