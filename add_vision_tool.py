with open("tools.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add import at top
if "from vision_agent import" not in src:
    src = src.replace(
        "import time\n",
        "import time\n\ntry:\n    from vision_agent import tool_vision_click\nexcept Exception:\n    def tool_vision_click(a): return 'Vision agent load nahi hua.'\n",
        1
    )

# Add to registry
if '"vision_click":' not in src:
    src = src.replace(
        '"web_search": web_search,',
        '"web_search": web_search,\n    "vision_click": tool_vision_click,'
    )

with open("tools.py", "w", encoding="utf-8") as f:
    f.write(src)
print("tools.py - vision_click added")
