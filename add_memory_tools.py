import re

with open("tools.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add import at top
if "from memory import" not in src:
    src = src.replace(
        "import time\n",
        "import time\n\ntry:\n    from memory import tool_remember, tool_recall, tool_forget, tool_note, tool_list_notes\nexcept Exception:\n    def tool_remember(a): return 'Memory load nahi hui.'\n    def tool_recall(a): return 'Memory load nahi hui.'\n    def tool_forget(a): return 'Memory load nahi hui.'\n    def tool_note(a): return 'Memory load nahi hui.'\n    def tool_list_notes(a): return 'Memory load nahi hui.'\n",
        1
    )

# Add to TOOLS registry
if '"remember": tool_remember' not in src:
    src = src.replace(
        '"web_search": web_search,',
        '"web_search": web_search,\n    "remember": tool_remember,\n    "recall": tool_recall,\n    "forget": tool_forget,\n    "note": tool_note,\n    "list_notes": tool_list_notes,'
    )

with open("tools.py", "w", encoding="utf-8") as f:
    f.write(src)

print("tools.py updated")