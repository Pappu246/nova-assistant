import edge_tts, asyncio, os

VOICES = [
    ("en-IN-NeerjaNeural", "+0%", "+0Hz"),
    ("en-IN-PrabhatNeural", "+0%", "+0Hz"),
    ("en-US-AvaMultilingualNeural", "-5%", "-5Hz"),
    ("en-US-AndrewMultilingualNeural", "-5%", "-5Hz"),
]

TEXT = "Namaste Boss, main NOVA hoon. Aaj ka mausam bahut accha hai, kaam shuru karein?"

async def gen():
    for v, r, p in VOICES:
        fname = v + ".mp3"
        c = edge_tts.Communicate(TEXT, v, rate=r, pitch=p)
        await c.save(fname)
        print("OK", fname)

asyncio.run(gen())
print("\nSaari files ban gayi. Sunno:")
for v, _, _ in VOICES:
    print(" ", v + ".mp3")