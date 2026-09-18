with open("browser_agent.py", "r", encoding="utf-8") as f:
    src = f.read()

src = src.replace(
    "try:\n    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\nexcept Exception:\n    pass\n",
    ""
)
src = src.replace(
    'asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())',
    ''
)

with open("browser_agent.py", "w", encoding="utf-8") as f:
    f.write(src)
print("Browser fix applied")
