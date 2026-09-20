with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add shutdown mode rules to prompt
if "shutdown_pc - mode STRICT" not in src:
    src = src.replace(
        "shutdown_pc(mode), ",
        "shutdown_pc(mode: STRICT 'shutdown'/'restart'/'cancel'), "
    )
    # Also add specific example
    src = src.replace(
        '"shutdown karo" -> set_reminder',
        '"shutdown karo" -> shutdown_pc {"mode": "shutdown"}'
    )

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Prompt updated")
