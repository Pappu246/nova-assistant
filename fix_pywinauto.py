with open("vision_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add pywinauto import
if "import pywinauto" not in src:
    src = src.replace(
        "import time\n",
        '''import time

try:
    from pywinauto import Desktop
    _PYWINAUTO = True
except Exception:
    _PYWINAUTO = False
''',
        1
    )
    print("pywinauto import added")

# Add taskbar activate function
taskbar_fn = '''

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

'''

if "_activate_taskbar_app" not in src:
    src = src.replace("def _capture_taskbar", taskbar_fn + "\ndef _capture_taskbar", 1)
    print("_activate_taskbar_app added")

with open("vision_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
print("vision_agent.py updated")
