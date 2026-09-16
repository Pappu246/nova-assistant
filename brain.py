"""
NOVA ka "dimaag" — Ollama (local, free LLM) ko sawal bhejta hai aur
decide karwata hai ki normal jawab dena hai ya koi tool (function) use
karna hai.

Setup (ek baar karna hai):
    1. https://ollama.com se Ollama install karo
    2. Terminal mein: ollama pull llama3.1
    3. pip install ollama
"""

import json
import ollama
from tools import TOOLS

MODEL_NAME = "llama3.1"

SYSTEM_PROMPT = """Tum NOVA ho, ek helpful voice/text assistant, jaise Iron Man ka Jarvis.

Tumhare paas yeh tools available hain:
- get_time: abhi ka time batata hai. Args: koi nahi.
- get_weather: kisi city ka weather batata hai. Args: {"city": "<city_name>"}
- open_app: koi application/program kholta hai. Args: {"app_name": "<app_name>"}

Jab user ka sawal in tools se solve ho sakta hai, sirf yeh JSON return karo
(kuch aur text nahi, sirf JSON):
{"tool": "<tool_name>", "args": {...}}

Agar tool ki zaroorat nahi hai (normal baat-cheet, sawal-jawab), to sirf
normal Hindi/Hinglish mein reply do, JSON mat do.
"""


def ask_nova(user_message, history=None):
    """
    user_message: user ne kya bola
    history: pichli conversation (list of {"role":..., "content":...})
    Return: NOVA ka final jawab (string)
    """
    if history is None:
        history = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = ollama.chat(model=MODEL_NAME, messages=messages)
    reply = response["message"]["content"].strip()

    # Check karo ki LLM ne tool call maanga hai ya normal reply diya hai
    tool_call = _try_parse_tool_call(reply)

    if tool_call:
        tool_name = tool_call.get("tool")
        args = tool_call.get("args", {})

        if tool_name in TOOLS:
            result = TOOLS[tool_name](args)
            return result
        else:
            return f"Mujhe '{tool_name}' naam ka tool nahi pata."

    # Tool call nahi tha — seedha LLM ka reply hi final jawab hai
    return reply


def _try_parse_tool_call(text):
    """Agar LLM ka reply valid tool-call JSON hai to dict return karo, warna None."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "tool" in parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None
