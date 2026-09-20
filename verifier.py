"""
NOVA Verifier - verify if a step succeeded based on result/observation.
"""
import os


# Heuristic keywords per tool
_SUCCESS_HINTS = {
    "open_app": ["khol", "open", "khul", "launch", "start"],
    "get_time": ["time", ":", "baje"],
    "get_weather": ["degree", "temperature", "temp", "celsius"],
    "play_youtube": ["youtube", "baja", "search", "play", "video"],
    "browse": ["success", "playing", "opened", "complete", "khul",
               "search", "youtube", "google", "play", "video",
               "kar liya", "kar diya", "baja diya", "search kar",
               "successfully", "now open", "now playing"],
    "take_screenshot": ["screenshot", "le liya", "capture"],
    "volume_up": ["volume", "badha", "increase"],
    "volume_down": ["volume", "kam", "decrease"],
    "volume_mute": ["mute", "band"],
    "remember": ["yaad", "save", "rakh"],
    "recall": [],  # Always succeeds if it returns something
    "note": ["note", "save"],
    "list_notes": ["note"],
    "set_reminder": ["reminder", "yaad dila", "set"],
    "list_reminders": ["reminder"],
    "agent_run": ["complete", "success", "done", "ok"],
}

_FAILURE_HINTS = [
    "fail", "error", "nahi mila", "not found", "exception",
    "nahi hua", "nahi khul", "could not", "cannot",
]


def verify(step, result):
    """Return (success: bool, reason: str)."""
    if result is None:
        return False, "Koi result nahi aaya"

    result_str = str(result).strip().lower()

    if not result_str:
        return False, "Result khaali hai"

    # Hard failure hints
    for hint in _FAILURE_HINTS:
        if hint in result_str:
            return False, "Result mein failure mila: '" + hint + "'"

    # Tool-specific success hints
    tool = step.get("tool", "")
    hints = _SUCCESS_HINTS.get(tool, [])

    # Special: browse with "successfully" in result - browser-use reports success
    if tool == "browse" and "successfully" in result_str:
        return True, "Browser-use reported success"

    if not hints:
        # Unknown tool - assume success if no failure
        return True, "Result mila"

    for hint in hints:
        if hint in result_str:
            return True, "Success hint mila: '" + hint + "'"

    # Strict mode: require success hint
    return False, "Koi success hint nahi mila (result: " + result_str[:60] + ")"


if __name__ == "__main__":
    # Tests
    tests = [
        ({"tool": "open_app"}, "chrome khol raha hoon", True),
        ({"tool": "open_app"}, "nahi mila", False),
        ({"tool": "get_time"}, "Abhi time hai 5:00 PM", True),
        ({"tool": "get_time"}, "fail hua", False),
        ({"tool": "unknown"}, "kuch bhi", True),
    ]
    for step, result, expected in tests:
        ok, reason = verify(step, result)
        status = "PASS" if ok == expected else "FAIL"
        print(f"  {status}  tool={step['tool']:15}  ok={ok}  reason={reason[:40]}")
    print()
    print("Verifier tests done")
