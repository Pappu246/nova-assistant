"""
NOVA Real-Time Brain - streaming thinking.
Uses think.py for decisions, streams text replies.
"""
import os
import json
import re
import time

try:
    from groq import Groq
    _GROQ = True
except Exception:
    _GROQ = False

import policy
from tools import TOOLS
from think import TOOL_SPECS, SYSTEM_PROMPT_TEMPLATE, _build_tool_list, _extract_json


GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"


def stream_reply(user_text, history=None):
    """
    Streaming thinking + reply.
    Yields: ('token', text) | ('done', full) | ('error', msg)
    """
    if history is None:
        history = []

    # Pending confirmation
    pending = policy.get_pending()
    if pending:
        user_low = user_text.lower()
        same_command = False

        if pending["tool"] == "open_app":
            app = str(pending["args"].get("app_name", "")).lower()
            if app and app in user_low:
                same_command = True
        elif pending["tool"] == "vision_click":
            if "click" in user_low:
                same_command = True

        if policy.is_yes(user_text) or same_command:
            policy.clear_pending()
            tool_name = pending["tool"]
            args = pending["args"]
            try:
                result = TOOLS[tool_name](args)
                yield ("token", str(result))
                yield ("done", str(result))
            except Exception as e:
                yield ("error", "Tool fail: " + str(e)[:80])
            return

        if policy.is_no(user_text):
            policy.clear_pending()
            msg = "Theek hai Boss, cancel kiya."
            yield ("token", msg)
            yield ("done", msg)
            return

        policy.clear_pending()

    if not _GROQ:
        yield ("error", "Groq not available")
        return

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        yield ("error", "GROQ_API_KEY missing")
        return

    tool_list = _build_tool_list()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{tool_list}", tool_list)

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_text})

    client = Groq(api_key=key)

    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                stream=True,
                response_format={"type": "json_object"},
                timeout=20,
            )

            buffer = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    buffer += delta

            # Parse final JSON
            decision = _extract_json(buffer.strip())

            if decision is None:
                # No JSON - treat buffer as plain reply
                reply = buffer.strip()[:400]
                for i in range(0, len(reply), 8):
                    yield ("token", reply[i:i+8])
                yield ("done", reply)
                return

            mode = decision.get("mode", "chat")

            # ---- CHAT ----
            if mode == "chat":
                reply = decision.get("reply", "").strip()
                if not reply:
                    reply = "Samajh nahi aaya."
                for i in range(0, len(reply), 8):
                    yield ("token", reply[i:i+8])
                yield ("done", reply)
                return

            # ---- AGENT ----
            if mode == "agent":
                goal = decision.get("goal", user_text)
                yield ("token", "Ek multi-step plan bana raha hoon Boss...")
                try:
                    import agent_loop
                    result = agent_loop.run_task(goal)
                    # Stream summary
                    for i in range(0, len(result), 8):
                        yield ("token", result[i:i+8])
                    yield ("done", result)
                except Exception as e:
                    yield ("error", "Agent fail: " + str(e)[:80])
                return

            # ---- TOOL ----
            if mode == "tool":
                tool_name = decision.get("tool", "")
                args = decision.get("args", {}) or {}

                if tool_name not in TOOLS:
                    reply = "Boss, tool nahi mila."
                    yield ("token", reply)
                    yield ("done", reply)
                    return

                if policy.is_blocked(tool_name, args):
                    reply = "Boss, ye blocked hai."
                    yield ("token", reply)
                    yield ("done", reply)
                    return

                if policy.requires_confirmation(tool_name, args):
                    policy.set_pending(tool_name, args)
                    msg = policy.make_confirmation_message(tool_name, args) + " Haan ya nahi bolo."
                    yield ("token", msg)
                    yield ("done", msg)
                    return

                try:
                    result = str(TOOLS[tool_name](args))
                    for i in range(0, len(result), 8):
                        yield ("token", result[i:i+8])
                    yield ("done", result)
                except Exception as e:
                    yield ("error", "Tool " + tool_name + " fail: " + str(e)[:80])
                return

            # Fallback
            reply = decision.get("reply", "Samajh nahi aaya.")
            yield ("token", reply)
            yield ("done", reply)
            return

        except Exception as e:
            print("[rt_brain] " + model + " fail: " + str(e)[:100])
            continue

    yield ("error", "All LLM models failed")


if __name__ == "__main__":
    print("=" * 55)
    print("  rt_brain.py TEST (thinking mode)")
    print("=" * 55)

    tests = [
        "time kya hai",
        "kya kar rahe ho",
        "chrome kholo",
        "java kya hai",
    ]

    for t in tests:
        print("\n>>> " + t)
        policy.clear_pending()  # reset between tests
        full = ""
        t0 = time.time()
        first = None
        for event in stream_reply(t, history=[]):
            if event[0] == "token":
                if first is None:
                    first = time.time() - t0
                full += event[1]
            elif event[0] == "error":
                print("  [error] " + event[1])
            elif event[0] == "done":
                print("  " + full[:100])
                print("  first=" + str(round(first or 0, 2)) + "s, total=" + str(round(time.time()-t0, 2)) + "s")
