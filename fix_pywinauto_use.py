with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

# In tool_vision_click, use pywinauto for taskbar
old_tool = '''def tool_vision_click(args):
    """args: {target: str, dry_run: bool}"""
    target = (args.get("target") or "").strip()
    if not target:
        return "Boss, kya click karna hai bolo."
    dry = bool(args.get("dry_run", False))
    result = vision_click(target, dry_run=dry)'''

new_tool = '''def tool_vision_click(args):
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

if old_tool in src:
    src = src.replace(old_tool, new_tool)
    print("tool_vision_click uses pywinauto for taskbar")
else:
    print("Tool pattern not found")

with open("vision_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
print("vision_agent.py updated")
