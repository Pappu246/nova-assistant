import os
import re
from collections import Counter

nova = "C:\\Users\\pyada\\Downloads\\nova"
SKIP = {"fix_", "test_", "check_", "make_", "add_", "remove_"}

imports = Counter()

for f in os.listdir(nova):
    if not f.endswith(".py"):
        continue
    if any(f.startswith(p) for p in SKIP):
        continue
    fp = os.path.join(nova, f)
    try:
        with open(fp, "r", encoding="utf-8") as fh:
            content = fh.read()
    except Exception:
        continue

    for m in re.finditer(r"^\s*import\s+([a-zA-Z0-9_]+)", content, re.MULTILINE):
        imports[m.group(1)] += 1
    for m in re.finditer(r"^\s*from\s+([a-zA-Z0-9_]+)", content, re.MULTILINE):
        imports[m.group(1)] += 1

LOCAL = {"main", "brain", "tools", "memory", "reminders", "wake", "voice_id",
         "screen_watcher", "browser_agent", "browser_prompt", "hud", "shutdown",
         "suno", "bolo", "identity"}

print("EXTERNAL IMPORTS:")
print("=" * 50)
for name, count in sorted(imports.items()):
    if name in LOCAL or name.startswith("_"):
        continue
    print(f"  {count:2d}x  {name}")
