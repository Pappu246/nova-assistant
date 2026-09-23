"""
NOVA Real-Time Listener - VAD-based.
Silero VAD se voice detect karo, chup hone pe turant STT.
"""
import time
import numpy as np
import sounddevice as sd

try:
    import torch
    _TORCH = True
except Exception:
    _TORCH = False

try:
    from silero_vad import load_silero_vad, VADIterator
    _SILERO = True
except Exception as e:
    print("[rt_listen] silero import fail: " + str(e)[:80])
    _SILERO = False


SAMPLE_RATE = 16000
MIC_DEVICE = 1
CHUNK_MS = 32  # Silero needs 512 samples @ 16kHz = 32ms
CHUNK_SAMPLES = 512

# VAD tuning
VAD_THRESHOLD = 0.4           # Silero threshold
SILENCE_AFTER_MS = 900         # Bolna band hone ke baad itna silence = stop
MIN_SPEECH_MS = 400            # Minimum speech length
MAX_SPEECH_SEC = 30            # Max recording


_vad_model = None


def _load_vad():
    global _vad_model
    if _vad_model is not None or not _SILERO:
        return _vad_model
    try:
        _vad_model = load_silero_vad()
        print("[rt_listen] Silero VAD loaded")
    except Exception as e:
        print("[rt_listen] VAD load fail: " + str(e)[:80])
        _vad_model = None
    return _vad_model


def listen_vad(timeout_sec=30, debug=False):
    """
    VAD-based listening.
    Waits for speech, records until silence, returns int16 audio array.
    Returns (audio_int16, duration_sec) or (None, 0) if timeout.
    """
    model = _load_vad()
    if model is None:
        # Fallback: fixed 5s record
        audio = sd.rec(int(5 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=1, dtype="int16", device=MIC_DEVICE)
        sd.wait()
        return audio.flatten(), 5.0

    # Reset VAD state
    try:
        model.reset_states()
    except Exception:
        pass

    speech_buffer = []
    silence_ms = 0
    speech_ms = 0
    recording = False
    start_time = time.time()
    triggered = False

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_SAMPLES,
            device=MIC_DEVICE,
        )
        stream.start()
    except Exception as e:
        print("[rt_listen] stream fail: " + str(e)[:60])
        return None, 0

    try:
        while True:
            try:
                data, _ = stream.read(CHUNK_SAMPLES)
            except Exception:
                break

            flat = data.flatten()
            audio_tensor = torch.from_numpy(flat.astype(np.float32) / 32768.0)
            try:
                prob = model(audio_tensor, SAMPLE_RATE).item()
            except Exception:
                prob = 0.0

            # Speech detected
            if prob > VAD_THRESHOLD:
                if not recording:
                    recording = True
                    if debug:
                        print("[rt_listen] speech start (prob=" + str(round(prob, 2)) + ")")
                speech_buffer.append(flat)
                speech_ms += (CHUNK_SAMPLES * 1000) // SAMPLE_RATE
                silence_ms = 0
                triggered = True
            else:
                if recording:
                    speech_buffer.append(flat)
                    silence_ms += (CHUNK_SAMPLES * 1000) // SAMPLE_RATE

                    # Silence detected - stop
                    if silence_ms >= SILENCE_AFTER_MS:
                        if debug:
                            print("[rt_listen] silence detected, stop")
                        break
                # else: not recording, keep waiting silently

            # Safety: max record length
            if speech_ms >= MAX_SPEECH_SEC * 1000:
                if debug:
                    print("[rt_listen] max length reached")
                break

            # Timeout overall
            if time.time() - start_time > timeout_sec:
                break

            if debug and recording and speech_ms % 500 == 0:
                print("[rt_listen] recording: " + str(speech_ms) + "ms, silence=" + str(silence_ms))

    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    if not speech_buffer:
        return None, 0

    audio = np.concatenate(speech_buffer).astype(np.int16)
    duration = len(audio) / SAMPLE_RATE

    # Too short?
    if speech_ms < MIN_SPEECH_MS:
        if debug:
            print("[rt_listen] too short (" + str(speech_ms) + "ms), skip")
        return None, 0

    return audio, duration


if __name__ == "__main__":
    print("=" * 55)
    print("  rt_listen.py VAD TEST")
    print("=" * 55)
    _load_vad()
    print()
    print("Mic [1] ready. Bolo kuch, phir chup ho jao.")
    print("Silence 800ms ke baad auto-stop hoga.")
    print()

    for i in range(3):
        print("--- Attempt " + str(i+1) + "/3 ---")
        print(">>> Bolo ABHI...")
        audio, dur = listen_vad(timeout_sec=20, debug=True)
        if audio is None:
            print("   (kuch nahi suna)")
        else:
            peak = int(np.abs(audio).max())
            print("   Captured: " + str(round(dur, 2)) + "s, peak=" + str(peak))
            # Transcribe for verification
            try:
                from rt_stt import transcribe
                import time
                t0 = time.time()
                text = transcribe(audio)
                dt = time.time() - t0
                print("   STT (" + str(round(dt, 2)) + "s): " + text)
            except Exception as e:
                print("   STT fail: " + str(e)[:60])
        print()

    print("=" * 55)
