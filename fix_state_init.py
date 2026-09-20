with open("main.py", "r", encoding="utf-8-sig") as f:
    src = f.read()

# Find continuous_mode and add state init at top
old = '''def continuous_mode():
    """Continuous - 'Hey Jarvis' ki zaroorat nahi. Sirf bolo, kaam kare."""
    from suno import listen, listen_continuous
    from bolo import speak, stop_speaking, start_esc_listener

    start_esc_listener()'''

new = '''def continuous_mode():
    """Continuous - 'Hey Jarvis' ki zaroorat nahi. Sirf bolo, kaam kare."""
    from suno import listen, listen_continuous
    from bolo import speak, stop_speaking, start_esc_listener

    state = agent_state.get_state()
    state.set_mode("idle")

    start_esc_listener()'''

if old in src:
    src = src.replace(old, new)
    print("state init at top of continuous_mode")
else:
    # Try alternate
    if "def continuous_mode" in src and "state = agent_state.get_state()" not in src.split("def continuous_mode")[1][:500]:
        # Just insert after function def line
        lines = src.split("\n")
        new_lines = []
        inserted = False
        in_continuous = False
        for line in lines:
            new_lines.append(line)
            if "def continuous_mode" in line:
                in_continuous = True
                continue
            if in_continuous and not inserted and line.strip().startswith('"""') and line.strip().endswith('"""'):
                # After docstring
                new_lines.append("    state = agent_state.get_state()")
                new_lines.append("    state.set_mode(\"idle\")")
                inserted = True
            elif in_continuous and not inserted and line.strip() and not line.strip().startswith('"""'):
                # First non-docstring line
                new_lines.insert(-1, "    state = agent_state.get_state()")
                new_lines.insert(-1, "    state.set_mode(\"idle\")")
                inserted = True
                in_continuous = False
        src = "\n".join(new_lines)
        print("state init inserted via alternate method")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Done")
