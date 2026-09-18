"""
NOVA ki awaaz - edge-tts Ava (female multilingual) + fallbacks.
"""
import os
import tempfile
import time as _time

import numpy as np

# ============ CONFIG ============
EDGE_VOICE = "en-US-EmmaMultilingualNeural"   # Female, ultra natural
EDGE_RATE = "+0%"
EDGE_PITCH = "+0Hz"
# ================================

try:
    from playsound3 import playsound
    _PLAY = True
except Exception:
    _PLAY = False

try:
    import sounddevice as sd
    _SD = True
except Exception:
    _SD = False


def _play_file(path):
    if _PLAY:
        try:
            playsound(path, block=True)
            return True
        except Exception as e:
            print(f"[playsound fail] {e}")
    if _SD:
        try:
            import wave
            with wave.open(path, "rb") as wf:
                sr = wf.getframerate()
                data = wf.readframes(wf.getnframes())
                samples = np.frombuffer(data, dtype=np.int16)
                sd.play(samples, samplerate=sr)
                sd.wait()
                return True
        except Exception as e:
            print(f"[sounddevice fail] {e}")
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


def speak(text):
    if not text:
        return
    text = text.strip()
    if not text:
        return

    print(f"NOVA: {text}")
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
