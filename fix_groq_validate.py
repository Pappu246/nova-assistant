with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

# Update _call_groq: JSON validate karo before return
old_call = """    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=200,
            )
            raw = resp.choices[0].message.content.strip()
            clean = _extract_json(raw)
            return clean if clean else raw
        except Exception as e:
            print(f"[groq {model} fail] {str(e)[:80]}")
            continue
    return None"""

new_call = """    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=200,
            )
            raw = resp.choices[0].message.content.strip()
            clean = _extract_json(raw)
            if clean:
                # JSON valid hai? Verify karo
                try:
                    parsed = json.loads(clean)
                    if isinstance(parsed, dict) and "tool" in parsed:
                        return clean
                    else:
                        print(f"[groq {model}] JSON mein 'tool' key nahi, fallback")
                        continue
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[groq {model}] invalid JSON: {str(e)[:50]}")
                    continue
        except Exception as e:
            print(f"[groq {model} fail] {str(e)[:80]}")
            continue
    return None"""

if old_call in src:
    src = src.replace(old_call, new_call)
    with open("brain.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("brain.py Groq JSON validation applied")
else:
    print("Old call block not found")
