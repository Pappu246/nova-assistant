from piper import PiperVoice
import wave, os, inspect

voice = PiperVoice.load("voices/hi_pratham.onnx")
print("Voice loaded!")
print("Sample rate:", voice.config.sample_rate)
print()

text = "Namaste Boss, main NOVA hoon. Kaam shuru karein?"

# Piper 1.8.0 API check
print("Methods available:", [m for m in dir(voice) if not m.startswith("_")])
print()

# Approach: synthesize yields chunks
try:
    print("Approach: synthesize() yields chunks")
    with wave.open("piper_test.wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(voice.config.sample_rate)
        count = 0
        for chunk in voice.synthesize(text):
            # chunk may be bytes or object with audio_int16_bytes
            if hasattr(chunk, "audio_int16_bytes"):
                wf.writeframes(chunk.audio_int16_bytes)
            else:
                wf.writeframes(chunk)
            count += 1
        print(f"  Wrote {count} chunks")
    print("File size:", os.path.getsize("piper_test.wav"))
    os.startfile("piper_test.wav")
except Exception as e:
    import traceback
    traceback.print_exc()
