"""
NOVA brain - thin wrapper over think.py (no rules, pure thinking).
"""
import policy
try:
    from synthesis import synthesize as _synthesize
except Exception:
    def _synthesize(q, r): return str(r)

from think import think
from tools import TOOLS


def ask_nova(user_message, history=None):
    """Main entry - think + execute."""
    if history is None:
        history = []

    # Pending confirmation check
    pending = policy.get_pending()
    if pending:
        user_low = user_message.lower()
        same_command = False

        if pending["tool"] == "open_app":
            app = str(pending["args"].get("app_name", "")).lower()
            if app and app in user_low:
                same_command = True
        elif pending["tool"] == "vision_click":
            if "click" in user_low:
                same_command = True

        if policy.is_yes(user_message) or same_command:
            policy.clear_pending()
            tool_name = pending["tool"]
            args = pending["args"]
            try:
                result = TOOLS[tool_name](args)
                return str(result)
            except Exception as e:
                return "Tool fail: " + str(e)[:100]

        if policy.is_no(user_message):
            policy.clear_pending()
            return "Theek hai Boss, cancel kiya."

        policy.clear_pending()

    # Think
    decision = think(user_message, history=history)
    mode = decision.get("mode", "chat")

    # Chat
    if mode == "chat":
        return decision.get("reply", "Samajh nahi aaya.")

    # Error
    if mode == "error":
        return decision.get("reply", "Brain fail.")

    # Agent - multi-step
    if mode == "agent":
        goal = decision.get("goal", user_message)
        try:
            import agent_loop
            return agent_loop.run_task(goal)
        except Exception as e:
            return "Agent fail: " + str(e)[:100]

    # Tool
    if mode == "tool":
        tool_name = decision.get("tool", "")
        args = decision.get("args", {}) or {}

        if tool_name not in TOOLS:
            return "Boss, tool nahi mila: " + str(tool_name)

        if policy.is_blocked(tool_name, args):
            return "Boss, ye blocked hai."

        if policy.requires_confirmation(tool_name, args):
            policy.set_pending(tool_name, args)
            msg = policy.make_confirmation_message(tool_name, args)
            return msg + " Haan ya nahi bolo."

        try:
            result = str(TOOLS[tool_name](args))
            # Synthesize live data results
            LIVE_TOOLS = {"live_data", "live_news", "live_crypto", "live_stock"}
            if tool_name in LIVE_TOOLS:
                result = _synthesize(user_message, result)
            return result
        except Exception as e:
            return "Tool " + tool_name + " fail: " + str(e)[:100]

    return "Samajh nahi aaya."


def _fix_gender(text):
    """Kept for backward compatibility."""
    if not text:
        return text
    import re
    fixes = [
        (r"\bkar rahi hoon\b", "kar raha hoon"),
        (r"\bbol rahi hoon\b", "bol raha hoon"),
        (r"\bsun rahi hoon\b", "sun raha hoon"),
        (r"\bsoch rahi\b", "soch raha"),
        (r"\bbaithi hoon\b", "baitha hoon"),
        (r"\bgayi\b", "gaya"),
        (r"\brahi\b", "raha"),
        (r"\bthi\b", "tha"),
    ]
    t = text
    for p, r in fixes:
        t = re.sub(p, r, t, flags=re.IGNORECASE)
    return t


if __name__ == "__main__":
    tests = [
        "time kya hai",
        "kya kar rahe ho",
        "mera naam Pappu hai",
        "mera naam kya hai",
    ]
    for t in tests:
        print("\n>>> " + t)
        print("NOVA: " + ask_nova(t, history=[]))
