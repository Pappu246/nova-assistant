with open("tools.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add close_browser function before TOOLS dict
close_fn = '''
def close_browser(_args=None):
    """Chromium browser ko band karo (jab user bole)."""
    try:
        import subprocess
        if platform.system() == "Windows":
            # Sirf browser-use ka chromium band karo
            subprocess.run(
                ["taskkill", "/F", "/IM", "chrome.exe", "/FI", "WINDOWTITLE eq *"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Chromium bhi try
            subprocess.run(
                ["taskkill", "/F", "/IM", "chromium.exe"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return "Browser band kar diya."
    except Exception as e:
        return f"Browser band nahi hua: {e}"
    return "Sirf Windows pe."


'''

if "def close_browser" not in src:
    src = src.replace("\nTOOLS = {", close_fn + "\nTOOLS = {", 1)

# Add to registry
if '"close_browser": close_browser' not in src:
    src = src.replace(
        '"browse": browse,',
        '"browse": browse,\n    "close_browser": close_browser,'
    )

with open("tools.py", "w", encoding="utf-8") as f:
    f.write(src)
print("tools.py updated - close_browser added")
