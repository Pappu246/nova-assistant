import time
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write as write_wav
import whisper
import tempfile
import os

SAMPLE_RATE = 16000
RECORD_SECONDS = 6
CALIB_SECONDS = 2

print("Whisper model load ho raha hai...")
_model = whisper.load_model("small")
print("Whisper ready hai.")

print(f"{CALIB_SECONDS} second chup raho...")
_calib = sd.rec(int(CALIB_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                channels=1, dtype="int16")
sd.wait()
AMBIENT = float(np.abs(_calib).mean())
PEAK_THRESHOLD = max(AMBIENT * 12.0, 900)
print(f"Calibrated: ambient={AMBIENT:.0f}, peak_thr={PEAK_THRESHOLD:.0f}")

_HINT = (
    "NOVA voice commands. time kya hai, chrome kholo, youtube kholo, "
    "notepad kholo, downloads kholo, screenshot lo, screenshot dikhao, "
    "gaana bajao, volume badhao, volume kam karo, mute karo, lock karo, "
    "shutdown karo, restart karo, bye, exit"
)

_HALLUCINATIONS = [
    "song play", "play song", "subscribe", "thanks for watching",
    "thank you", "please subscribe", "amara.org", "subtitle",
    "subtitles", "www.", "caption", "captions", "editor",
    "amazing", "yeah", "hmm", "okay", "hello everyone",
    "ご視聴", "ありがとう", "チャンネル登録",
    "nozomi", "no words", "请不吝点赞",
    "感谢观看", "訂閱", "點贊", "打賞",
]


def _is_repetition(text):
    words = text.lower().split()
    if len(words) < 6:
        return False
    if len(set(words)) / len(words) < 0.4:
        return True
    return False


def listen():
    print("\nTayyar ho jao...")
    time.sleep(0.3)
    print("BOL SAKTE HO ABHI!")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    flat = audio.flatten().astype(np.float32)
    abs_flat = np.abs(flat)
    avg = float(abs_flat.mean())
    peak = float(abs_flat.max())
    print(f"Samajh raha hoon... (avg={avg:.0f}, peak={peak:.0f}, thr={PEAK_THRESHOLD:.0f})")

    if peak < PEAK_THRESHOLD:
        print("(chup tha, skip)")
        return ""

    gain = min(8000.0 / max(peak, 1), 30.0)
    boosted = np.clip(flat * gain, -32768, 32767).astype(np.int16).reshape(-1, 1)
    print(f"(amplified {gain:.1f}x)")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        write_wav(tmp.name, SAMPLE_RATE, boosted)
        tmp_path = tmp.name

    try:
        result = _model.transcribe(
            tmp_path,
            fp16=False,
            language=None,
            initial_prompt=_HINT,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            condition_on_previous_text=False,
            temperature=0.0,
        )
        text = result["text"].strip()
    finally:
        os.remove(tmp_path)

    low = text.lower().strip()
    if len(low) < 2:
        return ""
    if _is_repetition(low):
        print(f"(repetition: {text[:40]}...)")
        return ""
    if any(h in low for h in _HALLUCINATIONS):
        print(f"(hallucination: {text[:40]}...)")
        return ""

    return text
