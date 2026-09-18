import os
from elevenlabs.client import ElevenLabs

key = os.environ.get("ELEVENLABS_API_KEY")
print("Key:", (key[:15] + "...") if key else "NAHI MILI")
print()

client = ElevenLabs(api_key=key)

print("=== Available Voices ===")
try:
    voices = client.voices.get_all()
    for v in voices.voices[:15]:
        print("  " + v.voice_id + "  " + v.name + "  (" + str(v.category) + ")")
except Exception as e:
    print("Voices list fail:", str(e)[:300])

print()
print("=== Testing voice KfwNTJ4LG6Kz5gi0fnqc ===")
try:
    audio = client.text_to_speech.convert(
        voice_id="KfwNTJ4LG6Kz5gi0fnqc",
        text="Test",
        model_id="eleven_multilingual_v2",
    )
    data = b"".join(audio)
    print("OK - " + str(len(data)) + " bytes")
except Exception as e:
    print("FULL ERROR:")
    print(str(e))
    print("Type:", type(e).__name__)