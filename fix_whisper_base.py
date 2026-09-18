import re
with open("suno.py", "r", encoding="utf-8") as f:
    src = f.read()

# tiny -> base
src = re.sub(r'whisper\.load_model\("tiny"\)', 'whisper.load_model("base")', src)

# Print message
src = src.replace(
    "Whisper tiny load ho raha hai (super fast)...",
    "Whisper base load ho raha hai (fast + accurate)..."
)

with open("suno.py", "w", encoding="utf-8") as f:
    f.write(src)
print("suno.py -> base")
