"""
NOVA Wake Word — 'Hey Jarvis' (soft-detection friendly).
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

# Soft detection ke liye sensitivity
THRESHOLD = 0.12        # pehle 0.35 tha, ab 0.22 (soft bhi pakde)
MIN_FRAMES_ABOVE = 1
WINDOW = 25
# Score spike ratio — mean se kitna upar peak ho
PEAK_RATIO = 2.2        # peak / rolling_mean > 3.5 to bhi trigger

_model = None


def _init():
    global _model
    if _model is None and _OWW:
        print("[wake] Hey Jarvis model load ho raha hai...")
        _model = Model(
            wakeword_models=["hey_jarvis"],
            inference_framework="onnx",
        )
        print("[wake] Ready. Bolo 'Hey Jarvis' (dheere bhi chalega).")


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
            if not preds:
                return
            score = float(list(preds.values())[0])
            scores.append(score)
            if len(scores) > WINDOW:
                scores.pop(0)

            peak = max(scores)
            mean_score = sum(scores) / len(scores) if scores else 0

            # Method 1: Absolute threshold (soft voice ke liye kam)
            if peak > THRESHOLD:
                triggered["flag"] = True
                print(f"[wake] Suna! (peak={peak:.2f})")
                return

            # Method 2: Relative spike - mean se bahut upar
            if len(scores) > 5 and peak > 0.1 and mean_score > 0:
                ratio = peak / max(mean_score, 0.01)
                if ratio > PEAK_RATIO and peak > 0.15:
                    triggered["flag"] = True
                    print(f"[wake] Suna! (spike, peak={peak:.2f}, ratio={ratio:.1f})")
                    return
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
    print("Test mode - 'Hey Jarvis' DHEERE bolo...")
    for i in range(5):
        print(f"\nAttempt {i+1}/5 (max 20 sec)...")
        if wait_for_wake_word(timeout_sec=20):
            print(">>> WAKE WORD DETECTED!")
        else:
            print(">>> Timeout")
