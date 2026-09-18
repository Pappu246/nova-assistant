import edge_tts, asyncio, os

VOICES = [
    ("en-US-AvaMultilingualNeural",   "Ava - US female, ultra natural"),
    ("en-US-AndrewMultilingualNeural", "Andrew - US male, ultra natural"),
    ("en-US-EmmaMultilingualNeural",  "Emma - US female"),
    ("en-US-BrianMultilingualNeural", "Brian - US male"),
    ("en-GB-SoniaNeural",             "Sonia - British female"),
    ("en-GB-RyanNeural",              "Ryan - British male (Jarvis)"),
    ("hi-IN-SwaraNeural",             "Swara - Hindi female"),
    ("hi-IN-MadhurNeural",            "Madhur - Hindi male (current)"),
]

TEXT = "Namaste Boss, main NOVA hoon. Aaj ka mausam bahut accha hai. Kaam shuru karein?"

async def gen_all():
    for voice, desc in VOICES:
        fname = f"v_{voice.replace('-', '_')}.mp3"
        try:
            c = edge_tts.Communicate(TEXT, voice, rate="+5%", pitch="+0Hz")
            await c.save(fname)
            print(f"OK  {voice:35s} | {desc}")
        except Exception as e:
            print(f"FAIL {voice}: {e}")

asyncio.run(gen_all())
print("\nDone! Files:")
import glob
for f in sorted(glob.glob("v_*.mp3")):
    print(" ", f)
