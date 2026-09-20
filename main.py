import sys
import re
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
    """Get verified identity or fallback to 'Boss'."""
    try:
        import identity
        return identity.get_name()
    except Exception:
        # Fallback: memory module
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

    # Natural follow-up question
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
    """Terminal se text padho - background thread."""
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

def continuous_mode():
    """Continuous - 'Hey Jarvis' ki zaroorat nahi. Sirf bolo, kaam kare."""
    from suno import listen, listen_continuous
    from bolo import speak, stop_speaking, start_esc_listener

    start_esc_listener()

    if _HUD:
        try:
            hud.start()
            hud.update("status", "Ready")
        except Exception:
            pass

    print("=" * 55)
    print("  NOVA Continuous Mode")
    print("  'Hey Jarvis' ki zaroorat nahi - bas bolo")
    print("  'stop' / 'ruko' - ruk jao | 'so jao' - sleep")
    print("=" * 55)

    name = "Boss"
    try:
        import identity
        name = identity.get_name()
    except Exception:
        pass

    # Start text input reader (background)
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
    
    # SLEEP removed

    while True:
        # Sleep disabled

        # Check typed input first (higher priority)
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

        sleep_keywords = ["so jao", "soja", "soo jao", "su jao", "sujao",
                          "gojao", "so jaa", "sleep", "band ho ja",
                          "chup ho ja", "shant ho ja", "good night"]
        is_sleep = any(w in low_clean for w in sleep_keywords)

        if is_sleep:
            print("[continuous] Sleep command detected")
            speak_with_interrupt("Theek hai Boss, standby pe ja raha hoon.")
            from wake import wait_for_wake_word
            while True:
                woke = wait_for_wake_word(timeout_sec=90)
                if woke:
                    speak_with_interrupt("Wapas aa gaya!")
                    break
            
            continue

        if any(w in low for w in ["bye", "goodbye", "shutdown"]):
            speak_with_interrupt("Theek hai Boss, milte hain!")
            break

        if any(w in low for w in ["stop", "ruko", "chup", "bas"]):
            continue

        reply = ask_nova(text, history)
        if _HUD:
            hud.update("nova", reply)
            hud.update("status", "Bol raha hoon...")
        speak_with_interrupt(reply)
        if _HUD:
            hud.update("status", "Ready")

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = history[-20:]

def voice_mode():
    from suno import listen
    from wake import wait_for_wake_word

    start_esc_listener()

    if _HUD:
        try:
            hud.start()
            hud.update("status", "Ready")
        except Exception as e:
            print(f"[hud start fail] {e}")

    print("=" * 55)
    print("  NOVA — 'Hey Jarvis' bolo ya seedha baat karo")
    print("  Esc = stop")
    print("=" * 55)

    # Proactive greeting
    greeting = proactive_greeting()
    speak_with_interrupt(greeting)

    try:
        import reminders
        def _on_reminder_fire(text):
            try:
                speak_with_interrupt(f"Boss, reminder: {text}")
            except Exception:
                pass
        reminders.start_watcher(_on_reminder_fire)
    except Exception:
        pass

    # Screen watcher start
    try:
        import screen_watcher
        def on_screen_msg(msg):
            try:
                speak_with_interrupt(msg)
            except Exception as e:
                print(f"[screen-speak fail] {e}")
        screen_watcher.start_watching(on_screen_msg, interval=30)
        print("[screen-watcher] Active")
    except Exception as e:
        print(f"[screen-watcher fail] {e}")

    history = []
    while True:
        print("\n>>> 'Hey Jarvis' bolo...")
        woke = wait_for_wake_word(timeout_sec=60)
        if not woke:
            continue

        print(">>> Sun raha hoon...")
        user_input = listen()

        if not user_input:
            continue

        print(f"Tum: {user_input}")

        low = user_input.lower()
        if any(w in low for w in ("bye", "goodbye", "band karo", "shutdown")):
            speak_with_interrupt("Theek hai Boss, milte hain!")
            break

        if any(w in low for w in ["stop", "ruko", "chup"]):
            continue

        reply = ask_nova(user_input, history)
        speak_with_interrupt(reply)

        history.append({"role": "user", "content": user_input})
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
    if "--continuous" in sys.argv:
        continuous_mode()
    elif "--text" in sys.argv:
        text_mode()
    else:
        voice_mode()
