import os
import base64
import numpy as np
from scipy.io.wavfile import write as write_wav
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents="Namaste Boss, main NOVA hoon. Aaj mausam bahut accha hai.",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Charon"
                )
            )
        )
    )
)

part = response.candidates[0].content.parts[0]
audio_data = part.inline_data.data

# Base64 string ko bytes mein convert karo
if isinstance(audio_data, str):
    audio_data = base64.b64decode(audio_data)

print("Raw audio bytes:", len(audio_data))
print("First 20 bytes (hex):", audio_data[:20].hex())

# Method 1: Direct WAV with scipy (16-bit PCM, 24000 Hz)
try:
    # int16 numpy array banao
    samples = np.frombuffer(audio_data, dtype=np.int16)
    write_wav("gemini_voice.wav", 24000, samples)
    print("Method 1 OK - size:", os.path.getsize("gemini_voice.wav"))
except Exception as e:
    print("Method 1 fail:", e)

# Method 2: Try 22050 Hz if 24000 fails
try:
    samples = np.frombuffer(audio_data, dtype=np.int16)
    write_wav("gemini_voice_22k.wav", 22050, samples)
    print("Method 2 OK (22kHz)")
except Exception as e:
    print("Method 2 fail:", e)

# Play
os.startfile("gemini_voice.wav")