with open("brain.py", "r", encoding="utf-8") as f:
    src = f.read()

old = """def _call_groq(messages):
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

new = """def _extract_json(text):
    \"\"\"Text se JSON object nikalo, chahe markdown ho ya extra text.\"\"\"
    if not text:
        return None
    text = text.strip()
    # Markdown code fence hatao
    if "```" in text:
        import re
        m = re.search(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    # Pehla { aur last } ke beech ka content
    if "{" in text and "}" in text:
        start = text.index("{")
        end = text.rindex("}") + 1
        text = text[start:end]
    try:
        return text
    except Exception:
        return None


def _call_groq(messages):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    client = Groq(api_key=key)

    # System prompt ke saath ek extra nudge
    messages = list(messages)
    messages[0] = {
        "role": "system",
        "content": messages[0]["content"] + "\\n\\nIMPORTANT: Reply with ONLY a valid JSON object. No markdown, no code fence, no explanation."
    }

    for model in [GROQ_MODEL, GROQ_FALLBACK]:
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

if old in src:
    src = src.replace(old, new)
    with open("brain.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("brain.py Groq JSON fix applied")
else:
    print("Old _call_groq not found")
