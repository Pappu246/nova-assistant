"""
NOVA Real-Time STT - Groq Whisper (cloud, 99% accurate) + local fallback.
"""
import os
import tempfile
import time

import numpy as np

try:
    from scipy.io.wavfile import write as write_wav
    _SCIPY = True
except Exception:
    _SCIPY = False

try:
    from groq import Groq
    _GROQ = True
except Exception:
    _GROQ = False

try:
    from faster_whisper import WhisperModel
    _FW = True
except Exception:
    _FW = False


SAMPLE_RATE = 16000

# Groq models (priority)
GROQ_MODELS = ["whisper-large-v3", "whisper-large-v3-turbo"]

_HINT = (
    "mera naam pappu hai. mera dost sahid pinkesh gopal jahid hai. "
    "time kya hai. chrome kholo. youtube kholo. gaana bajao. "
    "bihar cm kaun hai. aaj ki news. bitcoin price. "
    "mera channel kaise banau. mera portfolio banao. "
    "screenshot lo. volume badhao. mute karo. bye. stop. ruko."
)

_HALLUCINATIONS = [
    "song play", "play song", "subscribe", "thanks for watching",
    "thank you", "please subscribe", "amara.org", "subtitle",
    "subtitles", "www.", "caption", "captions",
    "ご視聴", "ありがとう",
]

# Local fallback model
_local_model = None


def _normalize_audio(audio_int16):
    """Normalize to peak=12000 (avoid clip, boost weak)."""
    flat = audio_int16.astype(np.float32).flatten()
    peak = float(np.abs(flat).max())
    if peak < 100:
        return flat.astype(np.int16)
    target = 12000.0
    gain = min(target / peak, 5.0)
    return np.clip(flat * gain, -32768, 32767).astype(np.int16)


def _transcribe_groq(audio_int16):
    """Groq Whisper API - fast, accurate."""
    if not _GROQ:
        return None

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None

    # Save to temp WAV
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        write_wav(tmp_path, SAMPLE_RATE, audio_int16)
    except Exception as e:
        print("[rt_stt] wav save fail: " + str(e)[:60])
        return None

    try:
        client = Groq(api_key=key)
        for model in GROQ_MODELS:
            try:
                t0 = time.time()
                with open(tmp_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        file=(os.path.basename(tmp_path), f.read()),
                        model=model,
                        language="hi",
                        prompt=_HINT[:200],
                        response_format="text",
                    )
                dt = time.time() - t0
                text = (result if isinstance(result, str) else result.text).strip()
                if text:
                    print("[rt_stt] Groq " + model + " (" + str(round(dt, 2)) + "s)")
                    return text
            except Exception as e:
                err = str(e)[:80]
                if any(x in err for x in ["503", "429", "unavailable"]):
                    continue
                print("[rt_stt] Groq " + model + " fail: " + err)
                continue
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return None


def _load_local_model():
    global _local_model
    if _local_model is not None:
        return _local_model
    if not _FW:
        return None
    try:
        _local_model = WhisperModel(
            "base", device="cpu", compute_type="int8", cpu_threads=4
        )
        print("[rt_stt] local faster-whisper base loaded")
    except Exception as e:
        print("[rt_stt] local load fail: " + str(e)[:60])
        _local_model = None
    return _local_model


def _transcribe_local(audio_int16):
    """Local faster-whisper fallback."""
    model = _load_local_model()
    if model is None:
        return ""

    audio_float = audio_int16.astype(np.float32) / 32768.0

    try:
        segments, info = model.transcribe(
            audio_float,
            language=None,
            task="transcribe",
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
            temperature=0.0,
            vad_filter=False,
            initial_prompt=_HINT,
            without_timestamps=True,
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text
    except Exception as e:
        print("[rt_stt] local fail: " + str(e)[:60])
        return ""


def transcribe(audio_int16, sample_rate=16000):
    """
    Main STT function.
    Try Groq Whisper first (fast + accurate), fall back to local.
    """
    if len(audio_int16) < sample_rate * 0.3:
        return ""

    # Normalize
    normalized = _normalize_audio(audio_int16)

    # Try Groq first
    text = _transcribe_groq(normalized)
    if text:
        # Filter hallucinations
        low = text.lower()
        for h in _HALLUCINATIONS:
            if h in low:
                print("[rt_stt] hallucination skip: " + text[:40])
                return ""
        return text

    # Fallback: local
    print("[rt_stt] Groq failed, using local")
    text = _transcribe_local(normalized)

    low = text.lower()
    for h in _HALLUCINATIONS:
        if h in low:
            return ""
    return text


# ============ TEST ============
if __name__ == "__main__":
    import sounddevice as sd

    print("=" * 55)
    print("  rt_stt.py TEST (Groq Whisper first)")
    print("=" * 55)
    print()

    MIC_DEVICE = 1
    print("Mic [1] - 5 second bolo")
    print("Bolo: 'Mera channel kaise banau'")
    print()

    audio = sd.rec(int(5 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="int16", device=MIC_DEVICE)
    sd.wait()
    peak = float(np.abs(audio).max())
    print("Recorded peak: " + str(int(peak)))
    print()

    t0 = time.time()
    text = transcribe(audio.flatten())
    dt = time.time() - t0

    print()
    print("STT time: " + str(round(dt, 2)) + "s")
    print("Text: " + text)
    print("=" * 55)
