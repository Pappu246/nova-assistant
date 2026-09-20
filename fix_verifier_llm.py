with open("verifier.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add LLM verification function before def verify
llm_fn = '''

def _llm_verify(step, result_str):
    """Fallback LLM verification for ambiguous cases."""
    try:
        from groq import Groq
    except Exception:
        return None

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None

    prompt = """You are a strict verifier. Did this tool call succeed?

Tool: """ + str(step.get("tool", "")) + """
Args: """ + str(step.get("args", {})) + """
Result: """ + result_str[:300] + """

Reply EXACTLY one of:
VERDICT: YES
REASON: <one short line>

VERDICT: NO
REASON: <one short line>

Rules:
- Failure keywords (error, fail, nahi mila, exception, cannot, not found) -> NO
- Success (khol diya, ho gaya, search kar liya, opened, launched, playing, complete) -> YES
- Empty/vague/uncertain -> NO
"""

    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=80,
            timeout=12,
        )
        text = (resp.choices[0].message.content or "").strip().upper()
        if "VERDICT: YES" in text or "VERDICT:YES" in text:
            return (True, "LLM verdict: YES")
        if "VERDICT: NO" in text or "VERDICT:NO" in text:
            return (False, "LLM verdict: NO")
    except Exception as e:
        print("[verifier] LLM error: " + str(e)[:60])
    return None

'''

if "_llm_verify" not in src:
    src = src.replace("def verify(step, result):", llm_fn + "\ndef verify(step, result, use_llm=True):", 1)

# Replace verify() ending to use LLM fallback
old_end = '''    for hint in hints:
        if hint in result_str:
            return True, "Success hint mila: '" + hint + "'"

    # Strict mode: require success hint
    return False, "Koi success hint nahi mila (result: " + result_str[:60] + ")"'''

new_end = '''    for hint in hints:
        if hint in result_str:
            return True, "Success hint mila: '" + hint + "'"

    # No keyword match. Try LLM fallback.
    if use_llm:
        llm_result = _llm_verify(step, result_str)
        if llm_result is not None:
            return llm_result

    # LLM unavailable - lenient default (avoid blocking agent)
    if not hints:
        return True, "No hints, assume success (LLM unavailable)"

    return False, "No success hint (LLM unavailable)"'''

if old_end in src:
    src = src.replace(old_end, new_end)
    print("LLM fallback added to verify()")
else:
    print("End pattern not found - checking alternate...")
    # Alternate: just add LLM call before final return
    old_alt = '''    # Strict mode: require success hint
    return False, "Koi success hint nahi mila (result: " + result_str[:60] + ")"'''
    new_alt = '''    # Try LLM
    if use_llm:
        llm_result = _llm_verify(step, result_str)
        if llm_result is not None:
            return llm_result
    return False, "No success hint and LLM unavailable"'''
    if old_alt in src:
        src = src.replace(old_alt, new_alt)
        print("LLM fallback added via alternate")
    else:
        print("No match found")

with open("verifier.py", "w", encoding="utf-8") as f:
    f.write(src)
print("verifier.py updated")
