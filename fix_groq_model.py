with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Update Groq model
src = src.replace(
    'GROQ_MODEL = "llama-3.3-70b-versatile"',
    'GROQ_MODEL = "openai/gpt-oss-120b"\nGROQ_FALLBACK = "openai/gpt-oss-20b"'
)
src = src.replace(
    'GROQ_MODEL = "llama-3.1-8b-instant"',
    'GROQ_MODEL = "openai/gpt-oss-120b"\nGROQ_FALLBACK = "openai/gpt-oss-20b"'
)

# Update _call_groq to try fallback
old_call = """def _call_groq(messages):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq llm fail] {str(e)[:100]}")
        return None"""

new_call = """def _call_groq(messages):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    client = Groq(api_key=key)

    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=200,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[groq {model} fail] {str(e)[:80]}")
            continue
    return None"""

if old_call in src:
    src = src.replace(old_call, new_call)

with open("brain.py", "w", encoding="utf-8") as f:
    f.write(src)
print("brain.py Groq model updated")
