import warnings
warnings.filterwarnings("ignore")
import asyncio

import os
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from browser_use import Agent, Browser
    from browser_use.llm import ChatGoogle
    _BU = True
except Exception as e:
    print(f"[browser_agent import fail] {e}")
    _BU = False

try:
    from google import genai
    _GENAI = True
except Exception:
    _GENAI = False

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]


def _gemini_call(prompt, max_retries=3):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None, "GEMINI_API_KEY set nahi hai."
    client = genai.Client(api_key=key)
    for attempt in range(max_retries):
        for model in MODELS:
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                return resp.text.strip(), model
            except Exception as e:
                err = str(e)[:80]
                if "503" in err or "UNAVAILABLE" in err or "404" in err or "NOT_FOUND" in err:
                    continue
                print(f"[gemini] {model}: {err}")
                continue
        if attempt < max_retries - 1:
            print(f"[gemini] Retry in 3s ({attempt+1}/{max_retries})...")
            time.sleep(3)
    return None, "Saare Gemini models busy."


async def _browse_task(task_english, model):
    llm = ChatGoogle(model=model)
    fallback = None
    for fb in MODELS:
        if fb != model:
            try:
                fallback = ChatGoogle(model=fb)
                break
            except Exception:
                continue
    browser = Browser(
        headless=False,
        keep_alive=False,          # Stable: task ke baad clean exit
    )
    agent = Agent(
        task=task_english,
        llm=llm,
        fallback_llm=fallback,
        browser=browser,
        use_vision=True,
    )
    try:
        result = await agent.run(max_steps=25)
        return result
    finally:
        # CDP session clean close
        try:
            await browser.close()
        except Exception:
            pass


def _extract_result(result):
    try:
        fr = result.final_result()
        if fr:
            return str(fr)
    except Exception:
        pass
    try:
        if hasattr(result, "all_results"):
            for r in reversed(result.all_results):
                if hasattr(r, "is_done") and r.is_done:
                    if hasattr(r, "extracted_content") and r.extracted_content:
                        return str(r.extracted_content)
                    if hasattr(r, "long_term_memory") and r.long_term_memory:
                        return str(r.long_term_memory)
    except Exception:
        pass
    try:
        if hasattr(result, "all_results") and result.all_results:
            last = result.all_results[-1]
            if hasattr(last, "long_term_memory") and last.long_term_memory:
                return str(last.long_term_memory)
    except Exception:
        pass
    return str(result)[:800]


def browse(args):
    if not _BU:
        return "browser-use install nahi hai."
    if not _GENAI:
        return "google-genai install nahi hai."

    task = args.get("task", "").strip()
    if not task:
        return "Kya browser me karna hai, bolo?"

    translate_prompt = f"""Convert this Hindi/Hinglish command into a clear English instruction for a browser automation agent.

User's command: {task}

Rules:
- Be specific and actionable
- Include exact URLs (youtube.com, amazon.in, google.com)
- "bajao"/"play" -> go to youtube, search, click first video, ensure playing
- "dhundho"/"search"/"price"/"mausam" -> search and EXTRACT the actual info from the page
- Keep under 2 sentences

Return ONLY the English task."""

    english_task, used_model = _gemini_call(translate_prompt)
    if not english_task:
        return f"Translation fail: {used_model}"

    print(f"[browser] Model: {used_model}")
    print(f"[browser] Task (EN): {english_task}")

    try:
        result = asyncio.run(_browse_task(english_task, used_model))
    except Exception as e:
        return f"Browser fail: {e}"

    final_answer = _extract_result(result)
    print(f"[browser] Extracted answer: {final_answer[:300]}")

    try:
        success = result.is_successful()
    except Exception:
        success = None
    print(f"[browser] Success flag: {success}")

    summary_prompt = f"""User ne ye command di: {task}

Browser agent ka final result:
---
{final_answer}
---

Ab Hinglish summary banao (2 lines max). STRICT RULES:
1. Agar result mein actual info hai (price, weather, title, etc.) -> wahi batao. "Boss, <info> mil gaya."
2. Agar result mein saaf likha hai task fail hua -> "Boss, nahi mil paya — <reason>."
3. KABHI apne se koi number, price, ya fact MAT banao.
4. "Boss" se shuru karo.

Sirf summary likho, kuch aur nahi."""

    hinglish, _ = _gemini_call(summary_prompt)
    if hinglish:
        return hinglish
    return final_answer[:300]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python browser_agent.py 'youtube pe kesariya bajao'")
    else:
        print(browse({"task": " ".join(sys.argv[1:])}))
