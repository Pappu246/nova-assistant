"""
NOVA Real-Time Voice Companion (Full-Duplex Human-Like Conversation).
Features:
- Continuous ambient listening with Silero VAD
- Voice Barge-In: bolte hi NOVA interrupt hokar chup ho jata hai
- Ultra low-latency streaming pipeline
- Natural Hinglish persona & long-term memory
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
    """Speak text blocking (for greetings and direct notices)."""
    rt_speak.speak(text, block=True)


def realtime_loop():
    """Main full-duplex real-time conversation loop."""
    name = get_name()

    print("=" * 60)
    print("  🎙️ NOVA Real-Time Voice Companion (Full-Duplex)")
    print(f"  Namaste {name}! Main live sun raha hoon.")
    print("  • Seedha bolo — bolna band karte hi jawab milega")
    print("  • Voice Barge-In: Beech mein bologe toh turant chup ho jaunga")
    print("  • 'so jao' -> standby | 'bye' -> exit")
    print("=" * 60)

    # Initial Greeting
    speak(f"Namaste {name}, main sun raha hoon. Kaho, kya haal chal?")

    # Background Reminders
    try:
        import reminders
        def _on_reminder(text):
            speak(f"Boss, ek reminder hai: {text}")
        reminders.start_watcher(_on_reminder)
    except Exception as e:
        print("[rt_main] Reminders note: " + str(e)[:60])

    history = []
    standby = False
    pending_audio = None

    while True:
        # Check if we already have audio captured from a barge-in interruption
        if pending_audio is not None:
            audio = pending_audio
            duration = len(audio) / rt_listen.SAMPLE_RATE
            pending_audio = None
        else:
            if not standby:
                print("\n🎤 [Sun raha hoon...]")
            audio, duration = rt_listen.listen_vad(timeout_sec=60, debug=False)

        if audio is None:
            continue

        # Transcribe
        t_stt_start = time.time()
        text = rt_stt.transcribe(audio)
        stt_duration = time.time() - t_stt_start

        if not text or not text.strip():
            continue

        print(f"\n👤 {name}: {text}")

        low = text.lower().strip()

        # ---- Standby Handling ----
        sleep_kw = ["so jao", "soja", "soo jao", "su jao", "sujao",
                    "standby", "sleep", "band ho ja", "good night"]
        if any(w in low for w in sleep_kw):
            print("💤 [Standby Mode]")
            speak("Theek hai Boss, standby pe hoon. Jab bhi bulaoge aa jaunga.")
            standby = True
            continue

        if standby:
            wake_kw = ["uth jao", "jago", "nova", "jarvis", "suno", "hey", "hello"]
            if any(w in low for w in wake_kw):
                print("⚡ [Active Mode]")
                speak("Haan Boss, main wapas aa gaya. Bolo kya karna hai?")
                standby = False
                continue
            else:
                continue

        # ---- Exit Command ----
        if any(w in low for w in ["bye", "goodbye", "alvida", "exit karo"]):
            speak(f"Alvida {name}! Apna khayal rakhna.")
            break

        # ---- Stop / Mute Command ----
        if low in ["stop", "ruko", "chup", "bas", "shant"]:
            rt_speak.stop_speaking()
            continue

        # ---- Streaming Brain + Live Speech with Voice Barge-In ----
        print("🤖 NOVA: ", end="", flush=True)

        token_stream = rt_brain.stream_reply(text, history)
        full_reply = rt_speak.speak_streaming(token_stream)
        print(f"{full_reply}\n")

        # Check if user interrupted while speaking and captured barge-in audio
        interrupted_audio = rt_listen.stop_barge_in_monitor()
        if interrupted_audio is not None and len(interrupted_audio) > 0:
            pending_audio = interrupted_audio

        # Update Conversation History
        if full_reply:
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": full_reply})
            if len(history) > 20:
                history = history[-20:]

    print("\n[rt_main] Voice session ended.")
    rt_speak.stop_speaking()


if __name__ == "__main__":
    try:
        realtime_loop()
    except KeyboardInterrupt:
        print("\n[rt_main] Interrupted by user.")
        rt_speak.stop_speaking()
