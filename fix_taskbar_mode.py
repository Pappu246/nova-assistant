with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add taskbar capture function before vision_click
taskbar_fn = '''

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

'''

if "_capture_taskbar" not in src:
    src = src.replace("def vision_click(", taskbar_fn + "\ndef vision_click(", 1)
    print("_capture_taskbar added")

# Modify vision_click to support taskbar mode
old_start = '''    print("[vision] Looking for: " + target_desc)

    # 1. Capture
    img, img_bytes, small_size = _capture()
    if not img:
        return {"ok": False, "reason": "screen capture failed"}

    before_hash = _hash_image(img)

    # 2. Find target (with optional region)
    region = None
    tlow = target_desc.lower()
    if "taskbar" in tlow:
        region = "bottom strip of screen (Windows taskbar)"
    elif "desktop" in tlow:
        region = "main desktop area (not taskbar)"
    elif "top" in tlow and "bar" in tlow:
        region = "top strip of screen (window title bar area)"

    found = _find_target_gemini(target_desc, img_bytes, region_hint=region)
    if not found:
        return {"ok": False, "reason": "target not found"}'''

new_start = '''    print("[vision] Looking for: " + target_desc)

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
        return {"ok": False, "reason": "target not found"}'''

if old_start in src:
    src = src.replace(old_start, new_start)
    print("vision_click taskbar mode added")
else:
    print("Start pattern not found")

# Fix scaling section to handle taskbar mode
old_scaling = '''    # Scale NORMALIZED coords (0-1000) -> logical screen coords
    if _PYAUTO:
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
        y = int(found["y_norm"] * img.size[1] / 1000)'''

new_scaling = '''    # Scale coords based on mode
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
        y = int(found["y_norm"] * img.size[1] / 1000)'''

if old_scaling in src:
    src = src.replace(old_scaling, new_scaling)
    print("Scaling updated for taskbar mode")
else:
    print("Scaling pattern not found")

with open("vision_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
print("vision_agent.py updated with taskbar mode")
