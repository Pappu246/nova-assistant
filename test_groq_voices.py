import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

VOICES = ["dan", "leo", "zac", "tara", "leah", "jess", "mia", "zoe"]
TEXT = "Namaste Boss, main NOVA hoon. Kaam shuru karein?"

for v in VOICES:
    try:
        print(f"Generating {v}...")
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice=v,
            input=TEXT,
            response_format="wav",
        )
        fname = f"voice_{v}.wav"
        response.write_to_file(fname)
        print(f"  OK -> {fname}")
    except Exception as e:
        print(f"  FAIL {v}: {str(e)[:100]}")

print("\nDone! Ab ye chalao:")
print('Get-ChildItem voice_*.wav | ForEach-Object { Start-Process $_.FullName; Start-Sleep 6 }')