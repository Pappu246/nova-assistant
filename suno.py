import time
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write as write_wav
import whisper
import tempfile
import os
import re

SAMPLE_RATE = 16000
MIC_DEVICE = 1
CALIB_SECONDS = 2
MAX_RECORD_SECONDS = 60
SILENCE_AFTER_VOICE = 2.0
CHUNK = 0.08

print("Whisper model load ho raha hai (medium - accurate)...")
_model = whisper.load_model("medium")
print("Whisper ready hai.")

try:
    _dev = sd.query_devices(MIC_DEVICE)
    print("MIC: [" + str(MIC_DEVICE) + "] " + _dev["name"][:50])
except Exception:
    print("MIC: [" + str(MIC_DEVICE) + "]")

print(str(CALIB_SECONDS) + " second chup raho...")
_calib = sd.rec(int(CALIB_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                channels=1, dtype="int16", device=MIC_DEVICE)
sd.wait()
AMBIENT = float(np.abs(_calib).mean())
VOICE_START = max(AMBIENT * 1.8, 2500)
SILENCE_LEVEL = max(AMBIENT * 1.2, 1500)
print("Calibrated: ambient=" + str(int(AMBIENT)))

_HINT = ("mera naam pappu hai. mera dost sahid pinkesh gopal jahid hai. "
         "time kya hai. chrome kholo. youtube kholo. gaana bajao. "
         "screenshot lo. volume badhao. volume kam karo. mute karo. "
         "bye. stop. ruko. kya kar rahe ho. kaise ho. theek hai.")

_DEVANAGARI_MAP = {
    "ताम": "time", "टाइम": "time", "समय": "time", "ताईं": "time",
    "क्रोम": "chrome", "यूट्यूब": "youtube", "गूगल": "google",
    "नोवा": "nova", "हैलो": "hello", "हाय": "hi", "नमस्ते": "namaste",
    "बॉस": "boss", "ठीक": "theek", "बंद": "band",
    "खोलो": "kholo", "खोल": "kholo", "बजाओ": "bajao",
    "चलाओ": "chalao", "बढ़ाओ": "badhao", "कम": "kam",
    "म्यूट": "mute", "स्क्रीनशॉट": "screenshot", "फोटो": "photo",
    "आवाज़": "volume", "आवाज": "volume", "गाना": "gaana",
    "गाने": "gaana", "रुको": "ruko", "रुक": "ruk",
    "स्टॉप": "stop", "चुप": "chup", "बस": "bas",
    "मेरा": "mera", "मेरी": "meri", "मेरे": "mere", "मुझे": "mujhe",
    "नाम": "naam", "क्या": "kya", "क्यों": "kyun", "कैसे": "kaise",
    "दोस्त": "dost", "भाई": "bhai", "बहन": "behen",
    "माँ": "maa", "पापा": "papa", "हूँ": "hoon", "है": "hai",
    "कर": "kar", "रहा": "raha", "रही": "rahi", "बता": "bata",
    "बताओ": "batao", "दिखा": "dikha", "दिखाओ": "dikhao",
    "अच्छा": "accha", "मदद": "madad", "मौसम": "mausam",
    "बाय": "bye", "तुम": "tum", "आप": "aap", "हो": "ho",
    "मैं": "main", "मै": "main", "जाओ": "jao", "आओ": "aao",
}

_HALLUCINATIONS = [
    "song play", "play song", "subscribe", "thanks for watching",
    "thank you", "please subscribe", "amara.org", "subtitle",
    "subtitles", "www.", "caption", "captions", "editor",
    "amazing", "yeah", "hmm", "okay", "hello everyone",
    "fourth verse", "list of men",
]

STOP_WORDS = ["stop", "ruko", "chup", "bas", "shut up", "band karo",
              "रुको", "स्टॉप", "चुप", "बंद"]


def _fix_transcription(text):
    if not text:
        return text
    t = text
    for hindi, eng in _DEVANAGARI_MAP.items():
        t = t.replace(hindi, eng)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _is_gibberish(text):
    if not text:
        return True
    low = text.lower().strip()
    if len(low) < 2:
        return True
    if not re.search(r"[a-zA-Z\u0900-\u097F]", low):
        return True
    words = low.split()
    if len(words) < 2:
        return False
    if len(set(words)) / len(words) < 0.35 and len(words) > 5:
        return True
    if re.search(r"[\u4e00-\u9fff\u3040-\u30ff]", text):
        return True
    return False


def _is_repetition(text):
    words = text.lower().split()
    if len(words) < 6:
        return False
    if len(set(words)) / len(words) < 0.4:
        return True
    return False


def listen():
    print()
    print("BOLO ABHI...")
    chunks = []
    chunk_samples = int(CHUNK * SAMPLE_RATE)
    voice_started = False
    silence_time = 0.0
    total_time = 0.0
    peak_all = 0

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=chunk_samples,
                            device=MIC_DEVICE)
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
                    print("(sun raha hoon...)")
                    chunks.append(flat)
            else:
                chunks.append(flat)
                if rms < SILENCE_LEVEL and peak < VOICE_START * 0.7:
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
        return ""

    audio = np.concatenate(chunks)

    if len(audio) < SAMPLE_RATE * 0.5:
        return ""

    duration = len(audio) / SAMPLE_RATE
    peak = float(np.abs(audio).max())
    print("Sun liya (" + str(round(duration, 1)) + "s) - samajh raha hoon...")

    if peak < VOICE_START:
        return ""

    flat = audio.astype(np.float32)
    gain = min(20000.0 / max(peak, 1), 10.0)
    boosted = np.clip(flat * gain, -32768, 32767).astype(np.int16)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        write_wav(tmp.name, SAMPLE_RATE, boosted)
        tmp_path = tmp.name

    try:
        result = _model.transcribe(
            tmp_path, fp16=False, language=None, task="transcribe",
            initial_prompt=_HINT, beam_size=5, best_of=3,
            condition_on_previous_text=False, temperature=0.0,
        )
        text = result["text"].strip()
        text = _fix_transcription(text)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    low = text.lower().strip()
    if _is_gibberish(low):
        print("(gibberish: " + text[:40] + ")")
        return ""
    if _is_repetition(low):
        print("(repetition: " + text[:40] + ")")
        return ""
    if any(h in low for h in _HALLUCINATIONS):
        print("(hallucination: " + text[:40] + ")")
        return ""

    return text


def listen_continuous(chunk_sec=4.0):
    try:
        from voice_id import is_boss
    except Exception:
        def is_boss(a, threshold=0.50): return True

    CHUNK_SIZE = int(0.1 * SAMPLE_RATE)
    MAX_SEC = 15
    SILENCE_AFTER = 1.2
    VOICE_START_MIN = max(VOICE_START, 1500)

    chunks = []
    voice_started = False
    silence_time = 0.0
    total_time = 0.0
    peak_all = 0

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="int16", blocksize=CHUNK_SIZE,
                                device=MIC_DEVICE)
        stream.start()
    except Exception as e:
        print("[continuous] stream fail: " + str(e)[:60])
        return "", False

    try:
        while total_time < MAX_SEC:
            try:
                data, _ = stream.read(CHUNK_SIZE)
            except Exception:
                break
            flat = data.flatten()
            peak = float(np.abs(flat).max())
            rms = float(np.abs(flat).mean())
            if peak > peak_all:
                peak_all = peak
            total_time += 0.1

            if not voice_started:
                if peak > VOICE_START_MIN:
                    voice_started = True
                    silence_time = 0.0
                    chunks.append(flat)
            else:
                chunks.append(flat)
                if rms < 400 and peak < VOICE_START_MIN * 0.7:
                    silence_time += 0.1
                    if silence_time >= SILENCE_AFTER:
                        break
                else:
                    silence_time = 0.0

        if not voice_started or len(chunks) < 3:
            return "", False
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    audio = np.concatenate(chunks)

    if len(audio) < SAMPLE_RATE * 1.0:
        return "", False

    peak = float(np.abs(audio).max())

    if peak < 1500:
        return "", False

    try:
        boss = is_boss(audio)
    except Exception:
        boss = True

    if not boss:
        return "", False

    gain = min(20000.0 / max(peak, 1), 10.0)
    boosted = np.clip(audio.astype(np.float32) * gain, -32768, 32767).astype(np.int16)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        write_wav(tmp.name, SAMPLE_RATE, boosted)
        tmp_path = tmp.name

    text = ""
    try:
        result = _model.transcribe(
            tmp_path, fp16=False, language=None, task="transcribe",
            initial_prompt=_HINT, beam_size=5, best_of=3,
            condition_on_previous_text=False, temperature=0.0,
        )
        text = result["text"].strip()
        text = _fix_transcription(text)
    except Exception as e:
        print("[continuous] transcribe err: " + str(e)[:60])
        return "", False
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    if not text:
        return "", True

    dur = len(audio) / SAMPLE_RATE
    print("[heard " + str(round(dur, 1)) + "s] " + text[:100])

    low = text.lower().strip()

    if len(low) < 2:
        return "", True

    words = low.split()
    if len(words) >= 4:
        unique = set(words)
        if len(unique) <= 2 and len(words) > 4:
            print("[continuous] repetition skip")
            return "", True
        from collections import Counter
        most_common = Counter(words).most_common(1)[0]
        if most_common[1] >= 3 and len(words) > 5:
            print("[continuous] repetition skip")
            return "", True

    cjk = re.compile("[\u4e00-\u9fff\u3040-\u30ff]")
    if cjk.search(text):
        print("[continuous] CJK skip")
        return "", True

    return text, True


def listen_for_stop(stop_event, timeout_sec=90):
    import time as _t

    start = _t.time()
    CHUNK_STOP = int(0.25 * SAMPLE_RATE)

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="int16", blocksize=CHUNK_STOP,
                                device=MIC_DEVICE)
        stream.start()
    except Exception as e:
        print("[stop] stream fail: " + str(e)[:60])
        return

    check_counter = 0
    try:
        while not stop_event.is_set():
            if _t.time() - start > timeout_sec:
                break
            try:
                data, _ = stream.read(CHUNK_STOP)
            except Exception:
                break

            flat = data.flatten()
            rms = float(np.abs(flat).mean())
            peak = float(np.abs(flat).max())

            if rms < 300 and peak < 1500:
                continue

            check_counter += 1
            if check_counter % 2 != 0:
                continue

            gain = min(22000.0 / max(peak, 1), 15.0)
            boosted = np.clip(flat.astype(np.float32) * gain, -32768, 32767).astype(np.int16)

            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    write_wav(tmp.name, SAMPLE_RATE, boosted)
                    tmp_path = tmp.name
                result = _model.transcribe(
                    tmp_path, fp16=False, language=None,
                    beam_size=1, best_of=1,
                    condition_on_previous_text=False,
                    temperature=0.0,
                    initial_prompt="stop ruko chup",
                )
                text = result["text"].strip().lower()
            except Exception:
                continue
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            if not text:
                continue

            check_str = text
            try:
                check_str += " " + _fix_transcription(text).lower()
            except Exception:
                pass

            for w in STOP_WORDS:
                if w in check_str:
                    print("[stop] DETECTED: " + w)
                    stop_event.set()
                    return
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
