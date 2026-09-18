"""
NOVA Wake Word — 'Hey Jarvis' peak-based detection.
"""

import numpy as np
import sounddevice as sd
import time

try:
    from openwakeword.model import Model
    _OWW = True
except Exception as e:
    print(f"[wake] openwakeword import fail: {e}")
    _OWW = False

SAMPLE_RATE = 16000
CHUNK = 1280  # 80ms

# Peak threshold — spikes detect karne ke liye
THRESHOLD = 0.35
# Kitne consecutive frames mein peak hona chahiye (80ms each)
MIN_FRAMES_ABOVE = 1
# Recent history window (frames)
WINDOW = 25

_model = None


def _init():
    global _model
    if _model is None and _OWW:
        print("[wake] Hey Jarvis model load ho raha hai...")
        _model = Model(
            wakeword_models=["hey_jarvis"],
            inference_framework="onnx",
        )
        print("[wake] Ready. Bolo 'Hey Jarvis'.")


def _beep():
    try:
        import winsound
        winsound.Beep(1200, 150)
    except Exception:
        pass


def wait_for_wake_word(timeout_sec=None):
    if not _OWW:
        time.sleep(5)
        return False

    _init()
    if _model is None:
        time.sleep(5)
        return False

    triggered = {"flag": False}
    scores = []
    start_time = time.time()

    def cb(indata, frames, time_info, status):
        if triggered["flag"]:
            return
        audio = indata[:, 0].astype(np.int16)
        try:
            preds = _model.predict(audio)
            if preds:
                score = list(preds.values())[0]
                scores.append(score)
                if len(scores) > WINDOW:
                    scores.pop(0)
                # Recent window mein kitne frames threshold se upar hain
                above = sum(1 for s in scores if s > THRESHOLD)
                # Peak recent
                peak = max(scores) if scores else 0
                # Trigger: agar recent peak THRESHOLD se upar hai
                if peak > THRESHOLD and above >= MIN_FRAMES_ABOVE:
                    triggered["flag"] = True
                    print(f"[wake] Suna! (peak={peak:.2f}, frames_above={above})")
        except Exception:
            pass

    with sd.InputStream(
        callback=cb,
        channels=1,
        samplerate=SAMPLE_RATE,
        dtype="int16",
        blocksize=CHUNK,
    ):
        while not triggered["flag"]:
            sd.sleep(50)
            if timeout_sec and (time.time() - start_time) > timeout_sec:
                break

    if triggered["flag"]:
        try:
            _model.reset()
        except Exception:
            pass
        _beep()
        time.sleep(0.4)
        return True

    return False


if __name__ == "__main__":
    print("Test mode - 'Hey Jarvis' bolo...")
    for i in range(3):
        print(f"\nAttempt {i+1}/3 (max 20 sec wait)...")
        if wait_for_wake_word(timeout_sec=20):
            print(">>> WAKE WORD DETECTED!")
        else:
            print(">>> Timeout")
