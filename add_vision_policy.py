with open("policy.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add vision_click to ASK (screen click = reversible but sensitive)
if '"vision_click"' not in src:
    src = src.replace(
        '"open_app": ASK,',
        '"open_app": ASK,\n    "vision_click": ASK,   # Clicks on screen, needs confirm'
    )

# Add confirmation message
if 'vision_click' not in src.split("def make_confirmation_message")[1][:800]:
    src = src.replace(
        '"open_app": f"\'{args.get(\'app_name\', \'app\')}\' kholna hai?",',
        '"open_app": f"\'{args.get(\'app_name\', \'app\')}\' kholna hai?",\n        "vision_click": f"Screen pe \'{args.get(\'target\', \'kya\')}\' pe click karna hai?",'
    )

with open("policy.py", "w", encoding="utf-8") as f:
    f.write(src)
print("policy.py - vision_click classified")
