"""
NOVA — Wake Word + Voice mode.
Ab NOVA 'Hey Jarvis' sune, tabhi command lega.
"""

import sys
from brain import ask_nova
from bolo import speak


def voice_mode():
    from suno import listen
    from wake import wait_for_wake_word

    print("=" * 50)
    print("  NOVA — 'Hey Jarvis' bolo, phir command do")
    print("  (band karne ke liye 'bye' bolo)")
    print("=" * 50)

    speak("Hello Boss, NOVA ready hai.")

    history = []
    wake_loaded = False

    while True:
        # Wake word ka wait karo
        if not wake_loaded:
            print("\n>>> 'Hey Jarvis' bolne ka wait kar raha hoon...")
        else:
            print("\n>>> 'Hey Jarvis' bolo...")

        woke = wait_for_wake_word(timeout_sec=None)
        wake_loaded = True

        if not woke:
            # Fallback mode (agar wake word fail ho gaya)
            print("(wake word timeout, direct sun raha hoon)")

        print(">>> Sun raha hoon...")

        user_input = listen()

        if not user_input:
            print("(kuch samajh nahi aaya, dobara 'Hey Jarvis' bolo)")
            continue

        print(f"Tum: {user_input}")

        low = user_input.lower()
        if any(word in low for word in ("bye", "band karo", "exit", "goodbye")):
            speak("Theek hai Boss, milte hain!")
            break

        reply = ask_nova(user_input, history)
        speak(reply)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = history[-20:]


def text_mode():
    print("=" * 40)
    print("  NOVA — text mode")
    print("=" * 40)

    history = []
    while True:
        user_input = input("\nTum: ").strip()
        if user_input.lower() in ("bye", "exit", "quit"):
            print("NOVA: Theek hai, milte hain!")
            break
        if not user_input:
            continue
        reply = ask_nova(user_input, history)
        print(f"NOVA: {reply}")
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = history[-20:]


def voice_mode_no_wake():
    """Wake word ke bina — purana tareeka (backup)."""
    from suno import listen

    print("=" * 50)
    print("  NOVA — Voice mode (no wake word)")
    print("=" * 50)

    speak("Hello Boss, NOVA ready hai.")

    history = []
    while True:
        user_input = listen()
        if not user_input:
            continue
        print(f"Tum: {user_input}")
        low = user_input.lower()
        if any(word in low for word in ("bye", "band karo", "exit")):
            speak("Theek hai, milte hain!")
            break
        reply = ask_nova(user_input, history)
        speak(reply)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 20:
            history = history[-20:]


if __name__ == "__main__":
    if "--text" in sys.argv:
        text_mode()
    elif "--no-wake" in sys.argv:
        voice_mode_no_wake()
    else:
        voice_mode()
