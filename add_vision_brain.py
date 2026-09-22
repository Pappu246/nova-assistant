with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add vision_click tool description
if "vision_click" not in src:
    src = src.replace(
        "copy_to_clipboard(text), type_text(text),",
        "copy_to_clipboard(text), type_text(text), vision_click(target),"
    )
    # Add rule
    src = src.replace(
        '4. BROWSER (sirf explicit "browser mein", "google pe"):',
        '''VISION CLICK (screen pe kisi bhi element pe click):
   - "X pe click karo" / "X dhundo aur click karo" -> vision_click {"target": "English description"}
   - "Taskbar mein YouTube kholo" -> vision_click {"target": "YouTube icon in taskbar"}
   - "Red button pe click karo" -> vision_click {"target": "red button"}
   - Target description ENGLISH mein do
   - Sirf screen elements ke liye (icons, buttons, links on desktop)

4. BROWSER (sirf explicit "browser mein", "google pe"):'''
    )

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("brain.py - vision_click rules added")
