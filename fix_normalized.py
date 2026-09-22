with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

# 1. Fix prompt to ask normalized coords
old_prompt = '''    prompt = """Find this UI element on screen: """ + target_desc + region_text + """

Return coordinates as JSON: {"x": <int>, "y": <int>, "found": true, "confidence": 0.0-1.0, "reason": "short"}

Coordinates are in the image's pixel space (top-left is 0,0).
If not found: {"x": 0, "y": 0, "found": false, "reason": "why"}
Return ONLY JSON, nothing else."""'''

new_prompt = '''    prompt = """Find this UI element on screen: """ + target_desc + region_text + """

Return coordinates as JSON:
{"x_norm": <int 0-1000>, "y_norm": <int 0-1000>, "found": true, "confidence": 0.0-1.0, "reason": "short"}

IMPORTANT: x_norm and y_norm are NORMALIZED coordinates from 0 to 1000.
- x_norm=0 means left edge, x_norm=1000 means right edge
- y_norm=0 means top edge, y_norm=1000 means bottom edge
- Example: element at center of screen -> x_norm=500, y_norm=500
- Example: element at top-left corner -> x_norm=50, y_norm=50
- Example: element in taskbar (bottom) -> y_norm=950

If not found: {"x_norm": 0, "y_norm": 0, "found": false, "reason": "why"}
Return ONLY JSON, nothing else."""'''

if old_prompt in src:
    src = src.replace(old_prompt, new_prompt)
    print("Prompt updated to normalized coords")
else:
    print("Prompt pattern not found")

# 2. Fix parsing to accept x_norm/y_norm
old_parse = '''            if data.get("found"):
                return {
                    "x": int(data.get("x", 0)),
                    "y": int(data.get("y", 0)),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reason": str(data.get("reason", "")),
                    "model": model,
                }'''

new_parse = '''            if data.get("found"):
                return {
                    "x_norm": int(data.get("x_norm", 0)),
                    "y_norm": int(data.get("y_norm", 0)),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reason": str(data.get("reason", "")),
                    "model": model,
                }'''

if old_parse in src:
    src = src.replace(old_parse, new_parse)
    print("Parsing updated to normalized")
else:
    print("Parse pattern not found")

# 3. Fix scaling to use normalized coords
old_scale = '''    # Scale coords from ACTUAL small image size back to physical screen
    orig_size = img.size
    x_phys, y_phys = _scale_coords(found["x"], found["y"], small_size, orig_size)
    print("[vision] Small=" + str(small_size) + " Physical=" + str(orig_size))

    # Convert physical coords -> logical (DPI scaling)
    if _PYAUTO:
        try:
            logical_w, logical_h = pyautogui.size()
            phys_w, phys_h = orig_size
            scale_x = logical_w / phys_w
            scale_y = logical_h / phys_h
            x = int(x_phys * scale_x)
            y = int(y_phys * scale_y)
            print("[vision] DPI scale: " + str(round(scale_x, 2)) + "x"
                  + " | physical=(" + str(x_phys) + "," + str(y_phys) + ")"
                  + " logical=(" + str(x) + "," + str(y) + ")")
        except Exception as e:
            x, y = x_phys, y_phys
            print("[vision] DPI scale fail: " + str(e)[:50])
    else:
        x, y = x_phys, y_phys

    print("[vision] Found at (" + str(x) + ", " + str(y) + ") conf=" + str(found["confidence"]))'''

new_scale = '''    # Scale NORMALIZED coords (0-1000) -> logical screen coords
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
        y = int(found["y_norm"] * img.size[1] / 1000)

    # Sanity check: coords inside screen?
    if _PYAUTO:
        sw, sh = pyautogui.size()
        if x < 0 or x >= sw or y < 0 or y >= sh:
            return {"ok": False, "reason": "coords out of screen: (" + str(x) + "," + str(y) + ")"}

    print("[vision] Found at (" + str(x) + ", " + str(y) + ") conf=" + str(found["confidence"]))'''

if old_scale in src:
    src = src.replace(old_scale, new_scale)
    print("Scaling updated to normalized")
else:
    print("Scale pattern not found")

# 4. Fix verify loop - unpack 3 values
src = src.replace("    img_after, _ = _capture()", "    img_after, _, _ = _capture()")

# 5. Remove unused _scale_coords call in dry_run response if any
src = src.replace(
    'return {"ok": True, "x": x, "y": y, "reason": "dry run", "verified": False}',
    'return {"ok": True, "x": x, "y": y, "reason": "dry run", "verified": False}'
)

with open("vision_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
print("vision_agent.py fully updated")
