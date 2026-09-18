import edge_tts, asyncio, os
async def gen():
    c = edge_tts.Communicate(
        "Namaste boss, main NOVA hoon. Aaj mausam bahut accha hai.",
        "hi-IN-SwaraNeural", rate="+0%", pitch="+0Hz"
    )
    await c.save("C:/Users/pyada/Downloads/nova/test_voice.mp3")
asyncio.run(gen())
os.startfile("C:/Users/pyada/Downloads/nova/test_voice.mp3")
