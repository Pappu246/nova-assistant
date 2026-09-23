"""
NOVA Synthesis - raw tool result ko clean Hinglish answer mein convert.
"""
import os


def synthesize(user_query, tool_result):
    """Tool result -> clean 1-2 sentence Hinglish answer."""
    try:
        from groq import Groq
    except Exception:
        return str(tool_result)

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return str(tool_result)

    result_str = str(tool_result)[:1500]
    if not result_str.strip():
        return "Kuch result nahi mila."

    prompt = (
        "Boss ne pucha: " + user_query + "\n\n"
        "Tool ne ye raw data diya:\n" + result_str + "\n\n"
        "Ab BOSS ko ek SHORT, CLEAN Hinglish jawab do (1-2 sentences).\n\n"
        "Rules:\n"
        "- Sirf SAHI info do jo tool ne di hai - apne se kuch add MAT karo\n"
        "- Agar data me 'Samrat Choudhary... 24th Chief Minister since 15 April 2026' hai\n"
        "  to bolo 'Bihar ke CM Samrat Choudhary hain (15 April 2026 se)'\n"
        "- Agar multiple results hain, best wala pick karo\n"
        "- Agar data wiki ya Hindi me hai, Hinglish me convert karo\n"
        "- 'Boss' ya 'Ji' use karo\n"
        "- Sirf jawab do, aur kuch nahi\n"
        "- Agar sahi answer nahi mila, to bolo 'Sahi info nahi mili Boss'\n\n"
        "Jawab:"
    )

    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
            timeout=15,
            reasoning_effort="low",
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("[synthesis] fail: " + str(e)[:80])
        return str(tool_result)


if __name__ == "__main__":
    print(synthesize(
        "Bihar CM kaun hai",
        "Chief Minister of Bihar - Wikipedia: ... Samrat Choudhary is serving as the 24th Chief Minister of Bihar since 15 April 2026."
    ))
