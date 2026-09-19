import os

nova = "C:\\Users\\pyada\\Downloads\\nova"

# Junk files
junk = [
    "chill",
    "gemini_model.txt",
    "import os.txt",
    "nova.txt",
    "function nova { Set-Location CUsers.txt",
    "cleanup.py",
    "check_size.py",
    "N14_PROVIDER_ROUTER.md",
    "en-AU-NatashaNeural.mp3",
    "en-GB-LibbyNeural.mp3",
    "en-US-GuyNeural.mp3",
    "en-US-JennyNeural.mp3",
]

for f in junk:
    fp = os.path.join(nova, f)
    if os.path.exists(fp):
        try:
            os.remove(fp)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Skip {f}: {e}")

print()
print("Remaining files:")
for f in sorted(os.listdir(nova)):
    fp = os.path.join(nova, f)
    if os.path.isfile(fp):
        print(f"  {f}")
    elif os.path.isdir(fp) and not f.startswith("."):
        print(f"  [DIR] {f}/")
