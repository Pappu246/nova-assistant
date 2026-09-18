"""
NOVA ki awaaz - Groq Orpheus TTS + edge-tts fallback.
"""
import os
import tempfile
import time as _time

import numpy as np

# ============ CONFIG ============
VOICE = "leah"   # Orpheus voices
# Options:
#   tara  - female, natural
#   leah  - female, warm
#   jess  - female, expressive
#   mia   - female, soft
#   zoe   - female, bright
#   leo   - male, calm
#   dan   - male, deep (JARVIS feel)
#   zac   - male, energetic
# ================================

try:
    from groq import Groq
    _GROQ = True
except Exception:
    _GROQ = False

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


def _groq_tts(text, path):
    if not _GROQ:
        return False
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("[groq] API key nahi mili")
        return False
    try:
        client = Groq(api_key=key)
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice=VOICE,
            input=text,
            response_format="wav",
        )
        response.write_to_file(path)
        return os.path.exists(path) and os.path.getsize(path) > 1000
    except Exception as e:
        print(f"[groq tts fail] {str(e)[:150]}")
        return False


def _edge_tts(text, path):
    try:
        import edge_tts, asyncio
        async def _gen():
            c = edge_tts.Communicate(text, "en-US-AndrewMultilingualNeural",
                                     rate="+0%", pitch="+0Hz")
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
            if f.startswith("nova_voice_") and (f.endswith(".wav") or f.endswith(".mp3")):
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

    # Try 1: Groq Orpheus
    wav_path = os.path.join(tempfile.gettempdir(), f"nova_voice_{ts}.wav")
    if _groq_tts(text, wav_path):
        print("[voice] Groq Orpheus")
        if _play_file(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
            return

    # Try 2: edge-tts (multilingual neural - natural)
    mp3_path = os.path.join(tempfile.gettempdir(), f"nova_voice_{ts}.mp3")
    if _edge_tts(text, mp3_path):
        print("[voice] edge-tts multilingual")
        if _play_file(mp3_path):
            try:
                os.remove(mp3_path)
            except Exception:
                pass
            return

    # Try 3: SAPI5
    _sapi(text)
