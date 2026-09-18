import os
from google import genai

key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=key)

# Priority order - pehla jo chale wahi use karenge
CANDIDATES = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
]

working = None
for model in CANDIDATES:
    try:
        print(f"Trying {model}...", end=" ")
        resp = client.models.generate_content(
            model=model,
            contents="Reply in one word: ready"
        )
        print("OK ->", resp.text.strip()[:40])
        working = model
        break
    except Exception as e:
        print("FAIL:", str(e)[:80])

if working:
    print(f"\n>>> USE THIS MODEL: {working}")
    # Save to file
    with open("gemini_model.txt", "w") as f:
        f.write(working)
else:
    print("\nKoi model kaam nahi kiya. Thodi der baad try karo.")
