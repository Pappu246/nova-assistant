import vision_agent
import time

print("3 second mein Notepad dhundo aur click karega...")
time.sleep(3)

result = vision_agent.tool_vision_click({"target": "Notepad icon in taskbar"})
print()
print("Result:", result)
