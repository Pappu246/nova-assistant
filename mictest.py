import sounddevice as sd
import numpy as np

def cb(indata, frames, t, status):
    lvl = float(np.abs(indata).mean())
    bar = "#" * int(lvl / 200)
    print(f"Level: {lvl:7.0f} {bar}")

print("10 second - bolo kuch zor se...")
with sd.InputStream(callback=cb, channels=1, samplerate=16000, dtype="int16"):
    sd.sleep(10000)
