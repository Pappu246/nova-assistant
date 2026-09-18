"""
NOVA ki awaaz — edge-tts super natural + playsound3 native audio.
"""

import platform
import subprocess
import os
import asyncio
import tempfile
import time as _time

try:
    import edge_tts
    _EDGE = True
except ImportError:
    _EDGE = False

try:
    from playsound3 import playsound
    _PLAY = True
except ImportError:
    _PLAY = False

# ============ VOICE SETTINGS ============
# Sabse natural: Swara (female, expressive)
VOICE = "hi-IN-SwaraNeural"
RATE = "+0%"
PITCH = "+0Hz"

# Alternatives (agar Swara pasand na aaye):
# VOICE = "hi-IN-MadhurNeural"    # male, thoda heavy
# VOICE = "en-IN-NeerjaNeural"    # English-Indian female
# VOICE = "en-IN-PrabhatNeural"   # English-Indian male
# VOICE = "en-US-AriaNeural"      # US female - F.R.I.D.A.Y. jaisi
# VOICE = "en-GB-RyanNeural"      # British male - Jarvis jaisi
# ========================================


def _cleanup_old():
    try:
        td = tempfile.gettempdir()
        for f in os.listdir(td):
            if f.startswith("nova_speech_") and f.endswith(".mp3"):
                try:
                    os.remove(os.path.join(td, f))
                except Exception:
                    pass
    except Exception:
        pass


def _play_mp3(path):
    if not _PLAY:
        return False
    try:
        playsound(path, block=True)
        return True
    except Exception as e:
        print(f"[playsound] {e}")
        return False


def _try_edge_tts(text, voice, rate, pitch, path):
    async def _gen():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await comm.save(path)

    try:
        asyncio.run(_gen())
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception as e:
        print(f"[edge-tts fail] {e}")
        return False


def speak(text):
    if not text:
        return
    text = text.strip()
    if not text:
        return

    print(f"NOVA: {text}")

    if _EDGE and _PLAY:
        _cleanup_old()
        fname = f"nova_speech_{int(_time.time() * 1000)}.mp3"
        path = os.path.join(tempfile.gettempdir(), fname)

        if _try_edge_tts(text, VOICE, RATE, PITCH, path):
            if _play_mp3(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
                return

        print("[bolo] edge-tts ya playsound fail")

    # fallback - print only, robotic SAPI5 nahi
    print(f"[NOVA text only] {text}")
