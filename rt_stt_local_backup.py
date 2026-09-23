"""
NOVA Real-Time STT - small model for speed.
"""
import os
import numpy as np

try:
    from faster_whisper import WhisperModel
    _FW = True
except Exception as e:
    print("[rt_stt] import fail: " + str(e)[:80])
    _FW = False

_model = None
SAMPLE_RATE = 16000

_HINT = (
    "mera naam pappu hai. mera dost sahid pinkesh gopal jahid hai. "
    "time kya hai. chrome kholo. youtube kholo. gaana bajao. "
    "screenshot lo. volume badhao. volume kam karo. mute karo. "
    "bye. stop. ruko. kya kar rahe ho. kaise ho. theek hai."
)

_HALLUCINATIONS = [
    "song play", "play song", "subscribe", "thanks for watching",
    "thank you", "please subscribe", "amara.org", "subtitle",
    "subtitles", "www.", "caption", "captions",
    "ご視聴", "ありがとう",
]


def _load_model():
    global _model
    if _model is not None or not _FW:
        return _model
    try:
        # small + int8 = FAST on CPU (~1s per 5s audio)
        _model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
        )
        print("[rt_stt] faster-whisper base (int8) loaded")
    except Exception as e:
        print("[rt_stt] load fail: " + str(e)[:80])
        _model = None
    return _model


def _normalize_audio(audio_int16):
    """Normalize to peak=10000 (prevents clip, boosts weak)."""
    flat = audio_int16.astype(np.float32).flatten()
    peak = float(np.abs(flat).max())
    if peak < 100:
        return flat.astype(np.int16)
    target = 10000.0
    gain = min(target / peak, 5.0)  # cap gain to avoid noise boost
    return np.clip(flat * gain, -32768, 32767).astype(np.int16)


def transcribe(audio_int16, sample_rate=16000):
    model = _load_model()
    if model is None:
        return ""
    if len(audio_int16) < sample_rate * 0.3:
        return ""

    normalized = _normalize_audio(audio_int16)
    audio_float = normalized.astype(np.float32) / 32768.0

    try:
        segments, info = model.transcribe(
            audio_float,
            language=None,
            task="transcribe",
            beam_size=1,          # FAST
            best_of=1,
            condition_on_previous_text=False,
            temperature=0.0,
            vad_filter=False,
            initial_prompt=_HINT,
            without_timestamps=True,
        )
        text = " ".join(seg.text for seg in segments).strip()
    except Exception as e:
        print("[rt_stt] fail: " + str(e)[:80])
        return ""

    low = text.lower()
    for h in _HALLUCINATIONS:
        if h in low:
            print("[rt_stt] hallucination: " + text[:40])
            return ""
    return text


if __name__ == "__main__":
    import sounddevice as sd
    import time

    print("=" * 55)
    print("  rt_stt.py FAST TEST")
    print("=" * 55)
    _load_model()
    print()
    MIC_DEVICE = 1
    print("Mic [" + str(MIC_DEVICE) + "] - 5s bolo")
    print("Bolo: 'Mera naam Pappu hai, time kya hai'")
    print("Target: peak 5000-15000 (door bolo agar clip ho)")
    print()

    t0 = time.time()
    audio = sd.rec(int(5 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="int16", device=MIC_DEVICE)
    sd.wait()
    peak = float(np.abs(audio).max())
    print("Recorded: peak=" + str(int(peak)))

    if peak < 500:
        print("Bahut kamzor"); exit()
    if peak > 30000:
        print("WARNING: clipping - mic se door bolo")

    t0 = time.time()
    text = transcribe(audio.flatten())
    dt = time.time() - t0

    print()
    print("STT time: " + str(round(dt, 2)) + "s")
    print("Text: " + text)
    print("=" * 55)
