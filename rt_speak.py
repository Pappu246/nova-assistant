"""
NOVA Real-Time TTS - soundfile version (pygame-free)
- edge-tts generates MP3
- soundfile reads MP3 (libsndfile)
- sounddevice plays it
- ESC key = stop (background listener)
"""
import os
import time
import queue
import tempfile
import threading
import asyncio

import numpy as np

# ---------- soundfile + sounddevice ----------
_SF = False
_SD = False
try:
    import soundfile as sf
    _SF = True
except Exception as e:
    print("[rt_speak] soundfile FAIL:", str(e)[:60])
try:
    import sounddevice as sd
    _SD = True
except Exception as e:
    print("[rt_speak] sounddevice FAIL:", str(e)[:60])

# ---------- edge-tts ----------
_EDGE = False
try:
    import edge_tts
    _EDGE = True
except Exception as e:
    print("[rt_speak] edge-tts FAIL:", str(e)[:60])

# ---------- ESC key listener ----------
_ESC_MODE = None
try:
    import keyboard as _kb
    _ESC_MODE = "keyboard"
except Exception:
    try:
        from pynput import keyboard as _pk
        _ESC_MODE = "pynput"
    except Exception:
        _ESC_MODE = None

print("[rt_speak] ESC:", _ESC_MODE, "| soundfile:", _SF, "| sounddevice:", _SD, "| edge:", _EDGE)


# ---------- State ----------
_speaking_flag = threading.Event()
_stop_flag = threading.Event()
_speak_queue = queue.Queue()
_worker = None
_esc_thread = None
_esc_active = False
_current_process = None


# ---------- Stop ----------
def _do_stop():
    global _current_process
    if _SD:
        try:
            sd.stop()
        except Exception:
            pass
    if _current_process is not None:
        try:
            _current_process.terminate()
        except Exception:
            pass
        _current_process = None


def stop_speaking():
    _stop_flag.set()
    _do_stop()


def is_speaking():
    return _speaking_flag.is_set()


# ---------- ESC watcher ----------
def _esc_loop():
    global _esc_active
    if _ESC_MODE == "keyboard":
        while _esc_active:
            try:
                if _kb.is_pressed("esc"):
                    print("\n[rt_speak] *** ESC pressed ***")
                    _stop_flag.set()
                    _do_stop()
                    time.sleep(0.3)
            except Exception:
                pass
            time.sleep(0.05)
    elif _ESC_MODE == "pynput":
        def on_press(key):
            if key == _pk.Key.esc:
                print("\n[rt_speak] *** ESC pressed ***")
                _stop_flag.set()
                _do_stop()
        with _pk.Listener(on_press=on_press) as listener:
            while _esc_active:
                time.sleep(0.1)
            listener.stop()


def _start_esc():
    global _esc_thread, _esc_active
    if _ESC_MODE is None or _esc_active:
        return
    _esc_active = True
    _esc_thread = threading.Thread(target=_esc_loop, daemon=True)
    _esc_thread.start()


def _stop_esc():
    global _esc_active
    _esc_active = False


# ---------- edge-tts ----------
async def _edge_save(text, path):
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await communicate.save(path)


def _edge_to_file(text, path):
    if not _EDGE:
        return False
    try:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_edge_save(text, path))
        finally:
            loop.close()
        return os.path.exists(path) and os.path.getsize(path) > 500
    except Exception as e:
        print("[rt_speak] edge fail:", str(e)[:80])
        return False


# ---------- SAPI fallback (offline) ----------
def _sapi_speak(text):
    global _current_process
    try:
        import platform, subprocess
        if platform.system() != "Windows":
            return False
        safe = text.replace("'", "''")
        ps = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.Rate = 1;"
            "$s.Speak('" + safe + "');"
        )
        _current_process = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        while _current_process.poll() is None:
            if _stop_flag.is_set():
                _current_process.terminate()
                break
            time.sleep(0.1)
        _current_process = None
        return True
    except Exception as e:
        print("[rt_speak] SAPI fail:", str(e)[:60])
        _current_process = None
        return False


# ---------- Playback via sounddevice ----------
def _play(path):
    if not (_SF and _SD):
        return
    try:
        data, sr = sf.read(path, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        sd.play(data, sr)
        # poll for stop
        stream = sd.get_stream()
        while stream is not None and stream.active:
            if _stop_flag.is_set():
                sd.stop()
                break
            time.sleep(0.03)
    except Exception as e:
        print("[rt_speak] play fail:", str(e)[:80])


# ---------- Worker ----------
def _worker_loop():
    while True:
        item = _speak_queue.get()
        if item is None:
            _speak_queue.task_done()
            break
        text, done_cb = item
        try:
            if not text or not text.strip():
                if done_cb:
                    done_cb()
                continue

            _stop_flag.clear()
            _speaking_flag.set()
            _start_esc()

            path = os.path.join(
                tempfile.gettempdir(),
                "nova_tts_" + str(int(time.time() * 1000)) + ".mp3",
            )

            if _edge_to_file(text, path):
                print("[rt_speak] speak:", text[:60])
                _play(path)
                try:
                    os.remove(path)
                except Exception:
                    pass
            else:
                print("[rt_speak] edge failed -> SAPI fallback")
                _sapi_speak(text)

            _speaking_flag.clear()
            _stop_esc()
            if done_cb:
                done_cb()
        except Exception as e:
            print("[rt_speak] worker err:", str(e)[:80])
            _speaking_flag.clear()
            _stop_esc()
        finally:
            try:
                _speak_queue.task_done()
            except Exception:
                pass


def _ensure_worker():
    global _worker
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_worker_loop, daemon=True)
        _worker.start()


# ---------- Public API ----------
def speak(text, done_callback=None, block=False):
    _ensure_worker()
    _speak_queue.put((text, done_callback))
    if block:
        _speak_queue.join()


def wait_until_done():
    _speak_queue.join()


# ---------- Test ----------
if __name__ == "__main__":
    print()
    print("=" * 50)
    print("  TEST: 10-second speech")
    print("  Press ESC anytime to STOP")
    print("=" * 50)
    print()

    speak(
        "Yeh ek lamba test hai. Agar tum ESC key dabao "
        "toh main turant ruk jaunga. Warna main das second "
        "baad khud ruk jaunga. ESC background mein sun raha hoon."
    )

    for i in range(150):
        if not is_speaking() and _speak_queue.empty():
            break
        time.sleep(0.1)

    print("Test done.")
