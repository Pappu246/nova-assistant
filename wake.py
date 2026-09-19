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
THRESHOLD = 0.30        # pehle 0.35 tha, ab 0.22 (soft bhi pakde)
MIN_FRAMES_ABOVE = 1
WINDOW = 25
# Score spike ratio — mean se kitna upar peak ho
PEAK_RATIO = 6.0        # peak / rolling_mean > 3.5 to bhi trigger

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



def _ping_dashboard():
    """Dashboard ko batao ki wake word suna."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/wake/ping",
            method="POST"
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


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

            # Spike detection DISABLED (too noisy)
            # Only absolute threshold now
            pass
        except Exception:
            pass

    # Try opening stream with retry
    stream = None
    for attempt in range(5):
        try:
            stream = sd.InputStream(
                callback=cb,
                channels=1,
                samplerate=SAMPLE_RATE,
                dtype="int16",
                blocksize=CHUNK,
            )
            break
        except Exception as e:
            print(f"[wake] stream open fail (attempt {attempt+1}): {str(e)[:60]}")
            time.sleep(0.5)
    if stream is None:
        print("[wake] Could not open mic")
        return False

    with stream:
        while not triggered["flag"]:
            sd.sleep(50)
            if timeout_sec and (time.time() - start_time) > timeout_sec:
                break

    if triggered["flag"]:
        try:
            _model.reset()
        except Exception:
            pass
        _ping_dashboard()
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
