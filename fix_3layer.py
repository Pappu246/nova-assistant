with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

old_tool = '''def tool_vision_click(args):
    """args: {target: str, dry_run: bool}"""
    target = (args.get("target") or "").strip()
    if not target:
        return "Boss, kya click karna hai bolo."
    dry = bool(args.get("dry_run", False))

    # If taskbar click, try pywinauto first (100% accurate)
    tlow = target.lower()
    if "taskbar" in tlow and not dry:
        # Extract app name from target
        import re
        # Remove "icon in taskbar", "in taskbar", "taskbar"
        app_name = re.sub(r"\\s*(icon|button)?\\s*(in|on)\\s+taskbar\\s*", "", tlow).strip()
        app_name = app_name.replace(" icon", "").replace(" button", "").strip()
        if app_name:
            print("[vision] Trying pywinauto for: " + app_name)
            if _activate_taskbar_app(app_name):
                return "Boss, " + app_name + " activate kar diya."

    result = vision_click(target, dry_run=dry)'''

new_tool = '''def tool_vision_click(args):
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
    result = vision_click(target, dry_run=dry)'''

if old_tool in src:
    src = src.replace(old_tool, new_tool)
    with open("vision_agent.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("3-layer fallback added")
else:
    print("Tool pattern not found")
