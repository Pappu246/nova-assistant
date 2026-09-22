with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

# Fix vision_click to convert physical -> logical coords
old = '''    # Scale coords from small to original
    # Small was resized to 1280x720 max, original is screen size
    small_max = (1280, 720)
    orig_size = img.size
    # Calculate small image dimensions preserving aspect
    sw = min(img.size[0], 1280)
    sh = int(img.size[1] * (sw / img.size[0]))
    if sh > 720:
        sh = 720
        sw = int(img.size[0] * (sh / img.size[1]))

    x, y = _scale_coords(found["x"], found["y"], (sw, sh), orig_size)

    print("[vision] Found at (" + str(x) + ", " + str(y) + ") conf=" + str(found["confidence"]))'''

new = '''    # Scale coords from small image (1280x720) back to PHYSICAL screen
    small_size = (1280, 720)
    orig_size = img.size
    x_phys, y_phys = _scale_coords(found["x"], found["y"], small_size, orig_size)

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

if old in src:
    src = src.replace(old, new)
    print("DPI scaling fixed")
else:
    print("Pattern not found")

with open("vision_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
