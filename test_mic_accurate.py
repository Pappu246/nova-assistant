import sounddevice as sd
import numpy as np
import whisper
import tempfile
import os
from scipy.io.wavfile import write as write_wav

SAMPLE_RATE = 16000
MIC_DEVICE = 1

print("Model load...")
model = whisper.load_model("small")
print("Ready!")
print()
print(">>> 6 second tak BOLO: 'Mera naam Pappu hai, aur mera dost ka naam Sahad hai'")
print(">>> Mic ke paas bolo (5-8 inch), clear awaaz mein")
print()

input("Enter dabao jab bolna shuru karo...")

audio = sd.rec(int(6 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
               channels=1, dtype="int16", device=MIC_DEVICE)
sd.wait()

rms = float(np.abs(audio).mean())
peak = float(np.abs(audio).max())
print(f"RMS: {rms:.0f}, Peak: {peak:.0f}")

# Amplify aggressively
gain = min(20000.0 / max(peak, 1), 40.0)
boosted = np.clip(audio.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
print(f"Amplified: {gain:.1f}x")

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    write_wav(tmp.name, SAMPLE_RATE, boosted)
    tmp_path = tmp.name

# Try MULTIPLE settings
print()
print("=== Test 1: Hindi force + transcribe ===")
r1 = model.transcribe(tmp_path, fp16=False, language="hi",
                       task="transcribe", beam_size=5,
                       condition_on_previous_text=False, temperature=0.0)
print(f"Result 1: {r1['text']}")
print()

print("=== Test 2: Auto language ===")
r2 = model.transcribe(tmp_path, fp16=False, language=None,
                       task="transcribe", beam_size=5,
                       condition_on_previous_text=False, temperature=0.0)
print(f"Result 2: {r2['text']} (lang: {r2.get('language', '?')})")
print()

print("=== Test 3: Medium model ===")
os.remove(tmp_path)
