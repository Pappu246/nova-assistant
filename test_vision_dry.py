import vision_agent

# DRY RUN - sirf find karega, click nahi karega
result = vision_agent.vision_click("Chrome browser icon", dry_run=True)
print()
print("Result:")
for k, v in result.items():
    print(f"  {k}: {v}")
