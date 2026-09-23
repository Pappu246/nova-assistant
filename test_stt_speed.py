"""Compare tiny, base, small models - speed vs accuracy."""
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
MIC_DEVICE = 1

MODELS = ["tiny", "base", "small"]


def record_5s():
    print("\n>>> 5 sec bolo: 'Mera naam Pappu hai, time kya hai'")
    print("    (mic ke paas, clear)")
    input("    Enter dabao jab ready ho...")
    audio = sd.rec(int(5 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="int16", device=MIC_DEVICE)
    sd.wait()
    peak = float(np.abs(audio).max())
    print("    Recorded peak: " + str(int(peak)))
    return audio.flatten()


def test_model(name, audio):
    print("\n=== " + name.upper() + " ===")
    t0 = time.time()
    model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=4)
    load_time = time.time() - t0
    print("  Load: " + str(round(load_time, 2)) + "s")

    # Normalize
    peak = float(np.abs(audio).max())
    if peak > 0:
        gain = min(12000.0 / peak, 5.0)
        audio_norm = np.clip(audio * gain, -32768, 32767).astype(np.int16)
    else:
        audio_norm = audio
    audio_float = audio_norm.astype(np.float32) / 32768.0

    # Warm-up run (not counted)
    _ = list(model.transcribe(audio_float, beam_size=1, language=None)[0])

    # Timed run
    t0 = time.time()
    segments, info = model.transcribe(
        audio_float,
        language=None,
        task="transcribe",
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
        temperature=0.0,
        without_timestamps=True,
        initial_prompt="mera naam pappu hai. time kya hai.",
    )
    text = " ".join(seg.text for seg in segments).strip()
    elapsed = time.time() - t0

    print("  STT time: " + str(round(elapsed, 2)) + "s")
    print("  Text: " + text)
    return elapsed, text


if __name__ == "__main__":
    print("=" * 55)
    print("  STT MODEL SPEED TEST")
    print("=" * 55)

    audio = record_5s()

    results = []
    for m in MODELS:
        try:
            t, txt = test_model(m, audio)
            results.append((m, t, txt))
        except Exception as e:
            print("  " + m + " fail: " + str(e)[:60])

    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    for m, t, txt in results:
        print("  " + m.ljust(8) + " " + str(round(t, 2)) + "s  | " + txt[:50])
    print("=" * 55)
