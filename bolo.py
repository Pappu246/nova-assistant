"""
NOVA ki awaaz - stop support ke saath.
"""
import os
import tempfile
import time as _time
import threading

import numpy as np

EDGE_VOICE = "hi-IN-MadhurNeural"
EDGE_RATE = "+5%"
EDGE_PITCH = "+0Hz"

_stop_flag = threading.Event()
_esc_started = False


def stop_speaking():
    """TTS turant band."""
    _stop_flag.set()
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
    except Exception:
        pass
    # Note: sd.stop() removed - it kills wake listener stream
    # pygame stop is enough for TTS


def is_stopped():
    return _stop_flag.is_set()


def start_esc_listener():
    """Esc = stop. Global keyboard listener."""
    global _esc_started
    if _esc_started:
        return
    _esc_started = True
    try:
        from pynput import keyboard

        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    print("[ESC] stop!")
                    stop_speaking()
            except Exception:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
        print("[bolo] Esc = stop, ready")
    except ImportError:
        print("[bolo] pynput nahi mila - 'pip install pynput'")


try:
    from playsound3 import playsound
    _PLAY = True
except Exception:
    _PLAY = False


def _play_file(path):
    if _PLAY:
        try:
            # Play in chunks so we can check stop flag
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            try:
                pygame.mixer.music.set_volume(0.6)
            except Exception:
                pass
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if _stop_flag.is_set():
                    pygame.mixer.music.stop()
                    return True
                pygame.time.wait(80)
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[pygame fail] {e}")
            # Fallback: playsound (can't be interrupted)
            try:
                playsound(path, block=True)
                return True
            except Exception:
                return False
    return False


def _edge_tts(text, path):
    try:
        import edge_tts, asyncio
        async def _gen():
            c = edge_tts.Communicate(text, EDGE_VOICE,
                                     rate=EDGE_RATE, pitch=EDGE_PITCH)
            await c.save(path)
        asyncio.run(_gen())
        return os.path.exists(path) and os.path.getsize(path) > 500
    except Exception as e:
        print(f"[edge-tts fail] {str(e)[:80]}")
        return False


def _sapi(text):
    try:
        import platform, subprocess
        if platform.system() != "Windows":
            print(f"[NOVA] {text}")
            return
        safe = text.replace("'", "''")
        ps = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.Rate = 1;"
            f"$s.Speak('{safe}');"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=False, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[SAPI fail] {e}")


def _cleanup_old():
    try:
        td = tempfile.gettempdir()
        for f in os.listdir(td):
            if f.startswith("nova_voice_"):
                try:
                    os.remove(os.path.join(td, f))
                except Exception:
                    pass
    except Exception:
        pass




import re as _re

def _clean_text_for_speech(text):
    """Emoji, markdown, symbols hatao - sirf clean sentence bache."""
    if not text:
        return ""
    t = text

    # Remove code blocks ```...```
    t = _re.sub(r"```[\s\S]*?```", " code block ", t)
    # Remove inline code `...`
    t = _re.sub(r"`([^`]*)`", r"\1", t)
    # Remove markdown bold/italic
    t = _re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = _re.sub(r"\*([^*]+)\*", r"\1", t)
    t = _re.sub(r"__([^_]+)__", r"\1", t)
    t = _re.sub(r"_([^_]+)_", r"\1", t)
    # Remove headings # ## ###
    t = _re.sub(r"^#+\s*", "", t, flags=_re.MULTILINE)
    # Remove table pipes and dashes
    t = _re.sub(r"\|", " ", t)
    t = _re.sub(r"^[-\s]+$", "", t, flags=_re.MULTILINE)
    # Remove list bullets
    t = _re.sub(r"^\s*[-*+]\s+", "", t, flags=_re.MULTILINE)
    t = _re.sub(r"^\s*\d+\.\s+", "", t, flags=_re.MULTILINE)
    # Remove markdown links [text](url)
    t = _re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    # Remove URLs
    t = _re.sub(r"https?://\S+", " link ", t)
    # Remove emoji (unicode ranges)
    emoji_pattern = _re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002700-\U000027BF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U0001F004-\U0001F0CF"
        "\U0001F191-\U0001F251"
        "\U0001F018-\U0001F270"
        "\U000025A0-\U000025FF"
        "\U00002B00-\U00002BFF"
        "\U0000FE00-\U0000FE0F"
        "\U0001F000-\U0001F02F"
        "\U0001F100-\U0001F1FF"
        "\U0001F200-\U0001F2FF"
        "]+",
        flags=_re.UNICODE
    )
    t = emoji_pattern.sub("", t)
    # Remove other symbols
    t = _re.sub(r"[★☆♥♦●○◆◇▬▲►▼◄]", " ", t)
    # Word fixes
    for old, new in _TTS_REPLACE.items():
        t = t.replace(old, new)

    # Remove parentheses content (TTS reads them as "open bracket" etc)
    t = _re.sub(r"\([^)]*\)", " ", t)
    t = _re.sub(r"\[[^\]]*\]", " ", t)
    t = _re.sub(r"\{[^}]*\}", " ", t)

    # Remove special chars (TTS padhta hai)
    t = t.replace("&", " aur ")
    t = t.replace("@", " at ")
    t = t.replace("#", " ")
    t = t.replace("~", " ")
    t = t.replace("^", " ")
    t = t.replace("|", " ")
    t = t.replace("\\", " ")
    t = t.replace("/", " ")
    t = t.replace("--", " ")
    t = t.replace("...", ".")
    t = t.replace("..", ".")

    # Remove quotes (TTS "quote unquote" bolta)
    t = t.replace("\"", "")
    t = t.replace("'", "")
    t = t.replace("\u2018", "")
    t = t.replace("\u2019", "")
    t = t.replace("\u201c", "")
    t = t.replace("\u201d", "")

    # Remove multiple punctuation like !! or ?? or ,,
    t = _re.sub(r"[!]{2,}", "!", t)
    t = _re.sub(r"[?]{2,}", "?", t)
    t = _re.sub(r"[,]{2,}", ",", t)
    t = _re.sub(r"[.]{2,}", ".", t)

    # Remove standalone commas at end (common issue)
    t = _re.sub(r"\s+,", ",", t)
    t = _re.sub(r",\s*,", ",", t)

    # Remove any remaining unusual symbols
    t = _re.sub(r"[<>*_=+\[\]{}()]", " ", t)

    # Clean multiple spaces/newlines
    t = _re.sub(r"\s+", " ", t)
    t = t.strip()
    return t




# ============ TTS WORD FIXES ============
_TTS_REPLACE = {
    "gup-shup": "baat cheet",
    "gup shup": "baat cheet",
    "chit-chat": "halki baat",
    "chit chat": "halki baat",
    "gupchup": "baat cheet",
    "chitchat": "halki baat",
    "email": "ee mail",
    "Email": "ee mail",
    "URL": "you are ell",
    "AI": "ay eye",
    "CEO": "see ee oh",
    "API": "ay pee eye",
    "PDF": "pee dee eff",
    "IP": "eye pee",
}


def _fix_tts_words(text):
    """Problematic words replace karo."""
    if not text:
        return text
    t = text
    for old, new in _TTS_REPLACE.items():
        t = t.replace(old, new)
    return t


def speak(text):
    if not text:
        return
    text = text.strip()
    if not text:
        return

    _stop_flag.clear()

    # Clean emoji/markdown
    clean = _clean_text_for_speech(text)
    if not clean:
        return

    print(f"NOVA: {clean}")
    text = clean

    _cleanup_old()
    ts = int(_time.time() * 1000)
    mp3_path = os.path.join(tempfile.gettempdir(), f"nova_voice_{ts}.mp3")

    if _edge_tts(text, mp3_path):
        print(f"[voice] edge-tts {EDGE_VOICE}")
        if _play_file(mp3_path):
            try:
                os.remove(mp3_path)
            except Exception:
                pass
            return

    _sapi(text)
