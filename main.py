"""
NOVA — Phase 2 (Voice: Speech-to-Text + Text-to-Speech, free/local)

Chalane ka tareeka:
    python main.py

Voice mode default hai. Agar sirf text se kaam chalana ho (jaise mic na
ho), to chalao: python main.py --text
"""

import sys
from brain import ask_nova
from bolo import speak


def voice_mode():
    from suno import listen

    print("=" * 40)
    print("  NOVA — ready hoon. Bolke baat karo.")
    print("  (band karne ke liye 'bye' bolo)")
    print("=" * 40)

    speak("Hello Boss, NOVA ready hai.")

    history = []

    while True:
        user_input = listen()

        if not user_input:
            print("(kuch samajh nahi aaya, dobara try karo)")
            continue

        print(f"Tum: {user_input}")

        if any(word in user_input.lower() for word in ("bye", "band karo", "exit")):
            speak("Theek hai, milte hain!")
            break

        reply = ask_nova(user_input, history)
        speak(reply)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

        if len(history) > 20:
            history = history[-20:]


def text_mode():
    print("=" * 40)
    print("  NOVA — text mode. Kya madad karoon?")
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


if __name__ == "__main__":
    if "--text" in sys.argv:
        text_mode()
    else:
        voice_mode()
