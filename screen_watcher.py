"""
NOVA Screen Watcher - screen dekhta hai, khud comments karta hai.
"""
import os
import time
import io
import hashlib
import threading

try:
    import mss
    _MSS = True
except Exception:
    _MSS = False

try:
    from google import genai
    from google.genai import types as gtypes
    _GEMINI = True
except Exception:
    _GEMINI = False

try:
    from PIL import Image
    _PIL = True
except Exception:
    _PIL = False


# Gemini models - priority order
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

_watch_active = False
_watch_thread = None
_last_comment_time = 0
_last_screen_hash = None
_recent_screens = []


def _capture_screen():
    if not _MSS:
        return None
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            if _PIL:
                img = Image.frombytes("RGB", shot.size, shot.rgb)
                img.thumbnail((1280, 720))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=70)
                return buf.getvalue()
            return None
    except Exception as e:
        print(f"[screen] capture fail: {e}")
        return None


def _hash_bytes(data):
    if not data:
        return None
    return hashlib.md5(data).hexdigest()[:16]


def _build_prompt(context=""):
    return f"""You are NOVA - Boss's AI companion. Boss tumhare saath Hinglish mein baat karta hai.

Ye Boss ke laptop ka current screen hai. Tumhe decide karna hai ki kuch BOLNA chahiye ya nahi.

{context}

RULES:
1. Agar screen pe kuch INTERESTING hai (error, problem, naya kuch khula) -> ACTIONABLE suggestion do
   - Sirf problem mat batao, SOLUTION bhi batao
   - Jaise: "Boss, error aa gaya - 'npm install' chalao theek ho jayega"
   - Jaise: "Boss, Git mein conflict hai - 'git status' dekho phir 'git merge --abort' try karo"
2. Agar screen pe normal cheez hai -> "SILENT"
3. Agar Boss kuch confusing kar raha -> "Boss, X mein help chahiye? Main bata du kaise?"
4. Max 2 lines, Hinglish mein, "Boss" se shuru
5. Agar pichhle 2 min mein bola tha -> "SILENT"

Examples:
- Python error ModuleNotFoundError -> "Boss, ye module missing hai — terminal mein 'pip install <module>' chala do, theek ho jayega."
- Git conflict -> "Boss, Git merge conflict hai — 'git status' dekho, phir 'git merge --abort' try karo."
- WhatsApp -> "Boss, WhatsApp khul gaya — kisi ko message karna hai to naam batao, main likh du."
- YouTube -> "Boss, YouTube chalu hai — koi specific video dhundhni hai?"
- Coding editor -> "Boss, code likh rahe ho — koi doubt ho to code paste karo, main help karungi."
- Shopping site -> "Boss, shopping kar rahe ho — price compare karna hai?"
- Normal desktop -> "SILENT"

Agar bolna chahiye to SIRF ye format do:
SPEAK: <your Hinglish actionable message>

Warna sirf likho: SILENT"""


def _analyze_screen(image_bytes, context=""):
    """Gemini se analyze karo - multiple models try karo."""
    if not _GEMINI or not image_bytes:
        return False, ""

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return False, ""

    prompt = _build_prompt(context)
    image_part = gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")

    for model_name in GEMINI_MODELS:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, image_part],
            )
            text = (response.text or "").strip()

            if not text:
                continue

            upper = text.upper()
            if upper == "SILENT" or upper.startswith("SILENT"):
                return False, ""

            if upper.startswith("SPEAK:"):
                msg = text[6:].strip()
                if msg:
                    return True, msg

            if len(text) < 250 and not text.startswith("```"):
                return True, text

            return False, ""

        except Exception as e:
            err = str(e)[:120]
            if any(x in err for x in ["503", "UNAVAILABLE", "429", "overload", "high demand"]):
                print(f"[screen {model_name}] busy, try next...")
                continue
            print(f"[screen {model_name}] {err}")
            continue

    print("[screen] Saare models busy, skip")
    return False, ""


def _watch_loop(on_speak_callback, interval=25):
    global _watch_active, _last_comment_time, _last_screen_hash

    while _watch_active:
        try:
            time.sleep(interval)
            if not _watch_active:
                break

            # Minimum 45 sec gap between comments
            if time.time() - _last_comment_time < 45:
                continue

            shot = _capture_screen()
            if not shot:
                continue

            h = _hash_bytes(shot)
            if h == _last_screen_hash:
                continue
            _last_screen_hash = h

            context = ""
            if _recent_screens:
                context = "Recent comments you made: " + " | ".join(_recent_screens[-2:])

            should_speak, msg = _analyze_screen(shot, context)

            if should_speak and msg:
                _recent_screens.append(msg)
                if len(_recent_screens) > 5:
                    _recent_screens.pop(0)

                _last_comment_time = time.time()
                print(f"[screen-watcher] SPEAK: {msg}")

                try:
                    on_speak_callback(msg)
                except Exception as e:
                    print(f"[screen-watcher callback] {e}")

        except Exception as e:
            print(f"[screen-watcher loop] {e}")
            time.sleep(5)


def start_watching(on_speak_callback, interval=30):
    global _watch_active, _watch_thread
    if _watch_active:
        return False
    _watch_active = True
    _watch_thread = threading.Thread(
        target=_watch_loop,
        args=(on_speak_callback, interval),
        daemon=True,
    )
    _watch_thread.start()
    print(f"[screen-watcher] Started (interval={interval}s)")
    return True


def stop_watching():
    global _watch_active
    _watch_active = False
    print("[screen-watcher] Stopped")


if __name__ == "__main__":
    from bolo import speak

    def test_speak(msg):
        print(f">>> SPEAKING: {msg}")
        speak(msg)

    start_watching(test_speak, interval=15)
    print("Test mode - 90 sec dekho screen...")
    time.sleep(90)
    stop_watching()
