with open("policy.py", "r", encoding="utf-8") as f:
    src = f.read()

# Fix shutdown message - ensure valid mode
old = '''        "shutdown_pc": f"{args.get('mode', 'shutdown')} karna hai?",'''
new = '''        "shutdown_pc": f"{'restart' if 'restart' in str(args).lower() else 'shutdown' if 'shutdown' in str(args).lower() or 'band' in str(args).lower() else 'PC band ya restart'} karna hai?",'''

if old in src:
    src = src.replace(old, new)
    print("Shutdown message fixed")

with open("policy.py", "w", encoding="utf-8") as f:
    f.write(src)
