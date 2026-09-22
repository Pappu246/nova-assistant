with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

# Fix _capture to return actual small size
old_cap = '''def _capture():
    """Capture screen and return (PIL_image, bytes_for_gemini)."""
    if not _MSS or not _PIL:
        return None, None
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            # Small copy for Gemini
            small = img.copy()
            small.thumbnail((1280, 720))
            buf = io.BytesIO()
            small.save(buf, format="JPEG", quality=75)
            return img, buf.getvalue()
    except Exception as e:
        print("[vision] capture fail: " + str(e)[:60])
        return None, None'''

new_cap = '''def _capture():
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
        return None, None, None'''

if old_cap in src:
    src = src.replace(old_cap, new_cap)
    print("_capture returns actual small_size")
else:
    print("Capture pattern not found")

# Fix vision_click to use actual small_size
old_use = '''    # 1. Capture
    img, img_bytes = _capture()
    if not img:
        return {"ok": False, "reason": "screen capture failed"}'''

new_use = '''    # 1. Capture
    img, img_bytes, small_size = _capture()
    if not img:
        return {"ok": False, "reason": "screen capture failed"}'''

if old_use in src:
    src = src.replace(old_use, new_use)
    print("vision_click uses actual small_size")

# Fix scaling block
old_scale = '''    # Scale coords from small image (1280x720) back to PHYSICAL screen
    small_size = (1280, 720)
    orig_size = img.size
    x_phys, y_phys = _scale_coords(found["x"], found["y"], small_size, orig_size)'''

new_scale = '''    # Scale coords from ACTUAL small image size back to physical screen
    orig_size = img.size
    x_phys, y_phys = _scale_coords(found["x"], found["y"], small_size, orig_size)
    print("[vision] Small=" + str(small_size) + " Physical=" + str(orig_size))'''

if old_scale in src:
    src = src.replace(old_scale, new_scale)
    print("Scaling uses actual small_size")

with open("vision_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Done")
