import edge_tts, asyncio, os

VOICES = [
    ("en-US-JennyNeural", "+0%", "+0Hz"),
    ("en-US-GuyNeural", "+0%", "+0Hz"),
    ("en-GB-LibbyNeural", "+0%", "+0Hz"),
    ("en-AU-NatashaNeural", "+0%", "+0Hz"),
]

TEXT = "Namaste Boss, main NOVA hoon. Kaam shuru karein?"

async def gen():
    for v, r, p in VOICES:
        fname = v + ".mp3"
        c = edge_tts.Communicate(TEXT, v, rate=r, pitch=p)
        await c.save(fname)
        print("OK", fname)

asyncio.run(gen())
