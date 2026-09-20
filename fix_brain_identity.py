with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add identity rules
if "IDENTITY RULES" not in src:
    src = src.replace(
        "1. MEMORY:",
        '''1. IDENTITY (VERY IMPORTANT):
   - "mera naam X hai" -> remember {"key": "user_name", "value": "X"}
   - Never invent a name
   - Never change user_name without user saying so
   - If user asks "mera naam kya hai" and no name -> reply "Boss"

2. MEMORY:'''
    )

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("brain.py identity rules added")
