import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
try:
    models = client.models.list()
    print("Available Groq models:")
    for m in models.data:
        print(f"  {m.id}")
except Exception as e:
    print("Fail:", e)
