import edge_tts, asyncio, os

async def gen():
    text = "Namaste Boss, main NOVA hoon. Aaj mausam bahut accha hai, kaam shuru karein?"
    c = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+0%", pitch="+0Hz")
    await c.save("C:/Users/pyada/Downloads/nova/voice_test.mp3")

asyncio.run(gen())
os.startfile("C:/Users/pyada/Downloads/nova/voice_test.mp3")
