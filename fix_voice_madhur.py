with open("bolo.py", "r", encoding="utf-8") as f:
    src = f.read()

# Edge voice settings update
import re

# Voice
src = re.sub(
    r'EDGE_VOICE\s*=\s*"[^"]*"',
    'EDGE_VOICE = "hi-IN-MadhurNeural"',
    src
)
# Rate
src = re.sub(
    r'EDGE_RATE\s*=\s*"[^"]*"',
    'EDGE_RATE = "+5%"',
    src
)
# Pitch
src = re.sub(
    r'EDGE_PITCH\s*=\s*"[^"]*"',
    'EDGE_PITCH = "+0Hz"',
    src
)

with open("bolo.py", "w", encoding="utf-8") as f:
    f.write(src)
print("bolo.py updated to Madhur")
