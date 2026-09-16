"""
NOVA — Phase 1 (text-based, fully free)

Chalane ka tareeka:
    python main.py

Exit karne ke liye "bye", "exit", ya "quit" type karo.
"""

from brain import ask_nova

def main():
    print("=" * 40)
    print("  NOVA — ready hoon. Kya madad karoon?")
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

        # Conversation history update karo (taaki context yaad rahe)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

        # History bahut lambi na ho jaye, isliye limit rakho
        if len(history) > 20:
            history = history[-20:]


if __name__ == "__main__":
    main()
