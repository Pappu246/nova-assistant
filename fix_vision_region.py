with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add region support to find_target
old_fn = '''def _find_target_gemini(target_desc, img_bytes):
    """Ask Gemini Vision to locate target. Returns (x, y) or None."""
    if not _GENAI or not img_bytes:
        return None

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("[vision] GEMINI_API_KEY missing")
        return None

    prompt = """Find this UI element on screen: """ + target_desc + """

Return coordinates as JSON: {"x": <int>, "y": <int>, "found": true, "confidence": 0.0-1.0, "reason": "short"}

Coordinates are in the image's pixel space. If not found: {"x": 0, "y": 0, "found": false, "reason": "why"}
Return ONLY JSON, nothing else."""'''

new_fn = '''def _find_target_gemini(target_desc, img_bytes, region_hint=None):
    """Ask Gemini Vision to locate target. Returns (x, y) or None."""
    if not _GENAI or not img_bytes:
        return None

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("[vision] GEMINI_API_KEY missing")
        return None

    region_text = ""
    if region_hint:
        region_text = "\\nRegion focus: " + region_hint + " (look ONLY in this region)"

    prompt = """Find this UI element on screen: """ + target_desc + region_text + """

Return coordinates as JSON: {"x": <int>, "y": <int>, "found": true, "confidence": 0.0-1.0, "reason": "short"}

Coordinates are in the image's pixel space (top-left is 0,0).
If not found: {"x": 0, "y": 0, "found": false, "reason": "why"}
Return ONLY JSON, nothing else."""'''

if old_fn in src:
    src = src.replace(old_fn, new_fn)
    print("region_hint added to _find_target_gemini")
else:
    print("Pattern not found")

# Update vision_click to accept region hint
old_call = '''    # 2. Find target
    found = _find_target_gemini(target_desc, img_bytes)'''
new_call = '''    # 2. Find target (with optional region)
    region = None
    tlow = target_desc.lower()
    if "taskbar" in tlow:
        region = "bottom strip of screen (Windows taskbar)"
    elif "desktop" in tlow:
        region = "main desktop area (not taskbar)"
    elif "top" in tlow and "bar" in tlow:
        region = "top strip of screen (window title bar area)"

    found = _find_target_gemini(target_desc, img_bytes, region_hint=region)'''

if old_call in src:
    src = src.replace(old_call, new_call)
    print("vision_click uses region hint")

with open("vision_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
print("vision_agent.py updated")
