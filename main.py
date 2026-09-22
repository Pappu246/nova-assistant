"""
NOVA - Voice assistant (continuous mode only, no wake word).
"""
import sys
import re
import agent_state
import time
import threading
from brain import ask_nova

try:
    import hud
    _HUD = True
except Exception:
    _HUD = False

from bolo import speak, stop_speaking, is_stopped, start_esc_listener

try:
    import memory
except Exception:
    memory = None


def speak_with_interrupt(text):
    """Bol + parallel mein voice 'stop' sune."""
    from suno import listen_for_stop

    stop_event = threading.Event()

    def _voice_stop_listener():
        try:
            listen_for_stop(stop_event, timeout_sec=90)
        except Exception as e:
            print(f"[stop-listener] {e}")

    def _watch():
        while not stop_event.is_set():
            stop_event.wait(0.15)
            if stop_event.is_set():
                print("[voice-stop] detected!")
                stop_speaking()
                break

    t1 = threading.Thread(target=_voice_stop_listener, daemon=True)
    t2 = threading.Thread(target=_watch, daemon=True)
    t1.start()
    t2.start()

    try:
        speak(text)
    finally:
        stop_event.set()


def get_user_name():
    try:
        import identity
        return identity.get_name()
    except Exception:
        if memory:
            try:
                n = memory.get_fact("user_name")
                if n:
                    return n
            except Exception:
                pass
    return "Boss"


def proactive_greeting():
    import datetime
    now = datetime.datetime.now()
    h = now.hour
    day = now.strftime("%A")
    name = get_user_name()

    if h < 12:
        greet = f"Good morning {name}!"
    elif h < 17:
        greet = f"Good afternoon {name}!"
    elif h < 21:
        greet = f"Good evening {name}!"
    else:
        greet = f"Good night {name}!"

    if h < 10:
        follow = "Aaj ka din shuru karein? Kya plan hai?"
    elif h < 17:
        follow = f"Aaj {day} hai. Kya kar rahe ho?"
    elif h < 21:
        follow = "Din kaisa raha? Kuch kaam karna hai?"
    else:
        follow = "Aaram kar rahe ho ya kuch kaam hai?"

    return f"{greet} Main NOVA hoon. {follow}"


# ============ TEXT INPUT READER ============

_typed_queue = []
_typed_lock = threading.Lock()


def _text_input_reader():
    while True:
        try:
            line = input()
            if line and line.strip():
                with _typed_lock:
                    _typed_queue.append(line.strip())
        except EOFError:
            break
        except Exception:
            break


def _get_typed():
    with _typed_lock:
        if _typed_queue:
            return _typed_queue.pop(0)
    return None


# ============ CONTINUOUS MODE (DEFAULT) ============

def continuous_mode():
    """Continuous mode - no wake word. Sirf bolo, kaam kare. Sirf teri awaaz sunta hai."""
    from suno import listen_continuous
    from bolo import start_esc_listener

    state = agent_state.get_state()
    state.set_mode("idle")

    start_esc_listener()

    if _HUD:
        try:
            hud.start()
            hud.update("status", "Ready")
        except Exception:
            pass

    print("=" * 55)
    print("  NOVA - Ready")
    print("  Seedha bolo, kaam karein")
    print("  'stop' / 'ruko' - ruk jao")
    print("  'so jao' - standby")
    print("=" * 55)

    name = get_user_name()

    threading.Thread(target=_text_input_reader, daemon=True).start()
    print("[input] Terminal mein type karo aur Enter dabao")

    speak_with_interrupt(f"Namaste {name}, sun raha hoon")

    # Start reminders watcher
    try:
        import reminders
        def _on_reminder_fire(text):
            try:
                speak_with_interrupt(f"Boss, reminder: {text}")
            except Exception:
                pass
        reminders.start_watcher(_on_reminder_fire)
        print("[reminders] Active")
    except Exception as e:
        print(f"[reminders] fail: {e}")

    history = []
    standby = False

    while True:
        typed = _get_typed()
        if typed:
            text = typed
            print(f"[typed] {text}")
            matched = True
        else:
            text, matched = listen_continuous(chunk_sec=3.0)

        if not text:
            continue

        print(f"Tum: {text}")
        if _HUD:
            hud.update("user", text)
            hud.update("status", "Soch raha hoon...")

        low = text.lower().strip()
        low_clean = re.sub(r"[^a-z ]", "", low)
        low_clean = re.sub(r"\s+", " ", low_clean).strip()

        # ---- STANDBY MODE ----
        sleep_keywords = ["so jao", "soja", "soo jao", "su jao", "sujao",
                          "gojao", "so jaa", "sleep", "band ho ja",
                          "chup ho ja", "shant ho ja", "good night"]
        is_sleep = any(w in low_clean for w in sleep_keywords)

        if is_sleep:
            print("[continuous] Standby mode. Bolne pe wapas active hoga.")
            speak_with_interrupt("Theek hai Boss, standby pe ja raha hoon. Jab bologe wapas active ho jaunga.")
            standby = True
            continue

        # ---- WAKE FROM STANDBY (any speech resumes) ----
        if standby:
            print("[continuous] Wapas active")
            speak_with_interrupt("Wapas aa gaya!")
            standby = False
            continue

        # ---- BYE ----
        if any(w in low for w in ["bye", "goodbye", "shutdown"]):
            speak_with_interrupt("Theek hai Boss, milte hain!")
            break

        # ---- STOP ----
        if any(w in low for w in ["stop", "ruko", "chup", "bas"]):
            continue

        # ---- PROCESS ----
        state.set_mode("thinking")
        reply = ask_nova(text, history)
        state.record_tool_result(reply)
        state.add_to_context("assistant", reply)

        state.set_mode("speaking")
        if _HUD:
            hud.update("nova", reply)
            hud.update("status", "Bol raha hoon...")
        speak_with_interrupt(reply)
        state.set_mode("idle")
        if _HUD:
            hud.update("status", "Ready")

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = history[-20:]


def text_mode():
    print("NOVA - text mode")
    history = []
    while True:
        u = input("\nTum: ").strip()
        if u.lower() in ("bye", "exit", "quit"):
            break
        if not u:
            continue
        r = ask_nova(u, history)
        print(f"NOVA: {r}")
        history.append({"role": "user", "content": u})
        history.append({"role": "assistant", "content": r})
        if len(history) > 20:
            history = history[-20:]


if __name__ == "__main__":
    if "--text" in sys.argv:
        text_mode()
    else:
        # Default: continuous mode (no wake word)
        continuous_mode()
