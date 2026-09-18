import subprocess
import platform
import datetime
import urllib.request
import urllib.parse
import json
import os
import webbrowser
import time

try:
    from memory import tool_remember, tool_recall, tool_forget, tool_note, tool_list_notes
except Exception:
    def tool_remember(a): return 'Memory load nahi hui.'
    def tool_recall(a): return 'Memory load nahi hui.'
    def tool_forget(a): return 'Memory load nahi hui.'
    def tool_note(a): return 'Memory load nahi hui.'
    def tool_list_notes(a): return 'Memory load nahi hui.'

try:
    import pyautogui
    _PYAUTOGUI = True
except Exception:
    _PYAUTOGUI = False

try:
    import mss
    _MSS = True
except Exception:
    _MSS = False

try:
    import yt_dlp
    _YTDLP = True
except Exception:
    _YTDLP = False


def get_time(_args=None):
    now = datetime.datetime.now()
    return f"Abhi time hai {now.strftime('%I:%M %p')}"


def get_weather(args):
    city = args.get("city", "Jaipur")
    try:
        geo_url = "https://geocoding-api.open-meteo.com/v1/search?name=" + urllib.parse.quote(city) + "&count=1"
        with urllib.request.urlopen(geo_url, timeout=10) as resp:
            geo_data = json.loads(resp.read())
        if not geo_data.get("results"):
            return f"{city} ka location nahi mila."
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        weather_url = "https://api.open-meteo.com/v1/forecast?latitude=" + str(lat) + "&longitude=" + str(lon) + "&current=temperature_2m"
        with urllib.request.urlopen(weather_url, timeout=10) as resp:
            weather_data = json.loads(resp.read())
        temp = weather_data["current"]["temperature_2m"]
        return f"{city} mein abhi {temp} degree C hai."
    except Exception as e:
        return f"Weather nahi mil paaya: {e}"


_HOME = os.path.expanduser("~")

WEBSITES = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "facebook": "https://facebook.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "amazon": "https://amazon.in",
    "spotify": "https://open.spotify.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "github": "https://github.com",
}

FOLDERS = {
    "downloads": os.path.join(_HOME, "Downloads"),
    "download": os.path.join(_HOME, "Downloads"),
    "documents": os.path.join(_HOME, "Documents"),
    "document": os.path.join(_HOME, "Documents"),
    "desktop": os.path.join(_HOME, "Desktop"),
    "pictures": os.path.join(_HOME, "Pictures"),
    "photos": os.path.join(_HOME, "Pictures"),
    "screenshots": os.path.join(_HOME, "Pictures", "Screenshots"),
    "music": os.path.join(_HOME, "Music"),
    "videos": os.path.join(_HOME, "Videos"),
}

APP_PATHS = {
    "vlc": [
        "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
        "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
    ],
    "code": [
        os.path.join(_HOME, "AppData", "Local", "Programs", "Microsoft VS Code", "Code.exe"),
        "C:\\Program Files\\Microsoft VS Code\\Code.exe",
    ],
}

APP_ALIASES = {
    "chrome": "chrome", "browser": "chrome", "edge": "msedge",
    "firefox": "firefox", "notepad": "notepad", "calculator": "calc",
    "calc": "calc", "paint": "mspaint", "file explorer": "explorer",
    "files": "explorer", "explorer": "explorer", "settings": "ms-settings:",
    "control panel": "control", "task manager": "taskmgr", "terminal": "wt",
    "command prompt": "cmd", "cmd": "cmd", "word": "winword",
    "excel": "excel", "powerpoint": "powerpnt", "vlc": "vlc",
    "code": "code", "vs code": "code", "vscode": "code",
    "visual studio code": "code",
}


def _normalize(text):
    s = text.lower().strip()
    fillers = ["kholo", "khol do", "khol", "open karo", "open", "karo",
               "chalao", "chala do", "start karo", "folder", "app",
               "application", "please", "zara", "thoda", "mera", "meri",
               "ko", "ka", "ki", "do", "de", "dedo", "dikhao", "dikha"]
    for f in fillers:
        s = s.replace(f, " ")
    return " ".join(s.split())


def _find_in(target_dict, text):
    words = set(text.split())
    for key in target_dict:
        if key in words:
            return key
    for key in target_dict:
        if key in text:
            return key
    return None


def _launch_windows(name):
    if name.startswith("ms-"):
        try:
            os.startfile(name)
            return True
        except Exception:
            return False
    if name in APP_PATHS:
        for path in APP_PATHS[name]:
            if os.path.exists(path):
                subprocess.Popen([path])
                return True
    try:
        os.startfile(name)
        return True
    except Exception:
        return False


def open_app(args):
    raw = args.get("app_name", "")
    if not raw:
        return "Kaunsa app kholna hai?"
    name = _normalize(raw)
    print(f"[open_app] raw={raw} cleaned={name}")

    key = _find_in(FOLDERS, name)
    if key:
        path = FOLDERS[key]
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        try:
            os.startfile(path)
            return f"{key} folder khol raha hoon..."
        except Exception as e:
            return f"{key} folder nahi khula: {e}"

    key = _find_in(WEBSITES, name)
    if key:
        webbrowser.open(WEBSITES[key])
        return f"{key} khol raha hoon..."

    key = _find_in(APP_ALIASES, name)
    exe = APP_ALIASES.get(key, name) if key else name

    if platform.system() == "Windows":
        if _launch_windows(exe):
            return f"{name} khol raha hoon..."
        return f"{name} nahi mila."
    return f"{name} nahi mila."


def take_screenshot(_args=None):
    if not _MSS:
        return "Screenshot ke liye: pip install mss"
    try:
        folder = os.path.join(_HOME, "Pictures", "Screenshots")
        os.makedirs(folder, exist_ok=True)
        fname = "screenshot_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        path = os.path.join(folder, fname)
        with mss.mss() as sct:
            sct.shot(output=path)
        os.startfile(folder)
        return f"Screenshot le liya."
    except Exception as e:
        return f"Screenshot fail: {e}"


def open_screenshots(_args=None):
    folder = os.path.join(_HOME, "Pictures", "Screenshots")
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    try:
        os.startfile(folder)
        return "Screenshots folder khol raha hoon."
    except Exception as e:
        return f"Folder nahi khula: {e}"


def play_youtube(args):
    """Simple YouTube - search + first video URL open (fast)."""
    query = args.get("query", "").strip()
    if not query:
        webbrowser.open("https://youtube.com")
        return "YouTube khol raha hoon."

    if not _YTDLP:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        webbrowser.open(url)
        return f"YouTube pe {query} search kar raha hoon."

    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch1",
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info and info.get("entries"):
                first = info["entries"][0]
                video_id = first.get("id")
                title = first.get("title", query)
                if video_id:
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    webbrowser.open(url)
                    return f"'{title}' baja raha hoon."
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        webbrowser.open(url)
        return f"YouTube pe {query} search kar raha hoon."
    except Exception as e:
        print(f"[youtube fail] {e}")
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        webbrowser.open(url)
        return f"YouTube pe {query} search kar raha hoon."


def browse(args):
    """Full browser agent - Gemini + browser-use."""
    task = args.get("task", "").strip()
    if not task:
        return "Boss, kya karna hai browser mein?"
    try:
        from browser_agent import browse as _browse
        return _browse({"task": task})
    except Exception as e:
        return f"Browser agent fail: {e}"


def play_spotify(args):
    query = args.get("query", "").strip()
    if not query:
        webbrowser.open("https://open.spotify.com")
        return "Spotify khol raha hoon."
    url = "https://open.spotify.com/search/" + urllib.parse.quote(query)
    webbrowser.open(url)
    time.sleep(4)
    if _PYAUTOGUI:
        try:
            time.sleep(1)
            for _ in range(3):
                pyautogui.press("tab")
                time.sleep(0.2)
            pyautogui.press("enter")
            return f"Spotify pe {query} play kar raha hoon."
        except Exception as e:
            print(f"[spotify click fail] {e}")
    return f"Spotify pe {query} search kar diya."


def _press_key(key, times=1):
    if not _PYAUTOGUI:
        return False
    for _ in range(times):
        pyautogui.press(key)
        time.sleep(0.05)
    return True


def volume_up(args):
    n = int(args.get("steps", 5))
    if _press_key("volumeup", n):
        return f"Volume {n} step badha diya."
    return "pyautogui chahiye."


def volume_down(args):
    n = int(args.get("steps", 5))
    if _press_key("volumedown", n):
        return f"Volume {n} step kam kar diya."
    return "pyautogui chahiye."


def volume_mute(_args=None):
    if _press_key("volumemute"):
        return "Mute kar diya."
    return "pyautogui chahiye."


def next_track(_args=None):
    if _press_key("nexttrack"):
        return "Agla gaana."
    return "pyautogui chahiye."


def prev_track(_args=None):
    if _press_key("prevtrack"):
        return "Pichla gaana."
    return "pyautogui chahiye."


def play_pause(_args=None):
    if _press_key("playpause"):
        return "Play/Pause toggle kiya."
    return "pyautogui chahiye."


def lock_pc(_args=None):
    try:
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "PC lock kar diya."
    except Exception as e:
        return f"Lock fail: {e}"
    return "Sirf Windows pe."


def shutdown_pc(args):
    mode = args.get("mode", "shutdown")
    try:
        if platform.system() != "Windows":
            return "Sirf Windows pe."
        if mode == "restart":
            os.system("shutdown /r /t 10")
            return "10 second mein restart ho raha hai."
        if mode == "cancel":
            os.system("shutdown /a")
            return "Cancel kar diya."
        os.system("shutdown /s /t 10")
        return "10 second mein shutdown. Cancel karne ke liye bolo."
    except Exception as e:
        return f"Fail: {e}"


def copy_to_clipboard(args):
    text = args.get("text", "")
    try:
        subprocess.run("clip", input=text.encode("utf-8"), shell=True, check=True)
        return "Clipboard mein copy kar diya."
    except Exception as e:
        return f"Copy fail: {e}"


def type_text(args):
    text = args.get("text", "")
    if not _PYAUTOGUI:
        return "pyautogui chahiye."
    try:
        time.sleep(1)
        pyautogui.typewrite(text, interval=0.03)
        return "Type kar diya."
    except Exception as e:
        return f"Typing fail: {e}"


def search_file(args):
    name = args.get("name", "").strip().lower()
    where = args.get("where", "downloads").lower()
    if not name:
        return "Kaunsi file dhundhni hai?"
    root = FOLDERS.get(where, os.path.join(_HOME, "Downloads"))
    matches = []
    try:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if name in f.lower():
                    matches.append(os.path.join(dirpath, f))
                    if len(matches) >= 5:
                        break
            if len(matches) >= 5:
                break
    except Exception as e:
        return f"Search fail: {e}"
    if not matches:
        return f"{name} naam ki file nahi mili {where} mein."
    parent = os.path.dirname(matches[0])
    os.startfile(parent)
    return f"{len(matches)} file mili. Pehli: {os.path.basename(matches[0])}"


def web_search(args):
    q = args.get("query", "").strip()
    if not q:
        return "Kya search karna hai?"
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(q))
    return f"Google pe {q} search kar raha hoon."


def close_browser(_args=None):
    """Chromium browser ko band karo (jab user bole)."""
    try:
        import subprocess
        if platform.system() == "Windows":
            # Sirf browser-use ka chromium band karo
            subprocess.run(
                ["taskkill", "/F", "/IM", "chrome.exe", "/FI", "WINDOWTITLE eq *"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Chromium bhi try
            subprocess.run(
                ["taskkill", "/F", "/IM", "chromium.exe"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return "Browser band kar diya."
    except Exception as e:
        return f"Browser band nahi hua: {e}"
    return "Sirf Windows pe."



TOOLS = {
    "get_time": get_time,
    "get_weather": get_weather,
    "open_app": open_app,
    "take_screenshot": take_screenshot,
    "open_screenshots": open_screenshots,
    "play_youtube": play_youtube,
    "browse": browse,
    "close_browser": close_browser,
    "play_spotify": play_spotify,
    "volume_up": volume_up,
    "volume_down": volume_down,
    "volume_mute": volume_mute,
    "next_track": next_track,
    "prev_track": prev_track,
    "play_pause": play_pause,
    "lock_pc": lock_pc,
    "shutdown_pc": shutdown_pc,
    "copy_to_clipboard": copy_to_clipboard,
    "type_text": type_text,
    "search_file": search_file,
    "web_search": web_search,
    "remember": tool_remember,
    "recall": tool_recall,
    "forget": tool_forget,
    "note": tool_note,
    "list_notes": tool_list_notes,
}
