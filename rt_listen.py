"""
NOVA Real-Time Listener - Full-Duplex VAD-based.
Silero VAD + Energy VAD with pre-speech circular buffer & Barge-In Detection.
"""
import os
import time
import collections
import threading
import numpy as np

try:
    import sounddevice as sd
    _SD = True
except Exception:
    _SD = False

try:
    import torch
    _TORCH = True
except Exception:
    _TORCH = False

try:
    from silero_vad import load_silero_vad
    _SILERO = True
except Exception:
    _SILERO = False


SAMPLE_RATE = 16000
CHUNK_SAMPLES = 512       # 32ms @ 16kHz
SILENCE_AFTER_MS = 480    # Snappy human pause detection (480ms)
MIN_SPEECH_MS = 300       # Minimum speech length
MAX_SPEECH_SEC = 30       # Max recording limit
PRE_SPEECH_CHUNKS = 6     # ~192ms pre-speech audio buffer

VAD_THRESHOLD = 0.38
BARGE_IN_THRESHOLD = 0.60

_vad_model = None
_barge_in_active = False
_barge_in_thread = None
_barge_in_audio_captured = None


def _get_mic_device():
    """Get configured mic device or None (system default)."""
    dev = os.environ.get("NOVA_MIC_DEVICE")
    if dev is not None:
        try:
            return int(dev)
        except Exception:
            return dev
    return None


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


def _calc_prob(model, chunk_int16):
    """Calculate speech probability for a 512-sample chunk."""
    if model is not None and _TORCH:
        try:
            tensor = torch.from_numpy(chunk_int16.astype(np.float32) / 32768.0)
            return float(model(tensor, SAMPLE_RATE).item())
        except Exception:
            pass
    # Fallback energy-based probability
    rms = np.sqrt(np.mean(chunk_int16.astype(np.float32) ** 2))
    return min(1.0, float(rms / 800.0))


def listen_vad(timeout_sec=30, debug=False, initial_buffer=None):
    """
    VAD-based listening with pre-speech circular buffer.
    Returns (audio_int16, duration_sec) or (None, 0) on timeout.
    """
    if not _SD:
        return None, 0

    # SEGFAULT FIX (NOVA): purana barge-in monitor join karke band karo,
    # phir hi nayi InputStream open karo (dual-open crash fix)
    try:
        stop_barge_in_monitor()
    except Exception:
        pass

    model = _load_vad()
    if model and _TORCH:
        try:
            model.reset_states()
        except Exception:
            pass

    mic_dev = _get_mic_device()
    pre_buffer = collections.deque(maxlen=PRE_SPEECH_CHUNKS)
    speech_buffer = []

    # If audio was captured during barge-in interrupt, start from it
    if initial_buffer is not None and len(initial_buffer) > 0:
        speech_buffer.append(initial_buffer)
        recording = True
        speech_ms = (len(initial_buffer) * 1000) // SAMPLE_RATE
    else:
        recording = False
        speech_ms = 0

    silence_ms = 0
    start_time = time.time()

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_SAMPLES,
            device=mic_dev,
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
            prob = _calc_prob(model, flat)

            if prob > VAD_THRESHOLD:
                if not recording:
                    recording = True
                    # Prepend pre-speech buffer so initial syllables are preserved
                    for prev in pre_buffer:
                        speech_buffer.append(prev)
                        speech_ms += (CHUNK_SAMPLES * 1000) // SAMPLE_RATE
                    if debug:
                        print(f"[rt_listen] speech start (prob={prob:.2f})")

                speech_buffer.append(flat)
                speech_ms += (CHUNK_SAMPLES * 1000) // SAMPLE_RATE
                silence_ms = 0
            else:
                if recording:
                    speech_buffer.append(flat)
                    silence_ms += (CHUNK_SAMPLES * 1000) // SAMPLE_RATE
                    if silence_ms >= SILENCE_AFTER_MS:
                        if debug:
                            print(f"[rt_listen] pause detected ({silence_ms}ms), ready")
                        break
                else:
                    pre_buffer.append(flat)

            if speech_ms >= MAX_SPEECH_SEC * 1000:
                if debug:
                    print("[rt_listen] max duration reached")
                break

            if time.time() - start_time > timeout_sec:
                break

    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    if not speech_buffer or speech_ms < MIN_SPEECH_MS:
        return None, 0

    audio = np.concatenate(speech_buffer).astype(np.int16)
    duration = len(audio) / SAMPLE_RATE
    return audio, duration


def start_barge_in_monitor(on_barge_in):
    """
    Background voice monitor while NOVA is speaking.
    If user speaks, calls on_barge_in() immediately.
    """
    global _barge_in_active, _barge_in_thread
    if not _SD:
        return

    _barge_in_active = True

    def _monitor():
        global _barge_in_active, _barge_in_audio_captured
        _barge_in_audio_captured = None
        model = _load_vad()
        mic_dev = _get_mic_device()

        consecutive_speech = 0
        captured_chunks = []

        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SAMPLES,
                device=mic_dev,
            )
            stream.start()
        except Exception:
            return

        try:
            while _barge_in_active:
                try:
                    data, _ = stream.read(CHUNK_SAMPLES)
                except Exception:
                    break

                flat = data.flatten()
                prob = _calc_prob(model, flat)

                if prob > BARGE_IN_THRESHOLD:
                    consecutive_speech += 1
                    captured_chunks.append(flat)
                    if consecutive_speech >= 3:
                        print("\n[rt_listen] 🛑 Voice Barge-In! Interrupting speech...")
                        if on_barge_in:
                            on_barge_in()
                        if captured_chunks:
                            _barge_in_audio_captured = np.concatenate(captured_chunks).astype(np.int16)
                        break
                else:
                    consecutive_speech = max(0, consecutive_speech - 1)
                    if len(captured_chunks) > 4:
                        captured_chunks.pop(0)

                time.sleep(0.01)
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    _barge_in_thread = threading.Thread(target=_monitor, daemon=True)
    _barge_in_thread.start()


def stop_barge_in_monitor():
    """Stop barge-in monitor and return any audio captured during interruption.

    """ + "SEGFAULT FIX (NOVA): monitor thread apni InputStream finally block" + """
    me khud band karta hai - yahan JOIN lete hain taaki stream 100% band ho,
    tabhi listen_vad nayi kholta hai (dual-InputStream crash fix).
    """
    global _barge_in_active, _barge_in_thread, _barge_in_audio_captured
    _barge_in_active = False
    if _barge_in_thread is not None and _barge_in_thread.is_alive():
        for _ in range(6):
            try:
                _barge_in_thread.join(timeout=0.25)
            except Exception:
                pass
            if not _barge_in_thread.is_alive():
                break
    _barge_in_thread = None
    captured = _barge_in_audio_captured
    _barge_in_audio_captured = None
    return captured


if __name__ == "__main__":
    print("=" * 55)
    print("  rt_listen.py VAD TEST (Full-Duplex)")
    print("=" * 55)
    _load_vad()
    print("Mic ready. Bolo kuch, phir chup ho jao.")
    print(f"Silence {SILENCE_AFTER_MS}ms ke baad auto-stop hoga.")
    print("=" * 55)
