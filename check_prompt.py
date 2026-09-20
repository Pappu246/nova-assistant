with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Check if agent_run is mentioned
if "agent_run" in src:
    print("agent_run IS mentioned")
    # Find context
    idx = src.find("agent_run")
    print()
    print("Context around agent_run:")
    print(src[max(0, idx-300):idx+300])
else:
    print("agent_run NOT in prompt")
