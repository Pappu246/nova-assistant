"""
NOVA Real-Time Main - VAD listen -> STT -> Streaming Brain -> Streaming TTS.
Full conversation loop with barge-in support.
"""
import sys
import time
import threading

import agent_state
import rt_listen
import rt_stt
import rt_brain
import rt_speak

try:
    import identity
except Exception:
    identity = None

try:
    import memory
except Exception:
    memory = None


def get_name():
    try:
        if identity:
            return identity.get_name()
    except Exception:
        pass
    return "Boss"


def speak(text):
    """Simple blocking speak (for greetings, errors)."""
    rt_speak._ensure_worker()
    rt_speak.enqueue(text)
    rt_speak._speak_queue.join()


def realtime_loop():
    """Main real-time conversation loop."""

    print("=" * 55)
    print("  NOVA Real-Time Mode")
    print("  Seedha bolo - VAD auto-detect karega")
    print("  Chup hone pe turant jawab milega")
    print("  'stop' / 'ruko' - ruk jao")
    print("  'bye' - exit")
    print("=" * 55)

    # Greeting
    name = get_name()
    speak(f"Namaste {name}, sun raha hoon")

    # Background: Start screen watcher + reminders
    try:
        import reminders
        def _on_reminder(text):
            speak(f"Boss, reminder: {text}")
        reminders.start_watcher(_on_reminder)
        print("[rt_main] Reminders active")
    except Exception as e:
        print("[rt_main] reminders fail: " + str(e)[:60])

    history = []
    standby = False
    cycle = 0

    while True:
        cycle += 1
        print("\n--- Cycle " + str(cycle) + " ---")

        # Listen with VAD
        print(">>> Bolo ABHI...")
        t0 = time.time()
        audio, duration = rt_listen.listen_vad(timeout_sec=60, debug=False)

        if audio is None:
            print("   (kuch nahi suna, dobara)")
            continue

        print("   Captured: " + str(round(duration, 2)) + "s")

        # STT
        t1 = time.time()
        text = rt_stt.transcribe(audio)
        stt_time = time.time() - t1

        if not text:
            print("   (STT khali, skip)")
            continue

        print("   STT (" + str(round(stt_time, 2)) + "s): " + text)
        print("   Tum: " + text)

        low = text.lower().strip()

        # ---- Standby mode ----
        sleep_kw = ["so jao", "soja", "soo jao", "su jao", "sujao",
                    "gojao", "sleep", "band ho ja", "good night"]
        if any(w in low for w in sleep_kw):
            print("[rt_main] Standby mode")
            speak("Theek hai Boss, standby pe ja raha hoon.")
            standby = True
            continue

        if standby:
            print("[rt_main] Wapas active")
            speak("Wapas aa gaya!")
            standby = False
            continue

        # ---- Bye ----
        if any(w in low for w in ["bye", "goodbye", "shutdown"]):
            speak("Theek hai Boss, milte hain!")
            break

        # ---- Stop (mid-speech) ----
        if any(w in low for w in ["stop", "ruko", "chup", "bas"]):
            print("[rt_main] Stop command")
            rt_speak.stop_speaking()
            continue

        # ---- Brain + speak (streaming) ----
        print("   [brain] streaming reply...")
        t2 = time.time()
        first_audio_flag = {"t": None}

        # Wrap speak_streaming to detect first audio start
        _orig_enqueue = rt_speak.enqueue

        def _tracked_enqueue(text, done_callback=None):
            if first_audio_flag["t"] is None:
                first_audio_flag["t"] = time.time() - t2
            return _orig_enqueue(text, done_callback)

        rt_speak.enqueue = _tracked_enqueue
        try:
            token_stream = rt_brain.stream_reply(text, history)
            full_reply = rt_speak.speak_streaming(token_stream)
        finally:
            rt_speak.enqueue = _orig_enqueue

        brain_time = time.time() - t2
        total_time = time.time() - t0
        first_audio = first_audio_flag["t"] or 0

        print("   NOVA: " + full_reply[:120])
        perceived = stt_time + first_audio
        print("   [timing] STT=" + str(round(stt_time, 2)) +
              "s | First audio=" + str(round(first_audio, 2)) +
              "s | PERCEIVED=" + str(round(perceived, 2)) + "s" +
              " | Total played=" + str(round(total_time, 2)) + "s")

        # Update history
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": full_reply})
        if len(history) > 20:
            history = history[-20:]

    print("\n[rt_main] Exit")
    rt_speak.stop_speaking()


if __name__ == "__main__":
    try:
        realtime_loop()
    except KeyboardInterrupt:
        print("\n[rt_main] Interrupted")
        rt_speak.stop_speaking()
