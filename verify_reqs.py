import importlib

# Map of import name -> pip name
PACKAGES = [
    ("whisper", "openai-whisper"),
    ("sounddevice", "sounddevice"),
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("edge_tts", "edge-tts"),
    ("playsound3", "playsound3"),
    ("pygame", "pygame"),
    ("openwakeword", "openwakeword"),
    ("onnxruntime", "onnxruntime"),
    ("speechbrain", "speechbrain"),
    ("torch", "torch"),
    ("torchaudio", "torchaudio"),
    ("groq", "groq"),
    ("ollama", "ollama"),
    ("pyautogui", "pyautogui"),
    ("pynput", "pynput"),
    ("psutil", "psutil"),
    ("mss", "mss"),
    ("PIL", "Pillow"),
    ("yt_dlp", "yt-dlp"),
    ("browser_use", "browser-use"),
    ("google.genai", "google-genai"),
    ("pytest", "pytest"),
]

print("Checking installed packages:")
print("=" * 50)

missing = []
for import_name, pip_name in PACKAGES:
    try:
        __import__(import_name)
        print(f"  OK    {pip_name}")
    except ImportError:
        print(f"  MISS  {pip_name}")
        missing.append(pip_name)

print()
if missing:
    print("Missing packages:")
    for p in missing:
        print(f"  pip install {p}")
else:
    print("All packages installed")
