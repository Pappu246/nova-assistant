import sys, os, tempfile, asyncio

print("Python:", sys.version)
print()

try:
    import edge_tts
    print("edge_tts imported OK, version:", getattr(edge_tts, "__version__", "?"))
except Exception as e:
    print("edge_tts import FAIL:", type(e).__name__, e)

try:
    import pygame
    print("pygame imported OK")
except Exception as e:
    print("pygame import FAIL:", type(e).__name__, e)

print()

try:
    import edge_tts
    path = os.path.join(tempfile.gettempdir(), "test_nova.mp3")
    if os.path.exists(path):
        os.remove(path)

    async def gen():
        c = edge_tts.Communicate("Namaste boss, main NOVA hoon", "hi-IN-MadhurNeural")
        await c.save(path)

    print("TTS generate kar raha hoon...")
    asyncio.run(gen())
    print("File saved:", path)
    print("Size:", os.path.getsize(path), "bytes")
except Exception as e:
    import traceback
    print("TTS FAIL:")
    traceback.print_exc()
