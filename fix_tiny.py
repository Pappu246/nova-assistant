with open("suno.py", "r", encoding="utf-8") as f:
    src = f.read()

# Print message
src = src.replace(
    "Whisper model load ho raha hai (base - fast)...",
    "Whisper tiny load ho raha hai (super fast)..."
)

# Force tiny - exact string replace
src = src.replace('_model = whisper.load_model("base")', '_model = whisper.load_model("tiny")')
src = src.replace('_model = whisper.load_model("small")', '_model = whisper.load_model("tiny")')
src = src.replace("_model = whisper.load_model('base')", '_model = whisper.load_model("tiny")')

with open("suno.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Done")
