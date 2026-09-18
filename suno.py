"""
NOVA ke kaan - turant detect, fast transcribe.
"""
import time
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write as write_wav
import whisper
import tempfile
import os

SAMPLE_RATE = 16000
CALIB_SECONDS = 2
MAX_RECORD_SECONDS = 15
SILENCE_AFTER_VOICE = 0.8    # bolna band -> 0.8 sec -> stop
CHUNK = 0.08                 # 80ms chunks (jaldi detect)

print("Whisper base load ho raha hai (fast + accurate)...")
_model = whisper.load_model("base")   # small se 3x tez
print("Whisper ready hai.")

print(f"{CALIB_SECONDS} second chup raho...")
_calib = sd.rec(int(CALIB_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                channels=1, dtype="int16")
sd.wait()
AMBIENT = float(np.abs(_calib).mean())
# Voice start threshold (kam - soft voice bhi pakde)
VOICE_START = max(AMBIENT * 2.5, 500)
# Silence threshold (chhota - bas thoda upar)
SILENCE_LEVEL = max(AMBIENT * 1.8, 350)
print(f"Calibrated: ambient={AMBIENT:.0f}, start={VOICE_START:.0f}, silence={SILENCE_LEVEL:.0f}")

_HINT = (
    "NOVA commands Hindi English Hinglish. "
    "mera naam, mere dost ka naam, bhai, behen, maa, papa. "
    "time kya hai, chrome kholo, screenshot lo, gaana bajao, volume, mute, bye."
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


def _record_until_silence():
    print("\nBOLO ABHI...")
    chunks = []
    chunk_samples = int(CHUNK * SAMPLE_RATE)
    voice_started = False
    silence_time = 0.0
    total_time = 0.0
    peak_all = 0
    voice_start_time = 0.0

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=chunk_samples)
    stream.start()
    try:
        while True:
            data, _ = stream.read(chunk_samples)
            flat = data.flatten()
            peak = float(np.abs(flat).max())
            rms = float(np.abs(flat).mean())
            if peak > peak_all:
                peak_all = peak
            total_time += CHUNK

            if not voice_started:
                if peak > VOICE_START:
                    voice_started = True
                    voice_start_time = total_time
                    print("(voice detect - sun raha hoon...)")
                    chunks.append(flat)
            else:
                chunks.append(flat)
                if rms < SILENCE_LEVEL and peak < VOICE_START * 0.8:
                    silence_time += CHUNK
                    if silence_time >= SILENCE_AFTER_VOICE:
                        break
                else:
                    silence_time = 0.0

            if total_time >= MAX_RECORD_SECONDS:
                break
    finally:
        stream.stop()
        stream.close()

    if not chunks:
        return None, peak_all

    audio = np.concatenate(chunks)
    return audio, peak_all


def listen():
    audio, peak = _record_until_silence()

    if audio is None or len(audio) < SAMPLE_RATE * 0.3:
        print(f"(chup tha, peak={peak:.0f})")
        return ""

    duration = len(audio) / SAMPLE_RATE
    avg = float(np.abs(audio).mean())
    print(f"Sun liya ({duration:.1f}s) - samajh raha hoon...")

    if peak < VOICE_START:
        print("(bahut kamzor, skip)")
        return ""

    flat = audio.astype(np.float32)
    gain = min(8000.0 / max(peak, 1), 20.0)
    boosted = np.clip(flat * gain, -32768, 32767).astype(np.int16)

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
            beam_size=1,      # faster (default 5)
            best_of=1,        # faster
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
