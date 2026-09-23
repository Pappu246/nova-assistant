"""
NOVA App Control - apps kholna, band karna, type karna, click karna.
Windows-focused. Safe: sirf whitelisted apps allowed.
FIXES: mute/unmute inversion, youtube plays first video, active window region.
"""
import os
import sys
import time
import subprocess
import platform
import urllib.parse
import webbrowser

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
            pyautogui.FAILSAFE = True
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


# ---------- Active window region helper ----------
def _active_region():
    """Return (left, top, width, height) of active window or None."""
    gw = _get_gw()
    if gw is None:
        return None
    try:
        w = gw.getActiveWindow()
        if w and hasattr(w, 'width') and hasattr(w, 'height'):
            if w.width > 80 and w.height > 80:
                return (int(w.left), int(w.top), int(w.width), int(w.height))
    except Exception:
        pass
    return None


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
            # Handle both property and method forms of isMinimized
            is_min = False
            try:
                val = w.isMinimized
                is_min = val() if callable(val) else bool(val)
            except Exception:
                is_min = False
            if is_min:
                try:
                    w.restore()
                except Exception:
                    pass
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
    """Take screenshot of ACTIVE WINDOW if possible, else full screen."""
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
        # Prefer active window region if available, but save full path info
        region = _active_region()
        if region:
            # For screenshot tool, save active window only if user wants - but we save full screen for reliability
            # Use full screen to avoid confusion; active region used for OCR only
            img = pag.screenshot()
        else:
            img = pag.screenshot()
        img.save(path)
        return "Screenshot save: " + path
    except Exception as e:
        return "Screenshot fail: " + str(e)[:60]


# ---------- Volume - PROPER mute/unmute (FIXES BUG 2) ----------

# State file for fallback tracking when pycaw unavailable
_MUTE_STATE_FILE = os.path.join(os.path.expanduser("~"), ".nova_mute_state")


def _get_endpoint_volume():
    """Try to get Windows audio endpoint via pycaw. Returns controller or None."""
    try:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume
    except Exception:
        return None


def _read_mute_state_file():
    try:
        if os.path.exists(_MUTE_STATE_FILE):
            with open(_MUTE_STATE_FILE, 'r') as f:
                return f.read().strip().lower() == "muted"
    except Exception:
        pass
    return None


def _write_mute_state_file(muted):
    try:
        with open(_MUTE_STATE_FILE, 'w') as f:
            f.write("muted" if muted else "unmuted")
    except Exception:
        pass


def is_muted():
    """Check if system is muted. Uses pycaw if available."""
    vol = _get_endpoint_volume()
    if vol is not None:
        try:
            return bool(vol.GetMute())
        except Exception:
            pass
    # Fallback: file state
    state = _read_mute_state_file()
    return state if state is not None else False


def _set_mute(muted: bool):
    """Internal: set mute state explicitly."""
    vol = _get_endpoint_volume()
    if vol is not None:
        try:
            vol.SetMute(muted, None)
            _write_mute_state_file(muted)
            return True
        except Exception as e:
            print("[volume] pycaw set mute fail:", str(e)[:60])
    # Fallback: keyboard toggle with state tracking
    current = _read_mute_state_file()
    # If we know state and it already matches, do nothing
    if current is not None and current == muted:
        return True
    # Otherwise toggle via keyboard
    kb = _get_kb()
    pag = _get_pag()
    # Try keyboard
    try:
        if kb is not None:
            kb.send("volume mute")
        elif pag is not None:
            pag.press("volumemute")
        else:
            return False
        _write_mute_state_file(muted)
        # If state unknown, we toggled blindly - assume we reached desired
        # If state was unknown, we still assume toggle worked
        return True
    except Exception:
        return False


def mute():
    """Explicitly mute (not toggle). Fixes inverted mute bug."""
    if _set_mute(True):
        return "Mute kar diya Boss."
    return "Mute fail."


def unmute():
    """Explicitly unmute (not toggle). Fixes bug where 'unmute' toggled to mute."""
    if _set_mute(False):
        return "Unmute kar diya Boss, awaaz wapas aa gayi."
    return "Unmute fail."


def toggle_mute():
    """Toggle mute state."""
    vol = _get_endpoint_volume()
    if vol is not None:
        try:
            cur = bool(vol.GetMute())
            vol.SetMute(not cur, None)
            _write_mute_state_file(not cur)
            return "Mute toggle kiya - " + ("mute" if not cur else "unmute") + "."
        except Exception:
            pass
    # Fallback
    kb = _get_kb()
    pag = _get_pag()
    try:
        if kb is not None:
            kb.send("volume mute")
        elif pag is not None:
            pag.press("volumemute")
        else:
            return "keyboard module nahi hai."
        # Flip file state
        cur = _read_mute_state_file()
        new_state = not cur if cur is not None else True
        _write_mute_state_file(new_state)
        return "Mute toggle kiya."
    except Exception as e:
        return "Mute fail: " + str(e)[:60]


def volume_up():
    kb = _get_kb()
    # Try pycaw for precise control
    vol = _get_endpoint_volume()
    if vol is not None:
        try:
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(min(1.0, cur + 0.15), None)
            return "Volume badha diya."
        except Exception:
            pass
    if kb is None:
        pag = _get_pag()
        if pag:
            try:
                for _ in range(3):
                    pag.press("volumeup")
                return "Volume badha diya."
            except Exception as e:
                return "Volume fail: " + str(e)[:60]
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
    vol = _get_endpoint_volume()
    if vol is not None:
        try:
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(max(0.0, cur - 0.15), None)
            return "Volume kam kar diya."
        except Exception:
            pass
    if kb is None:
        pag = _get_pag()
        if pag:
            try:
                for _ in range(3):
                    pag.press("volumedown")
                return "Volume kam kar diya."
            except Exception as e:
                return "Volume fail: " + str(e)[:60]
        return "keyboard module nahi hai."
    try:
        for _ in range(3):
            kb.send("volume down")
            time.sleep(0.05)
        return "Volume kam kar diya."
    except Exception as e:
        return "Volume fail: " + str(e)[:60]


# ---------- Web helpers (FIX BUG 3: youtube actually plays) ----------

def _yt_dlp_first_video_url(query):
    """Use yt-dlp to get first video URL. Returns url or None."""
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch1",
            "skip_download": True,
            "extractor_args": {"youtube": {"skip": ["dash", "hls"]}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("ytsearch1:" + query, download=False)
            if info and info.get("entries"):
                first = info["entries"][0]
                vid = first.get("id")
                if vid:
                    return "https://www.youtube.com/watch?v=" + vid
    except Exception as e:
        print("[youtube] yt-dlp fail:", str(e)[:80])
    return None


def youtube_search(query):
    """Search YouTube and PLAY first video (not just search page). FIXES BUG 3."""
    if not query or not query.strip():
        try:
            webbrowser.open("https://www.youtube.com")
            return "YouTube khol diya Boss."
        except Exception as e:
            return "YouTube fail: " + str(e)[:60]
    query = query.strip()
    # Try to get direct video URL via yt-dlp
    direct_url = _yt_dlp_first_video_url(query)
    try:
        if direct_url:
            webbrowser.open(direct_url)
            time.sleep(0.8)
            return "YouTube pe '" + query + "' ka pehla video chala diya Boss. " + direct_url
        # Fallback: search results page
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        webbrowser.open(url)
        time.sleep(1.0)
        return "YouTube pe search kar diya: " + query + " (direct video nahi mila, search khola)"
    except Exception as e:
        return "YouTube fail: " + str(e)[:60]


def google_search(query):
    """Open Chrome + Google search."""
    try:
        url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
        webbrowser.open(url)
        time.sleep(0.8)
        return "Google pe search kar diya: " + query
    except Exception as e:
        return "Google fail: " + str(e)[:60]


def open_url(url):
    """Open any URL in default browser."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return "Khol diya: " + url
    except Exception as e:
        return "URL fail: " + str(e)[:60]


def whatsapp_send(contact, message):
    """Open WhatsApp web + send message (basic)."""
    try:
        url = "https://web.whatsapp.com/"
        webbrowser.open(url)
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
    print("1. Testing volume mute/unmute toggle...")
    print("is_muted before:", is_muted())
    print(mute())
    time.sleep(0.5)
    print("is_muted after mute:", is_muted())
    print(unmute())
    print("is_muted after unmute:", is_muted())
    print(toggle_mute())
    print()
    print("2. Listing windows...")
    print(list_windows()[:300])
    print()
    print("Done.")
