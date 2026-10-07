"""
WhatsApp CALL feature tests (voice + video) - comms_agent.whatsapp_call.
Poora flow mock karke test hota hai (koi real WhatsApp/pyautogui nahi chalta):
  a) contact naam se resolve + chat search flow (search -> type naam -> enter)
  b) pywinauto/ui_agent se precise call button click (pehla try)
  c) fail hone pe vision_click fallback
  d) video: true se video call button
  e) policy ASK (galti se call na lage) + agent-mode safeguard
  f) think/planner/verifier/rt_brain wiring ("X ko call karo" -> tool chale)
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_loop
import app_control
import comms_agent
import planner
import policy
import rt_brain
import think
import tools
import verifier


# ================= FAKE AUTOMATION ENV =================

class _FakePG:
    def __init__(self, log):
        self.log = log
        self.PAUSE = 0.1
        self.FAILSAFE = True

    def hotkey(self, *keys):
        self.log.append(("hotkey", tuple(keys)))

    def press(self, key):
        self.log.append(("press", key))

    def click(self, x=None, y=None):
        self.log.append(("click", x, y))


class _FakeWindow:
    def __init__(self, log):
        self.log = log
        self.title = "WhatsApp"
        self.left = 0
        self.top = 0
        self.visible = True

    def activate(self):
        self.log.append(("activate", self.title))

    def minimize(self):
        pass

    def maximize(self):
        pass


class _FakeGW:
    def __init__(self, log):
        self.log = log

    def getWindowsWithTitle(self, title):
        return [_FakeWindow(self.log)]


class _FakeClipboard:
    def __init__(self, log):
        self.log = log

    def copy(self, text):
        self.log.append(("copy", str(text)))


def _install_fakes(monkeypatch):
    """Fake pyautogui/pygetwindow/pyperclip + no-sleep. Returns shared log."""
    log = []
    pg = _FakePG(log)
    monkeypatch.setitem(sys.modules, "pyautogui", pg)
    monkeypatch.setitem(sys.modules, "pygetwindow", _FakeGW(log))
    monkeypatch.setitem(sys.modules, "pyperclip", _FakeClipboard(log))
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    monkeypatch.setattr(comms_agent, "_wa_desktop_installed", lambda: True)
    monkeypatch.setattr(comms_agent, "WA_CALL_STATE_WAIT_SEC", 0)
    monkeypatch.setattr(comms_agent.os, "system", lambda *_: 0)
    return log


def _index_of(log, pred):
    for i, entry in enumerate(log):
        if pred(entry):
            return i
    return -1


# ================= a) CHAT OPEN FLOW (search -> naam -> enter) =================

def test_open_chat_search_flow(monkeypatch):
    """_wa_open_chat_and_run: esc -> ctrl+f -> naam paste -> enter (chat khul jati hai)."""
    log = _install_fakes(monkeypatch)
    ok, note = comms_agent._wa_open_chat_and_run("Pinkesh")
    assert ok is True and note == "desktop"
    assert ("hotkey", ("ctrl", "f")) in log
    assert ("copy", "Pinkesh") in log
    idx_paste = log.index(("copy", "Pinkesh"))
    idx_v = log.index(("hotkey", ("ctrl", "v")))
    idx_enter = log.index(("press", "enter"))
    assert idx_paste < idx_v < idx_enter, "search flow order galat: " + str(log)


def test_send_by_name_regression(monkeypatch):
    """PR #3 ka send flow toota nahi: chat khulne ke BAAD message paste + enter."""
    log = _install_fakes(monkeypatch)
    ok, note = comms_agent._wa_send_by_name("Pinkesh", "hello")
    assert ok is True and note == "desktop"
    idx_enter_chat = log.index(("press", "enter"))
    idx_msg = _index_of(log, lambda e: e == ("copy", "hello"))
    assert idx_msg > idx_enter_chat, "message chat khulne se pehle paste ho gaya: " + str(log)
    assert log[-1] == ("press", "enter"), "send ke liye final enter missing: " + str(log)


# ================= b) + c) CALL BUTTON: pywinauto pehle, vision fallback ======

def test_voice_call_full_flow_pywinauto_first(monkeypatch):
    log = _install_fakes(monkeypatch)
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window",
                        lambda: log.append(("focus", "WhatsApp")))
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: log.append(("ui_click", video)) or "Clicked: Voice call")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: log.append(("vision_click", video)) or "vision_click (10,20)")

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert "voice call" in r.lower() and "laga diya" in r, r

    # chat search pehle, call button baad me
    idx_enter = log.index(("press", "enter"))
    idx_focus = log.index(("focus", "WhatsApp"))
    idx_ui = log.index(("ui_click", False))
    assert idx_enter < idx_focus < idx_ui, "order galat: " + str(log)
    # pywinauto chala to vision fallback NAHI chalna chahiye
    assert ("vision_click", False) not in log
    # video flag voice call me False
    assert ("ui_click", False) in log


def test_call_falls_back_to_vision_click(monkeypatch):
    log = _install_fakes(monkeypatch)
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: log.append(("focus", "WhatsApp")))
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: log.append(("ui_click", video)) or None)
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: log.append(("vision_click", video)) or "vision_click (500,40)")

    r = str(comms_agent.whatsapp_call({"contact": "Ravi"}))
    assert "laga diya" in r, r
    assert ("ui_click", False) in log and ("vision_click", False) in log
    assert log.index(("ui_click", False)) < log.index(("vision_click", False))


def test_call_fails_when_both_clicks_fail(monkeypatch):
    log = _install_fakes(monkeypatch)
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui", lambda video=False: None)
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision", lambda video=False: None)

    r = str(comms_agent.whatsapp_call({"contact": "Ravi"}))
    assert "fail" in r.lower(), r
    ok, reason = verifier.verify({"tool": "whatsapp_call"}, r)
    assert not ok, "Dono click fail hone pe verifier ko failure dena chahiye: " + reason


def test_call_fails_when_whatsapp_window_missing(monkeypatch):
    _install_fakes(monkeypatch)
    monkeypatch.setattr(comms_agent, "_wa_open_chat_and_run",
                        lambda *a, **kw: (False, "WhatsApp window khula nahi (app install / QR login check karo)"))
    r = str(comms_agent.whatsapp_call({"contact": "Ravi"}))
    assert "nahi laga paya" in r and "fail" in r.lower(), r


# ================= d) VIDEO CALL =================

def test_video_flag_parsing():
    assert comms_agent._wa_call_wants_video({}) is False
    assert comms_agent._wa_call_wants_video({"video": True}) is True
    assert comms_agent._wa_call_wants_video({"video": "true"}) is True
    assert comms_agent._wa_call_wants_video({"video": "video"}) is True
    assert comms_agent._wa_call_wants_video({"video": "false"}) is False
    assert comms_agent._wa_call_wants_video({"video_call": "haan"}) is True


def test_video_call_flow(monkeypatch):
    log = _install_fakes(monkeypatch)
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: log.append(("ui_click", video)) or "Clicked: Video call")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: (_ for _ in ()).throw(AssertionError("fallback nahi chahiye")))

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh", "video": True}))
    assert "video call" in r.lower() and "laga diya" in r, r
    assert ("ui_click", True) in log, "video=True se video call button try hona chahiye: " + str(log)


def test_call_without_contact_asks():
    r = str(comms_agent.whatsapp_call({}))
    assert "kisko" in r.lower() or "contact" in r.lower(), r


def test_contact_naam_se_resolve_hota_hai(monkeypatch):
    """contacts.json se naam resolve + chat search naam se hi hota hai."""
    called = {}
    monkeypatch.setattr(comms_agent, "_resolve_contact", lambda n: ("9876543210", ""))
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui", lambda video=False: "Clicked: Voice call")
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")

    def fake_open(name, after_open=None, wait_load=12):
        called["name"] = name
        return after_open(None, None, "desktop")

    monkeypatch.setattr(comms_agent, "_wa_open_chat_and_run", fake_open)
    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert called["name"] == "Pinkesh"
    assert "Pinkesh" in r and "laga diya" in r


def test_verifier_hints_for_call():
    ok, _ = verifier.verify({"tool": "whatsapp_call"},
                            "WhatsApp me 'Pinkesh' ko voice call laga diya (desktop mode).")
    assert ok
    bad, _ = verifier.verify({"tool": "whatsapp_call"},
                             "'Pinkesh' ko voice call nahi laga paya - fail (test)")
    assert not bad


# ================= e) POLICY: ASK + AGENT SAFEGUARD =================

def test_policy_call_is_ask_not_safe():
    assert policy.classify("whatsapp_call") == "ask"
    assert policy.requires_confirmation("whatsapp_call", {"contact": "Pinkesh"}) is True
    # message bhejna safe hi rahe (PR #3 behaviour)
    assert policy.classify("whatsapp_send") == "safe"


def test_confirmation_message_mentions_contact_and_kind():
    m = policy.make_confirmation_message("whatsapp_call", {"contact": "Pinkesh"})
    assert "Pinkesh" in m and "voice call" in m.lower()
    m2 = policy.make_confirmation_message("whatsapp_call", {"contact": "Ravi", "video": True})
    assert "Ravi" in m2 and "video call" in m2.lower()


def test_agent_mode_does_not_auto_call(monkeypatch):
    """CALL SAFEGUARD: agent mode me whatsapp_call auto-approve NAHI hoga."""
    executed = []
    monkeypatch.setitem(tools.TOOLS, "whatsapp_call",
                        lambda a: executed.append(a) or "call laga diya")
    monkeypatch.setattr(planner, "create_plan", lambda goal, context=None: [
        {"step": 1, "tool": "whatsapp_call", "args": {"contact": "Pinkesh"},
         "description": "call", "status": "pending"},
    ])
    agent_loop.clear_task_history()
    r = str(agent_loop.run_task("Pinkesh ko call karo", force=True))
    assert not executed, "Agent mode me call execute nahi honi chahiye!"
    assert "confirmation" in r.lower() and "haan" in r.lower(), r


# ================= f) PLANNER + THINK WIRING =================

def test_think_and_tools_wired():
    assert "whatsapp_call" in tools.TOOLS
    assert "whatsapp_call" in think.TOOL_SPECS
    tl = think._build_tool_list()
    assert "whatsapp_call" in tl, "LLM tool list me whatsapp_call missing"
    assert "video" in think.TOOL_SPECS["whatsapp_call"].lower()


def test_think_prompt_has_call_example():
    assert 'whatsapp_call' in think.SYSTEM_PROMPT_TEMPLATE
    assert 'ko call karo' in think.SYSTEM_PROMPT_TEMPLATE
    assert 'video' in think.SYSTEM_PROMPT_TEMPLATE.lower()


def test_rt_brain_prompt_has_call_rules():
    p = rt_brain.CONVERSATIONAL_VOICE_SYSTEM_PROMPT
    assert "whatsapp_call" in p
    assert "video call" in p.lower()


def test_planner_schema_and_prompt():
    assert "whatsapp_call" in planner.TOOL_SCHEMAS
    assert "video" in planner.TOOL_SCHEMAS["whatsapp_call"]["video"].lower()


def test_planner_call_goal_no_enter_step():
    """Call goal me send/enter step append NAHI hona chahiye (message flow se alag)."""
    steps = [
        {"step": 1, "tool": "whatsapp_call", "args": {"contact": "Pinkesh"}, "status": "pending"},
        {"step": 2, "tool": "type_text", "args": {"text": "hi"}, "status": "pending"},
    ]
    out = planner._ensure_send_step("Pinkesh ko call karo", steps)
    assert len(out) == 2 and out[-1]["tool"] == "type_text", "Call goal me enter add ho gaya!"

    out2 = planner._ensure_send_step("Pinkesh ko whatsapp video call karo", list(steps))
    assert len(out2) == 2, "Video call goal me bhi send-step nahi hona chahiye"

    # Message goal pe purana fix as-is chalega (PR #3 preserve)
    msg_steps = [
        {"step": 1, "tool": "type_text", "args": {"text": "hello"}, "status": "pending"},
    ]
    out3 = planner._ensure_send_step("Pinkesh ko message karo hello", msg_steps)
    assert len(out3) == 2 and out3[-1]["tool"] == "press_key"


# ================= g) RT_BRAIN ROUTING ("X ko call karo") =================

class _FakeResp:
    def __init__(self, content):
        msg = type("M", (), {"content": content})()
        self.choices = [type("C", (), {"message": msg})()]


class _FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kw):
        return _FakeResp(self.content)


class _FakeGroq:
    """Groq client jaisa - 'X ko call karo' pe whatsapp_call decision deta hai."""

    def __init__(self, api_key=None, content=None):
        self.chat = type("Chat", (), {
            "completions": _FakeCompletions(
                content or '{"mode": "tool", "tool": "whatsapp_call", "args": {"contact": "Pinkesh"}}')
        })()


def test_rt_brain_call_command_goes_to_confirmation(monkeypatch):
    """'Pinkesh ko call karo' -> whatsapp_call ASK -> pending confirmation."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(rt_brain, "_GROQ", True)
    monkeypatch.setattr(rt_brain, "Groq", _FakeGroq, raising=False)
    policy.clear_pending()

    out = [txt for kind, txt in rt_brain.stream_reply("Pinkesh ko call karo", [])
           if kind in ("token", "done")]

    pending = policy.get_pending()
    assert pending is not None and pending["tool"] == "whatsapp_call", str(pending)
    assert pending["args"].get("contact") == "Pinkesh"
    assert out and "Pinkesh" in out[-1] and "call" in out[-1].lower(), str(out)
    policy.clear_pending()


def test_rt_brain_haan_pe_call_tool_chalta_hai(monkeypatch):
    """Pending call ke baad 'haan' bolo -> whatsapp_call execute."""
    executed = []
    monkeypatch.setitem(tools.TOOLS, "whatsapp_call",
                        lambda a: executed.append(dict(a)) or "WhatsApp me 'Pinkesh' ko voice call laga diya")
    policy.clear_pending()
    policy.set_pending("whatsapp_call", {"contact": "Pinkesh", "video": False})

    out = [txt for kind, txt in rt_brain.stream_reply("haan", []) if kind in ("token", "done")]

    assert executed == [{"contact": "Pinkesh", "video": False}]
    assert out and "call laga diya" in out[-1], str(out)
    assert policy.get_pending() is None


def test_rt_brain_same_call_command_repeats_call(monkeypatch):
    """Pending ke waqt wahi 'X ko call karo' dobara -> bina 'haan' bhi chale."""
    executed = []
    monkeypatch.setitem(tools.TOOLS, "whatsapp_call",
                        lambda a: executed.append(dict(a)) or "WhatsApp me 'Ravi' ko video call laga diya")
    policy.clear_pending()
    policy.set_pending("whatsapp_call", {"contact": "Ravi", "video": True})

    list(rt_brain.stream_reply("Ravi ko video call karo", []))
    assert executed == [{"contact": "Ravi", "video": True}]
    assert policy.get_pending() is None


def test_rt_brain_nahi_pe_call_cancel(monkeypatch):
    executed = []
    monkeypatch.setitem(tools.TOOLS, "whatsapp_call", lambda a: executed.append(a) or "call laga diya")
    policy.clear_pending()
    policy.set_pending("whatsapp_call", {"contact": "Pinkesh", "video": False})

    out = [txt for kind, txt in rt_brain.stream_reply("nahi", []) if kind in ("token", "done")]
    assert not executed
    assert out and "cancel" in out[-1].lower(), str(out)
    assert policy.get_pending() is None
