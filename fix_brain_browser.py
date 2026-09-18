with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

if "close_browser" not in src:
    # Add tool description
    src = src.replace(
        '7. browse - {"task": "user ki poori command"}',
        '7. browse - {"task": "user ki poori command"}  (SMART browser)\n7b. close_browser - {}  (browser band karo - sirf jab user "browser band karo" bole)'
    )

    # Add rule in priority 3
    src = src.replace(
        "Warna browse USE MAT KARO.",
        """Warna browse USE MAT KARO.

- "browser band karo" / "chrome band karo" -> close_browser {}
- Browser apne aap kabhi band nahi hoga - sirf user bole tab.""",
        1
    )

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("brain.py updated")
