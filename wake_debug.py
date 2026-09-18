import numpy as np
import sounddevice as sd
import time
from openwakeword.model import Model

SAMPLE_RATE = 16000
CHUNK = 1280

print("Model load ho raha hai...")
model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx",
)
print("Ready! 30 second tak bolo - 'Hey Jarvis' baar baar.\n")

max_score = {"val": 0.0}
frame_count = {"n": 0}

def cb(indata, frames, t, status):
    audio = indata[:, 0].astype(np.int16)
    rms = float(np.abs(audio).mean())
    preds = model.predict(audio)
    frame_count["n"] += 1
    score = list(preds.values())[0] if preds else 0
    if score > max_score["val"]:
        max_score["val"] = score
    # Har 10 frame pe print (0.8 sec)
    if frame_count["n"] % 10 == 0:
        bar = "#" * int(score * 50)
        print(f"mic_rms={rms:6.0f}  score={score:.3f}  {bar}")

with sd.InputStream(callback=cb, channels=1, samplerate=SAMPLE_RATE,
                    dtype="int16", blocksize=CHUNK):
    sd.sleep(30000)

print(f"\nMax score: {max_score['val']:.3f}")
if max_score["val"] < 0.1:
    print(">>> Mic bahut kamzor hai ya galat device")
elif max_score["val"] < 0.5:
    print(">>> Mic theek hai, par 'Hey Jarvis' clearly nahi bola")
else:
    print(">>> Wake word detect ho raha tha!")
