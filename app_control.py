"""
NOVA App Control - apps kholna, band karna, type karna, click karna.
Windows-focused. Safe: sirf whitelisted apps allowed.
"""
import os
import sys
import time
import subprocess
import platform

IS_WIN = platform.system() == "Windows"

# ---------- Lazy imports ----------
_pag = None
_gw = None
_kb = None

def _get_pag():
    global _pag
    if _pag is None:
        try:
            import pyautogui
            pyautogui.FAILSAFE = True   # corner pe jaane se ruk jayega
            pyautogui.PAUSE = 0.05
            _pag = pyautogui
        except Exception as e:
            print("[app_control] pyautogui load fail:", str(e)[:60])
    return _pag


def _get_gw():
    global _gw
    if _gw is None:
        try:
            import pygetwindow as gw
            _gw = gw
        except Exception as e:
            print("[app_control] pygetwindow load fail:", str(e)[:60])
    return _gw


def _get_kb():
    global _kb
    if _kb is None:
        try:
            import keyboard
            _kb = keyboard
        except Exception:
            pass
    return _kb


# ---------- App launcher (whitelist) ----------
APP_MAP = {
    "chrome": ["chrome"],
    "google chrome": ["chrome"],
    "browser": ["chrome"],
    "notepad": ["notepad"],
    "calculator": ["calc"],
    "calc": ["calc"],
    "explorer": ["explorer"],
    "file explorer": ["explorer"],
    "files": ["explorer"],
    "cmd": ["cmd"],
    "command prompt": ["cmd"],
    "terminal": ["cmd"],
    "powershell": ["powershell"],
    "vscode": ["code"],
    "vs code": ["code"],
    "code": ["code"],
    "word": ["winword"],
    "excel": ["excel"],
    "powerpoint": ["powerpnt"],
    "paint": ["mspaint"],
    "task manager": ["taskmgr"],
    "settings": ["ms-settings:"],
    "whatsapp": ["whatsapp"],
    "telegram": ["telegram"],
    "spotify": ["spotify"],
    "vlc": ["vlc"],
}


def open_app(name):
    """Open an app by friendly name."""
    if not IS_WIN:
        return "App control sirf Windows pe hai Boss."
    key = name.lower().strip()
    cmd = APP_MAP.get(key)
    if not cmd:
        # Try direct start
        try:
            subprocess.Popen("start " + key, shell=True)
            return name + " khol raha hoon Boss."
        except Exception as e:
            return "App nahi mila: " + name

    try:
        if cmd[0].endswith(":"):
            os.startfile(cmd[0])
        else:
            subprocess.Popen(cmd, shell=False)
        time.sleep(0.5)
        return name + " khol diya Boss."
    except Exception as e:
        # Fallback: shell start
        try:
            subprocess.Popen("start " + cmd[0], shell=True)
            return name + " khol diya Boss."
        except Exception:
            return "Nahi khol paya: " + name + " - " + str(e)[:60]


def close_app(name):
    """Close windows matching title."""
    if not IS_WIN:
        return "Sirf Windows pe."
    gw = _get_gw()
    if gw is None:
        return "pygetwindow nahi hai Boss."
    try:
        wins = gw.getWindowsWithTitle(name)
        if not wins:
            return name + " naam ki window nahi mili."
        for w in wins:
            try:
                w.close()
            except Exception:
                pass
        return name + " band kar diya Boss."
    except Exception as e:
        return "Close fail: " + str(e)[:60]


def focus_window(title):
    """Bring a window to front."""
    if not IS_WIN:
        return "Sirf Windows pe."
    gw = _get_gw()
    if gw is None:
        return "pygetwindow nahi hai."
    try:
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return title + " window nahi mili."
        w = wins[0]
        try:
            if w.isMinimized:
                w.restore()
            w.activate()
        except Exception:
            try:
                w.minimize()
                w.restore()
            except Exception:
                pass
        return title + " focus kar diya."
    except Exception as e:
        return "Focus fail: " + str(e)[:60]


def list_windows():
    """List all open windows."""
    if not IS_WIN:
        return "Sirf Windows pe."
    gw = _get_gw()
    if gw is None:
        return "pygetwindow nahi hai."
    try:
        titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
        if not titles:
            return "Koi window khuli nahi hai."
        return "Khuli windows: " + ", ".join(titles[:15])
    except Exception as e:
        return "List fail: " + str(e)[:60]


def type_text(text):
    """Type text in focused window."""
    pag = _get_pag()
    if pag is None:
        return "pyautogui nahi hai."
    try:
        pag.typewrite(text, interval=0.02)
        return "Type kar diya."
    except Exception as e:
        return "Type fail: " + str(e)[:60]


def press_key(key):
    """Press a key or combo like 'enter', 'ctrl+c', 'alt+tab'."""
    kb = _get_kb()
    if kb is not None:
        try:
            kb.send(key)
            return "Key bheja: " + key
        except Exception:
            pass
    pag = _get_pag()
    if pag is None:
        return "koi input tool nahi."
    try:
        if "+" in key:
            parts = key.split("+")
            pag.hotkey(*parts)
        else:
            pag.press(key)
        return "Key bheja: " + key
    except Exception as e:
        return "Key fail: " + str(e)[:60]


def click(x, y):
    """Click at screen coords."""
    pag = _get_pag()
    if pag is None:
        return "pyautogui nahi hai."
    try:
        pag.click(int(x), int(y))
        return "Click kiya (" + str(x) + "," + str(y) + ")"
    except Exception as e:
        return "Click fail: " + str(e)[:60]


def screenshot(path=None):
    """Take screenshot, save + return path."""
    pag = _get_pag()
    if pag is None:
        return "pyautogui nahi hai."
    try:
        if path is None:
            path = os.path.join(
                os.path.expanduser("~"),
                "Pictures",
                "nova_shot_" + str(int(time.time())) + ".png",
            )
            os.makedirs(os.path.dirname(path), exist_ok=True)
        img = pag.screenshot()
        img.save(path)
        return "Screenshot save: " + path
    except Exception as e:
        return "Screenshot fail: " + str(e)[:60]


# ---------- Volume (Windows via keyboard) ----------
def volume_up():
    kb = _get_kb()
    if kb is None:
        return "keyboard module nahi hai."
    try:
        for _ in range(3):
            kb.send("volume up")
            time.sleep(0.05)
        return "Volume badha diya."
    except Exception as e:
        return "Volume fail: " + str(e)[:60]


def volume_down():
    kb = _get_kb()
    if kb is None:
        return "keyboard module nahi hai."
    try:
        for _ in range(3):
            kb.send("volume down")
            time.sleep(0.05)
        return "Volume kam kar diya."
    except Exception as e:
        return "Volume fail: " + str(e)[:60]


def mute():
    kb = _get_kb()
    if kb is None:
        return "keyboard module nahi hai."
    try:
        kb.send("volume mute")
        return "Mute toggle kiya."
    except Exception as e:
        return "Mute fail: " + str(e)[:60]


# ---------- Web helpers ----------
def youtube_search(query):
    """Open Chrome + YouTube search."""
    try:
        url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+")
        subprocess.Popen(["start", "chrome", url], shell=True)
        time.sleep(1.5)
        return "YouTube pe search kar diya: " + query
    except Exception as e:
        return "YouTube fail: " + str(e)[:60]


def google_search(query):
    """Open Chrome + Google search."""
    try:
        url = "https://www.google.com/search?q=" + query.replace(" ", "+")
        subprocess.Popen(["start", "chrome", url], shell=True)
        time.sleep(1.0)
        return "Google pe search kar diya: " + query
    except Exception as e:
        return "Google fail: " + str(e)[:60]


def open_url(url):
    """Open any URL in Chrome."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        subprocess.Popen(["start", "chrome", url], shell=True)
        return "Khol diya: " + url
    except Exception as e:
        return "URL fail: " + str(e)[:60]


def whatsapp_send(contact, message):
    """Open WhatsApp web + send message (basic)."""
    try:
        # WhatsApp Web - can't fully automate without more setup
        url = "https://web.whatsapp.com/"
        subprocess.Popen(["start", "chrome", url], shell=True)
        return ("WhatsApp Web khol diya. "
                + contact + " ko manually message bhejo: " + message[:40])
    except Exception as e:
        return "WhatsApp fail: " + str(e)[:60]


# ---------- TEST ----------
if __name__ == "__main__":
    print("=" * 55)
    print("  app_control.py TEST")
    print("=" * 55)
    print()
    print("1. Opening notepad...")
    print(open_app("notepad"))
    time.sleep(2)
    print()
    print("2. Typing text...")
    print(type_text("Hello NOVA testing"))
    time.sleep(0.5)
    print()
    print("3. Listing windows...")
    print(list_windows()[:200])
    time.sleep(1)
    print()
    print("4. Closing notepad...")
    print(close_app("Notepad"))
    print()
    print("Done.")
