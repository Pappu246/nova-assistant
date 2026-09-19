import os

nova = "C:\\Users\\pyada\\Downloads\\nova"

# Important files jo HONI chahiye
must_have = [
    "main.py", "suno.py", "bolo.py", "brain.py", "tools.py",
    "voice_id.py", "wake.py", "screen_watcher.py",
    "browser_agent.py", "browser_prompt.py",
    "reminders.py", "memory.py", "hud.py",
    "server.py", "shutdown.py",
    "nova_startup.bat", "nova_stop.bat", "nova_silent.vbs",
    "requirements.txt", "README.md", ".gitignore",
    "nova_memory.db", "boss_voice.pkl", "reminders.json",
]

print("=" * 60)
print("  VERIFY: Important Files")
print("=" * 60)
print()

all_ok = True
for f in must_have:
    fp = os.path.join(nova, f)
    if os.path.exists(fp):
        size = os.path.getsize(fp) / 1024
        print(f"  OK       {size:7.1f} KB  {f}")
    else:
        print(f"  MISSING  ---------   {f}")
        all_ok = False

print()

# Directories
for d in ["web"]:
    dp = os.path.join(nova, d)
    if os.path.exists(dp):
        files = os.listdir(dp)
        print(f"  OK       [DIR] {d}/ ({len(files)} files)")
        for f in files:
            print(f"             - {f}")
    else:
        print(f"  MISSING  [DIR] {d}/")
        all_ok = False

print()
print("=" * 60)
if all_ok:
    print("  All important files present")
else:
    print("  Some files missing - check above")
print("=" * 60)
