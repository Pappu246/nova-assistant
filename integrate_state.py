with open("main.py", "r", encoding="utf-8-sig") as f:
    src = f.read()

# Add import
if "import agent_state" not in src:
    src = src.replace(
        "import sys\nimport re",
        "import sys\nimport re\nimport agent_state"
    )

# Set mode when listening / thinking / speaking in continuous_mode
# Find continuous_mode function and add state tracking
old_loop_start = '''    while True:
        # Check typed input first (higher priority)'''

new_loop_start = '''    state = agent_state.get_state()

    while True:
        state.set_mode("listening")
        # Check typed input first (higher priority)'''

if old_loop_start in src:
    src = src.replace(old_loop_start, new_loop_start)
    print("Loop start updated")

# Track user input + speaking mode
old_after_hear = '''        last_activity = time.time()
        print(f"Tum: {text}")'''
new_after_hear = '''        print(f"Tum: {text}")
        state.add_to_context("user", text)
        state.record_observation(text)'''
if old_after_hear in src:
    src = src.replace(old_after_hear, new_after_hear)
    print("User input tracking added")

# Track speaking mode around reply
old_speak = '''        reply = ask_nova(text, history)
        if _HUD:
            hud.update("nova", reply)
            hud.update("status", "Bol raha hoon...")
        speak_with_interrupt(reply)
        if _HUD:
            hud.update("status", "Ready")'''
new_speak = '''        state.set_mode("thinking")
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
            hud.update("status", "Ready")'''
if old_speak in src:
    src = src.replace(old_speak, new_speak)
    print("Speaking mode tracking added")

# Also in voice_mode
old_voice = '''        reply = ask_nova(user_input, history)
        speak_with_interrupt(reply)'''
new_voice = '''        state = agent_state.get_state()
        state.set_mode("thinking")
        state.add_to_context("user", user_input)
        reply = ask_nova(user_input, history)
        state.add_to_context("assistant", reply)
        state.set_mode("speaking")
        speak_with_interrupt(reply)
        state.set_mode("idle")'''
if old_voice in src:
    src = src.replace(old_voice, new_voice)
    print("Voice mode tracking added")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Done")
