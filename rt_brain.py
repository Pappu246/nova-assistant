"""
NOVA Real-Time Conversational Brain - Streaming Natural Voice AI.
Low-latency sentence streaming with conversational memory.
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
try:
    from synthesis import synthesize as _synthesize
except Exception:
    def _synthesize(q, r): return str(r)

from tools import TOOLS
from think import _build_tool_list, _extract_json, fit_messages

GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"

CONVERSATIONAL_VOICE_SYSTEM_PROMPT = """You are NOVA — a brilliant, warm, witty, and highly capable AI companion for Boss (Pappu).

*** REAL-TIME VOICE CONVERSATION RULES ***
1. SPEAK LIKE A REAL HUMAN FRIEND:
   - Talk naturally in fluent, lively Hinglish (Hindi + English mix).
   - Use natural conversational expressions: "Arey haan", "Bilkul Boss", "Suno na", "Arey wah", "Achha to yeh baat hai", "Samajh gaya".
   - You are MALE — use "kar raha hoon", "bol raha hoon", "sun raha hoon" (NEVER "rahi").

2. CRISP & ENGAGING (OPTIMIZED FOR VOICE):
   - Keep spoken replies SHORT and punchy (1 to 2 sentences) so the conversation flows seamlessly.
   - Don't give boring long essays or bullet points unless Boss explicitly asks for a detailed breakdown.
   - Ask thoughtful follow-ups or show friendly enthusiasm when appropriate.

3. DESKTOP APPS vs BROWSER:
   - Installed apps (WhatsApp, Telegram, Spotify, Discord, VS Code, Notepad, Calc, VLC) are native desktop apps -> use open_app, NEVER browse.

4. WHATSAPP CALL (VOICE / VIDEO):
   - "call kaato", "kaat do", "cut karo", "call cut" -> tool: whatsapp_call_end, args {}. No confirmation; mode=tool.
   - "X ko call karo", "X ko phone karo", "X se baat karni hai" -> tool: whatsapp_call, args {"contact": "X"} (voice call)
   - "X ko video call karo" -> tool: whatsapp_call, args {"contact": "X", "video": true}
   - Call START karne ke liye HAMESHA whatsapp_call tool (mode=tool) use karo - mode=agent ya whatsapp_send MAT use karo.
   - whatsapp_call se pehle NOVA khud confirmation maangta hai ("X ko call lagana hai?") - yeh normal hai.

5. RESPONSE FORMAT:
   - For CASUAL TALK / ANSWERS / QUESTIONS: Return JSON: {"mode": "chat", "reply": "<short spoken Hinglish reply>"}
   - For PC ACTIONS / TOOLS: Return JSON: {"mode": "tool", "tool": "<tool_name>", "args": {...}}
   - For MULTI-STEP COMPLEX TASKS: Return JSON: {"mode": "agent", "goal": "<the full goal>"}

AVAILABLE TOOLS:
{tool_list}

Respond with a single clean JSON object."""


def _chat_completion_with_json_fallback(client, model, messages,
                                        temperature=0.4, max_tokens=400, timeout=15):
    """
    GROQ 400 FIX (NOVA): openai/gpt-oss-120b kabhi-kabhi response_format
    json_object pe 'Error 400: Failed to generate JSON' deta hai.
    Pehle JSON mode try karo; 400/json fail pe BINA response_format retry.
    (_extract_json plain-text reply se bhi JSON nikal leta hai.)
    """
    try:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            timeout=timeout,
        )
    except Exception as e:
        err_low = str(e).lower()
        if not ("json" in err_low or "400" in err_low or "response_format" in err_low):
            raise
        print("[rt_brain] json mode fail (" + str(e)[:60] + ") - retry WITHOUT response_format")
        return client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )


def _save_mem(user_text, nova_text):
    try:
        import memory
        memory.log_conversation(user_text, nova_text)
    except Exception:
        pass


def stream_reply(user_text, history=None):
    """
    Streaming thinking + reply for real-time voice.
    Yields: ('token', text) | ('done', full) | ('error', msg)
    """
    if history is None:
        history = []

    # Pending confirmation check
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
        elif pending["tool"] == "whatsapp_call":
            # CALL FIX (NOVA): "Pinkesh ko call karo" dobara bolo to pending
            # call turant chale (contact + call/video/phone dono chahiye)
            args = pending["args"]
            contact = str(args.get("contact") or args.get("name") or "").lower()
            if contact and contact in user_low and any(
                    w in user_low for w in ("call", "video", "phone")):
                same_command = True

        # STALE PENDING FIX (NOVA): naya command + 'haan' sath me aaye to
        # purani pending execute mat karo (is_confirmation command detect karta hai)
        if policy.is_confirmation(user_text, pending) or same_command:
            policy.clear_pending()
            tool_name = pending["tool"]
            args = pending["args"]
            try:
                result = str(TOOLS[tool_name](args))
                yield ("token", result)
                yield ("done", result)
            except Exception as e:
                yield ("error", "Tool fail: " + str(e)[:80])
            return

        if policy.is_no(user_text):
            policy.clear_pending()
            msg = "Theek hai Boss, cancel kar diya."
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
    system_prompt = CONVERSATIONAL_VOICE_SYSTEM_PROMPT.replace("{tool_list}", tool_list)

    # Long-term memory injection
    try:
        import memory as _mem
        mem_ctx = _mem.get_memory_context(max_facts=6, max_convos=2)
        if mem_ctx:
            system_prompt += "\n\n[Memory about Boss]:\n" + mem_ctx
        try:
            _mem.auto_extract(user_text)
        except Exception:
            pass
    except Exception:
        pass

    # 413 FIX: request strictly <8000 tokens (system rakho, purane msgs drop)
    messages = fit_messages(system_prompt, history[-8:], user_text)

    client = Groq(api_key=key)

    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        try:
            # GROQ 400 FIX: json_object fail ho to bina response_format retry
            resp = _chat_completion_with_json_fallback(
                client, model, messages,
                temperature=0.4, max_tokens=400, timeout=15,
            )

            raw = resp.choices[0].message.content.strip()
            decision = _extract_json(raw)

            if decision is None:
                reply = raw[:300]
                yield ("token", reply)
                _save_mem(user_text, reply)
                yield ("done", reply)
                return

            mode = decision.get("mode", "chat")

            # ---- CHAT ----
            if mode == "chat":
                reply = decision.get("reply", "").strip()
                if not reply:
                    reply = "Haan Boss, sun raha hoon."
                yield ("token", reply)
                _save_mem(user_text, reply)
                yield ("done", reply)
                return

            # ---- AGENT ----
            if mode == "agent":
                goal = decision.get("goal", user_text)
                yield ("token", "Haan Boss, abhi karta hoon.")
                try:
                    import agent_loop
                    result = agent_loop.run_task(goal)
                    yield ("token", " " + str(result))
                    _save_mem(user_text, result)
                    yield ("done", result)
                except Exception as e:
                    yield ("error", "Agent fail: " + str(e)[:80])
                return

            # ---- TOOL ----
            if mode == "tool":
                tool_name = decision.get("tool", "")
                args = decision.get("args", {}) or {}

                if tool_name not in TOOLS:
                    reply = "Boss, ye tool available nahi hai."
                    yield ("token", reply)
                    yield ("done", reply)
                    return

                if policy.is_blocked(tool_name, args):
                    reply = "Boss, ye action allowed nahi hai."
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
                    LIVE_TOOLS = {"live_data", "live_news", "live_crypto", "live_stock"}
                    if tool_name in LIVE_TOOLS:
                        result = _synthesize(user_text, result)
                    yield ("token", result)
                    _save_mem(user_text, result)
                    yield ("done", result)
                except Exception as e:
                    yield ("error", "Tool " + tool_name + " fail: " + str(e)[:80])
                return

            # Fallback
            reply = decision.get("reply", "Haan Boss, bolo?")
            yield ("token", reply)
            _save_mem(user_text, reply)
            yield ("done", reply)
            return

        except Exception as e:
            print("[rt_brain] " + model + " fail: " + str(e)[:100])
            continue

    yield ("error", "LLM response fail")


if __name__ == "__main__":
    print("[rt_brain] ready")
