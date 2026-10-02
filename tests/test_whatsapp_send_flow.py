"""
WhatsApp message SEND flow tests (Problem 3) - planner.py + agent_loop.py
  a) planner: message type ke baad final press_key enter (send) ensure
  b) dedup: sirf SUCCEEDED steps skip hon, repeated 'enter' steps chalein
  c) vision click se pehle target app window focus ho
Poora flow simulate hota hai: contact search -> message type -> enter (send).
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_loop
import planner
import tools


def _step(n, tool, args, desc=""):
    return {"step": n, "tool": tool, "args": args, "description": desc, "status": "pending"}


def _whatsapp_plan():
    """Typical 'Rahul ko message karo hello' plan - enter DO baar aata hai."""
    return [
        _step(1, "open_app", {"app_name": "whatsapp"}, "WhatsApp kholo"),
        _step(2, "vision_click", {"target": "search box"}, "Search box pe click"),
        _step(3, "type_text", {"text": "Rahul"}, "Contact search"),
        _step(4, "press_key", {"key": "enter"}, "Contact chat kholo"),
        _step(5, "type_text", {"text": "hello"}, "Message type karo"),
        _step(6, "press_key", {"key": "enter"}, "Message SEND karo"),
    ]


# ================= a) PLANNER: SEND STEP ENSURE =================

def test_planner_appends_missing_send_step():
    """Message type ke baad enter nahi hai -> final send step add ho."""
    steps = _whatsapp_plan()[:5]  # aakhri 'enter' (send) missing
    out = planner._ensure_send_step("Rahul ko message karo hello", steps)
    assert out[-1]["tool"] == "press_key"
    assert "enter" in str(out[-1]["args"].get("key", "")).lower()
    assert len(out) == 6
    assert [s["step"] for s in out] == [1, 2, 3, 4, 5, 6]


def test_planner_keeps_existing_send_step():
    steps = _whatsapp_plan()
    out = planner._ensure_send_step("Rahul ko whatsapp pe hello bhejo", steps)
    assert len(out) == 6  # koi extra step add nahi hua


def test_planner_ignores_non_message_goals():
    steps = [_step(1, "open_app", {"app_name": "notepad"}),
             _step(2, "type_text", {"text": "notes"})]
    out = planner._ensure_send_step("notepad kholo aur kuch type karo", steps)
    assert len(out) == 2, "Non-message goal pe send step add NAHI hona chahiye"


# ================= b) DEDUP: SIRF SUCCEEDED SKIP =================

def test_dedup_allows_repeated_enter_steps():
    """DEDUP FIX: do non-consecutive 'press_key enter' steps dono bachne chahiye."""
    plan = _whatsapp_plan()
    out = agent_loop._deduplicate_plan(plan)
    enters = [s for s in out if s["tool"] == "press_key"]
    assert len(enters) == 2, "Dono enter steps (contact open + send) rehne chahiye"
    assert len(out) == 6


def test_dedup_skips_only_succeeded_steps():
    plan = _whatsapp_plan()
    done = {agent_loop._step_key(plan[0])}  # open_app pehle hi SUCCEED ho chuka
    out = agent_loop._deduplicate_plan(plan, done)
    assert all(s["tool"] != "open_app" for s in out)
    assert len(out) == 5


def test_dedup_does_not_skip_merely_tried_steps():
    """Jo step sirf TRY hua (fail), wo skip NAHI hona chahiye."""
    plan = _whatsapp_plan()
    # koi completed keys nahi (sab sirf try hue the)
    out = agent_loop._deduplicate_plan(plan, set())
    assert len(out) == 6


def test_dedup_removes_consecutive_duplicates():
    plan = [
        _step(1, "press_key", {"key": "enter"}),
        _step(2, "press_key", {"key": "enter"}),  # back-to-back same -> skip
        _step(3, "type_text", {"text": "hi"}),
    ]
    out = agent_loop._deduplicate_plan(plan)
    assert len(out) == 2


# ================= c) + FULL FLOW: run_task simulation =================

@pytest.fixture
def fake_env(monkeypatch):
    """Planner + tools + focus_window ko mock karke poora flow chalao."""
    calls = []

    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: calls.append(("open_app", dict(a))) or "whatsapp khol raha hoon...")
    monkeypatch.setitem(tools.TOOLS, "vision_click",
                        lambda a: calls.append(("vision_click", dict(a))) or "search box pe click kar diya")
    monkeypatch.setitem(tools.TOOLS, "type_text",
                        lambda a: calls.append(("type_text", dict(a))) or "Type kar diya.")
    monkeypatch.setitem(tools.TOOLS, "press_key",
                        lambda a: calls.append(("press_key", dict(a))) or "enter key bheja")

    import app_control
    monkeypatch.setattr(app_control, "focus_window",
                        lambda title: calls.append(("focus_window", title)) or (str(title) + " focus kar diya."))

    monkeypatch.setattr(planner, "create_plan", lambda goal, context=None: _whatsapp_plan())
    monkeypatch.setattr(agent_loop, "MAX_RETRIES_PER_STEP", 0)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)  # verifier LLM fallback off

    agent_loop.clear_task_history()
    return calls


def test_full_whatsapp_send_flow(fake_env):
    """Poora flow: WhatsApp open -> search click -> contact type -> enter ->
    message type -> enter (SEND). Enter DO baar chalna chahiye."""
    calls = fake_env
    result = agent_loop.run_task("Rahul ko whatsapp pe message karo hello", force=True)

    tool_calls = [c for c in calls if c[0] != "focus_window"]
    assert [c[0] for c in tool_calls] == [
        "open_app", "vision_click", "type_text", "press_key", "type_text", "press_key",
    ], "Sare 6 steps (dono enter samet) chalne chahiye the: " + str(tool_calls)

    # Message SEND hua? (aakhri action press_key enter)
    assert tool_calls[-1] == ("press_key", {"key": "enter"})
    assert "task complete" in result.lower()


def test_focus_window_called_before_vision_click(fake_env):
    """FOCUS FIX: vision_click se pehle WhatsApp window focus honi chahiye
    (warna fullscreen fallback terminal pe click karta hai)."""
    calls = fake_env
    agent_loop.run_task("Rahul ko whatsapp pe message karo hello", force=True)

    names = [c[0] for c in calls]
    assert "focus_window" in names, "vision_click se pehle focus_window call hona chahiye"
    focus_idx = names.index("focus_window")
    vc_idx = names.index("vision_click")
    assert focus_idx < vc_idx, "Focus vision_click se PEHLE hona chahiye"
    assert calls[focus_idx][1] == "WhatsApp"
