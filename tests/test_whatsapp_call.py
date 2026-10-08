"""
WhatsApp CALL feature tests (voice + video) - comms_agent.whatsapp_call.

CALL FIX (NOVA) ke baad yeh test karta hai:
  a) chat open flow (search -> naam -> enter) + send regression (PR #3)
  b) STRICT UIA filter - chat ka "Voice call" TEXT ignore, header Button pick,
     "Missed voice call" block (fuzzy match hata diya gaya)
  c) click chain: UIA -> verify -> vision -> verify -> coords -> verify
  d) VERIFY: OCR chala par call screen nahi -> HONEST fail (jhoothi success nahi)
     OCR hi unavailable -> alag honest message
  e) already-active call pe double-dial skip, video flag, probe, coords fallback
  f) policy ASK + agent-mode safeguard + think/planner/verifier/rt_brain wiring

Poora flow mock karke test hota hai - koi real WhatsApp/pyautogui/OCR nahi chalta.
"""
import subprocess
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_loop
import comms_agent
import planner
import policy
import rt_brain
import think
import tools
import verifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
        self._hWnd = 197
        self.left = 0
        self.top = 0
        self.width = 1000
        self.height = 800
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

    def getActiveWindow(self):
        return _FakeWindow(self.log)


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
    monkeypatch.setattr(comms_agent, "_wa_foreground_info", lambda: (197, "WhatsApp"))
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


# ================= FAKE UIA TREE =================

class _FakeRect:
    def __init__(self, left, top, right, bottom):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


class _FakeElInfo:
    def __init__(self, name, control_type):
        self.name = name
        self.control_type = control_type
        self.class_name = ""


class _FakeEl:
    """pywinauto UIAWrapper jaisa: element_info + rectangle() + invoke()/click_input()."""

    def __init__(self, el_id, name, control_type="Text", rect=(0, 0, 10, 10),
                 log=None, can_invoke=True):
        self.id = el_id
        self.element_info = _FakeElInfo(name, control_type)
        self._rect = _FakeRect(*rect)
        self.log = log if log is not None else []
        self.can_invoke = can_invoke

    def rectangle(self):
        return self._rect

    def invoke(self):
        if not self.can_invoke:
            raise RuntimeError("InvokePattern not supported")
        self.log.append(("invoke", self.id))

    def click_input(self):
        self.log.append(("click_input", self.id))


class _FakeUIAWindow:
    """WhatsApp window: 1000x800. Header = top 22% (176px) aur left >= 25% (250px)."""

    def __init__(self, descendants, rect=(0, 0, 1000, 800)):
        self._desc = descendants
        self.element_info = _FakeElInfo("WhatsApp", "Window")
        self.handle = 197
        self._rect = _FakeRect(*rect)

    def window_text(self):
        return "WhatsApp"

    def descendants(self):
        return self._desc

    def rectangle(self):
        return self._rect


def _install_uia(monkeypatch, descendants, is_win=True):
    """comms_agent._wa_uia_window ko fake WhatsApp window dedo."""
    win = _FakeUIAWindow(descendants)
    monkeypatch.setattr(comms_agent, "_wa_uia_window", lambda: win)
    monkeypatch.setattr(comms_agent, "_wa_foreground_info", lambda: (197, "WhatsApp"))
    for el in descendants:
        el.top_level_parent = lambda: win
    try:
        import ui_agent
        monkeypatch.setattr(ui_agent, "IS_WIN", is_win, raising=False)
    except Exception:
        pass
    return win


# WhatsApp Desktop jaisa realistic tree: chat ke call-log messages + header buttons
def _realistic_tree(log):
    return [
        # chat list / message bubbles - inpe click NAHI hona chahiye
        _FakeEl("chat_text_voice", "Voice call", "Text", (100, 400, 200, 420), log),
        _FakeEl("chat_text_missed", "Missed voice call", "Text", (100, 440, 240, 460), log),
        _FakeEl("chat_text_ended", "Call ended", "Text", (100, 480, 220, 500), log),
        _FakeEl("chat_text_noans", "No answer", "Text", (100, 520, 200, 540), log),
        _FakeEl("chat_text_video", "Video call", "Text", (100, 560, 200, 580), log),
        # header buttons (top 22%, right side) - asli call button
        _FakeEl("header_voice_btn", "Voice call", "Button", (900, 60, 940, 100), log),
        _FakeEl("header_video_btn", "Video call", "Button", (850, 60, 890, 100), log),
    ]


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


def test_open_chat_handles_2tuple_and_3tuple(monkeypatch):
    """after_open 2-tuple (send) aur 3-tuple (call) dono pass-through hone chahiye."""
    _install_fakes(monkeypatch)
    r2 = comms_agent._wa_open_chat_and_run("A", after_open=lambda pg, cb, m: (True, m))
    assert len(r2) == 2 and r2 == (True, "desktop"), r2
    r3 = comms_agent._wa_open_chat_and_run(
        "B", after_open=lambda pg, cb, m: (True, "note", "detected"))
    assert len(r3) == 3 and r3 == (True, "note", "detected"), r3
    # Garbage return pe bhi crash na ho
    r1 = comms_agent._wa_open_chat_and_run("C", after_open=lambda pg, cb, m: "weird")
    assert len(r1) == 3 and r1[0] is True, r1


def test_unpack_result_handles_both_shapes():
    assert comms_agent._wa_unpack_result((False, "note")) == (False, "note", "unknown")
    assert comms_agent._wa_unpack_result((True, "n", "detected")) == (True, "n", "detected")
    assert comms_agent._wa_unpack_result("junk")[0] is False


# ================= b) STRICT UIA FILTER (fuzzy HATA diya) =================

def test_strict_filter_picks_header_button_not_chat_text(monkeypatch):
    """Chat ka 'Voice call' TEXT ignore, header ka Button pick ho."""
    log = []
    _install_uia(monkeypatch, _realistic_tree(log))
    cands = comms_agent._wa_uia_call_candidates(video=False)
    assert cands, "koi candidate nahi mila"
    assert cands[0][3].id == "header_voice_btn", [c[1:3] for c in cands]
    assert cands[0][2] == "button"
    # chat text candidate list me ho sakta hai, par top pe NAHI
    ids = [c[3].id for c in cands]
    assert ids.index("header_voice_btn") < ids.index("chat_text_voice"), ids


def test_strict_filter_blocks_call_log_words(monkeypatch):
    """'Missed voice call' / 'No answer' jaise call-log naam block hone chahiye."""
    _install_uia(monkeypatch, _realistic_tree([]))
    cands = comms_agent._wa_uia_call_candidates(video=False)
    ids = [c[3].id for c in cands]
    assert "chat_text_missed" not in ids, ids
    assert "chat_text_noans" not in ids, ids
    assert "chat_text_ended" not in ids, ids


def test_strict_match_is_exact_not_fuzzy(monkeypatch):
    """Naam me extra word ho to exact match fail - fuzzy substring nahi chalega."""
    els = [
        _FakeEl("weird", "Voice call for Pinkesh", "Button", (900, 60, 940, 100), []),
        _FakeEl("exact", "Voice call", "Button", (900, 120, 940, 160), []),
    ]
    _install_uia(monkeypatch, els)
    cands = comms_agent._wa_uia_call_candidates(video=False)
    ids = [c[3].id for c in cands]
    assert "weird" not in ids, "fuzzy match wapas aa gaya: " + str(ids)
    assert "exact" in ids


def test_video_candidates_only_video_names(monkeypatch):
    """video=True pe voice-only naam candidate nahi banenge."""
    _install_uia(monkeypatch, _realistic_tree([]))
    cands = comms_agent._wa_uia_call_candidates(video=True)
    ids = [c[3].id for c in cands]
    assert ids[0] == "header_video_btn", ids
    assert "header_voice_btn" not in ids, ids


def test_score_formula_header_and_button_bonus(monkeypatch):
    """score = weight*2 + 5 (header region) + 3 (button)."""
    log = []
    els = [
        _FakeEl("chat", "voice call", "Text", (100, 400, 200, 420), log),      # 3*2 = 6
        _FakeEl("btn_low", "voice call", "Button", (100, 400, 200, 420), log),  # 6 + 3 = 9
        _FakeEl("hdr", "voice call", "Button", (900, 60, 940, 100), log),       # 6+5+3 = 14
        _FakeEl("generic", "call", "Button", (900, 60, 940, 100), log),         # 1*2+5+3 = 10
    ]
    _install_uia(monkeypatch, els)
    scores = {c[3].id: c[0] for c in comms_agent._wa_uia_call_candidates(False)}
    assert scores == {"chat": 6, "btn_low": 9, "hdr": 14, "generic": 10}, scores


def test_candidates_dump_prints(monkeypatch, capsys):
    _install_uia(monkeypatch, _realistic_tree([]))
    comms_agent._wa_uia_call_candidates(video=False, dump=True)
    out = capsys.readouterr().out
    assert "strict candidate" in out and "Voice call" in out


def test_no_uia_window_returns_empty(monkeypatch):
    monkeypatch.setattr(comms_agent, "_wa_uia_window", lambda: None)
    assert comms_agent._wa_uia_call_candidates(video=False) == []
    assert comms_agent._wa_click_call_button_ui(False) is None


def test_config_wa_call_names_extends_weights(monkeypatch, tmp_path):
    cfg = tmp_path / "comms_config.json"
    cfg.write_text('{"wa_call_names": ["Start a voice call"]}', encoding="utf-8")
    monkeypatch.setattr(comms_agent, "CONFIG_PATH", str(cfg))
    w = comms_agent._wa_call_name_weights(False)
    assert w.get("start a voice call") == 3
    assert w.get("voice call") == 3, "default naam gayab ho gaya"


# ================= UIA CLICK: invoke pehle, click_input fallback ==============

def test_uia_click_prefers_invoke(monkeypatch):
    log = []
    _install_uia(monkeypatch, _realistic_tree(log))
    cands = comms_agent._wa_uia_call_candidates(False)
    ok, how = comms_agent._wa_uia_click(cands[0][3])
    assert ok is True and how == "invoke", how
    assert log == [("invoke", "header_voice_btn")], log


def test_uia_click_falls_back_to_click_input(monkeypatch):
    log = []
    els = [_FakeEl("noinv", "Voice call", "Button", (900, 60, 940, 100), log,
                   can_invoke=False)]
    _install_uia(monkeypatch, els)
    cands = comms_agent._wa_uia_call_candidates(False)
    ok, how = comms_agent._wa_uia_click(cands[0][3])
    assert ok is True and how == "click_input", how
    assert log == [("click_input", "noinv")], log


def test_uia_click_total_fail_returns_false(monkeypatch):
    el = _FakeEl("dead", "Voice call", "Button", (900, 60, 940, 100), [], can_invoke=False)
    el.click_input = lambda: (_ for _ in ()).throw(RuntimeError("no coords"))
    _install_uia(monkeypatch, [el])
    ok, how = comms_agent._wa_uia_click(el)
    assert ok is False and "fail" in how, how


def test_ui_layer_clicks_top_candidate(monkeypatch):
    """_wa_click_call_button_ui: focus pehle, phir top candidate invoke."""
    log = []
    order = []
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window",
                        lambda: order.append("focus"))
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    _install_uia(monkeypatch, _realistic_tree(log))
    note = comms_agent._wa_click_call_button_ui(False)
    assert note and "header_voice_btn" not in note and "invoke" in note, note
    assert order == ["focus"], order
    assert ("invoke", "header_voice_btn") in log


def test_ui_layer_none_when_not_windows(monkeypatch):
    try:
        import ui_agent
        monkeypatch.setattr(ui_agent, "IS_WIN", False, raising=False)
    except Exception:
        pytest.skip("ui_agent nahi hai")
    assert comms_agent._wa_click_call_button_ui(False) is None


# ================= c) CLICK CHAIN + VERIFY =================

def _stub_verify(monkeypatch, states):
    """_wa_call_state_note ko scripted states dedo (list khatam ho to last repeat)."""
    calls = []
    seq = list(states)

    def _fake(video=False, wait=None):
        calls.append(video)
        return seq.pop(0) if len(seq) > 1 else seq[0]

    monkeypatch.setattr(comms_agent, "_wa_call_state_note", _fake)
    return calls


def _stub_no_active(monkeypatch):
    monkeypatch.setattr(comms_agent, "_wa_call_already_active", lambda video=False: False)


def test_ui_click_verified_first_try_no_fallback(monkeypatch):
    log = _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_DETECTED, "ringing")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: log.append(("focus",)))
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: log.append(("ui", video)) or "uia invoke 'Voice call'")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: (_ for _ in ()).throw(AssertionError("fallback nahi chahiye")))
    monkeypatch.setattr(comms_agent, "_wa_call_fallback_xy",
                        lambda video=False: (_ for _ in ()).throw(AssertionError("coords nahi chahiye")))

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert "laga diya" in r and "Ringing" in r, r
    assert log.index(("press", "enter")) < log.index(("focus",)) < log.index(("ui", False))
    assert "(" not in r and ")" not in r, "spoken reply me parentheses nahi chahiye: " + r


def test_verify_fail_falls_to_vision_then_coords(monkeypatch):
    """UIA click hua par verify fail -> vision -> verify fail -> coords -> verify OK."""
    log = _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [
        (comms_agent.WA_CALL_ABSENT, "no call-screen text"),      # after UIA
        (comms_agent.WA_CALL_ABSENT, "no call-screen text"),      # after vision
        (comms_agent.WA_CALL_DETECTED, "calling"),                # after coords
    ])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: log.append(("ui", video)) or "uia invoke")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: log.append(("vision", video)) or "vision_click (900,60)")
    monkeypatch.setattr(comms_agent, "_wa_call_fallback_xy",
                        lambda video=False: log.append(("coords", video)) or "coords click (910,70)")

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert "laga diya" in r, r
    i_ui = log.index(("ui", False))
    i_vis = log.index(("vision", False))
    i_xy = log.index(("coords", False))
    assert i_ui < i_vis < i_xy, "chain order galat: " + str(log)


def test_vision_used_when_ui_misses(monkeypatch):
    log = _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_DETECTED, "calling")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: log.append(("ui", video)) or None)
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: log.append(("vision", video)) or "vision_click (900,60)")

    r = str(comms_agent.whatsapp_call({"contact": "Ravi"}))
    assert "laga diya" in r, r
    assert log.index(("ui", False)) < log.index(("vision", False))


# ================= d) HONEST FAIL (jhoothi success NAHI) =================

def test_honest_fail_when_verify_absent(monkeypatch):
    """Sab click hue par calling screen nahi aayi -> HONEST fail, success nahi."""
    _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_ABSENT, "no call-screen text")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui", lambda video=False: "uia invoke")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: "vision_click (900,60)")
    monkeypatch.setattr(comms_agent, "_wa_call_fallback_xy", lambda video=False: None)

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert "nahi laga paya" in r and "fail" in r.lower(), r
    assert "calling screen nahi aayi" in r, r
    assert "--call-probe" in r, r
    assert "laga diya" not in r, "jhoothi success bol diya: " + r
    ok, reason = verifier.verify({"tool": "whatsapp_call"}, r)
    assert not ok, "verifier ko failure pakadna chahiye: " + reason


def test_honest_message_when_ocr_unavailable(monkeypatch):
    """OCR hi nahi chala -> 'confirm nahi kar paya' (hard fail nahi, success bhi nahi)."""
    _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_UNKNOWN, "ocr unavailable")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui", lambda video=False: "uia invoke")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision", lambda video=False: None)
    monkeypatch.setattr(comms_agent, "_wa_call_fallback_xy", lambda video=False: None)

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert "confirm nahi kar paya" in r, r
    assert "khud check kar lo" in r, r
    assert "laga diya" not in r, r
    assert "(" not in r and ")" not in r, r


def test_honest_fail_when_no_click_layer_worked(monkeypatch):
    _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_UNKNOWN, "ocr unavailable")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui", lambda video=False: None)
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision", lambda video=False: None)
    monkeypatch.setattr(comms_agent, "_wa_call_fallback_xy", lambda video=False: None)

    r = str(comms_agent.whatsapp_call({"contact": "Ravi"}))
    assert "nahi laga paya" in r and "fail" in r.lower(), r
    assert "click hi nahi hua" in r, r
    ok, _ = verifier.verify({"tool": "whatsapp_call"}, r)
    assert not ok


def test_call_fails_when_whatsapp_window_missing(monkeypatch):
    _install_fakes(monkeypatch)
    monkeypatch.setattr(
        comms_agent, "_wa_open_chat_and_run",
        lambda *a, **kw: (False, "WhatsApp window khula nahi (app install / QR login check karo)"))
    r = str(comms_agent.whatsapp_call({"contact": "Ravi"}))
    assert "nahi laga paya" in r and "fail" in r.lower(), r
    ok, _ = verifier.verify({"tool": "whatsapp_call"}, r)
    assert not ok


def test_click_layer_crash_does_not_break_chain(monkeypatch):
    """Ek layer crash ho to agla layer chale, exception bahar na aaye."""
    _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_DETECTED, "calling")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")

    def _boom(video=False):
        raise RuntimeError("pywinauto crash")

    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui", _boom)
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: "vision_click (900,60)")
    monkeypatch.setattr(comms_agent, "_wa_call_fallback_xy", lambda video=False: None)

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert "laga diya" in r, r


# ================= e) VERIFY / STATE / PROBE / FALLBACK =================

class _FakeVisionControl:
    """vision_control.read_screen jaisa - mode ke hisaab se text deta hai."""

    def __init__(self, active=None, full=None, boom=False, empty=False):
        self.active, self.full, self.boom, self.empty = active, full, boom, empty
        self.modes = []

    def read_screen(self, region_mode="active"):
        self.modes.append(region_mode)
        if self.boom:
            raise RuntimeError("ocr engine missing")
        if self.empty:
            return "(kuch text nahi mila)"
        return self.active if region_mode == "active" else self.full


def test_verify_detected_from_active_ocr(monkeypatch):
    monkeypatch.setattr(comms_agent, "WA_CALL_STATE_WAIT_SEC", 0)
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    fake = _FakeVisionControl(active="Pinkesh\nCalling")
    monkeypatch.setitem(sys.modules, "vision_control", fake)
    state, hint = comms_agent._wa_call_state_note(False, wait=0)
    assert state == "detected" and hint == "calling", (state, hint)
    assert fake.modes == ["active"], "pehle active window OCR chahiye"


def test_verify_detects_end_call_and_order(monkeypatch):
    """'End call' bhi detection hai; hint order spec ke hisaab se pehla match."""
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    monkeypatch.setitem(sys.modules, "vision_control",
                        _FakeVisionControl(active="End call"))
    assert comms_agent._wa_call_state_note(False, wait=0) == ("detected", "end call")
    monkeypatch.setitem(sys.modules, "vision_control",
                        _FakeVisionControl(active="End video call"))
    assert comms_agent._wa_call_state_note(True, wait=0) == ("detected", "end video call")
    monkeypatch.setitem(sys.modules, "vision_control",
                        _FakeVisionControl(active="Reconnecting"))
    assert comms_agent._wa_call_state_note(False, wait=0) == ("detected", "reconnecting")
    assert comms_agent._WA_CALL_SCREEN_HINTS[0] == "end call"


def test_verify_falls_back_to_full_screen(monkeypatch):
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    fake = _FakeVisionControl(active="Pinkesh\nlast seen today", full="Ringing")
    monkeypatch.setitem(sys.modules, "vision_control", fake)
    state, hint = comms_agent._wa_call_state_note(False, wait=0)
    assert state == "detected" and hint == "ringing", (state, hint)
    assert fake.modes == ["active", "full"], fake.modes


def test_verify_ignores_chat_call_log_text(monkeypatch):
    """'Call ended' / 'No answer' chat message me bhi hote hain - detected nahi."""
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    fake = _FakeVisionControl(active="Missed voice call\nCall ended\nNo answer\nPinkesh")
    monkeypatch.setitem(sys.modules, "vision_control", fake)
    state, _ = comms_agent._wa_call_state_note(False, wait=0)
    assert state == "absent", "chat ke call-log text se false positive ho gaya"
    for bad in ("call ended", "no answer"):
        assert bad not in comms_agent._WA_CALL_SCREEN_HINTS


def test_verify_absent_when_no_hint(monkeypatch):
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    fake = _FakeVisionControl(active="Pinkesh\nonline\nType a message")
    monkeypatch.setitem(sys.modules, "vision_control", fake)
    assert comms_agent._wa_call_state_note(False, wait=0)[0] == "absent"


def test_verify_unknown_when_ocr_raises(monkeypatch):
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    monkeypatch.setitem(sys.modules, "vision_control", _FakeVisionControl(boom=True))
    state, hint = comms_agent._wa_call_state_note(False, wait=0)
    assert state == "unknown", (state, hint)


def test_verify_unknown_when_ocr_empty(monkeypatch):
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    monkeypatch.setitem(sys.modules, "vision_control", _FakeVisionControl(empty=True))
    assert comms_agent._wa_call_state_note(False, wait=0)[0] == "unknown"


def test_already_active_skips_double_dial(monkeypatch):
    """Call pehle se chal rahi hai to button dobara nahi dabega."""
    _install_fakes(monkeypatch)
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_call_already_active", lambda video=False: True)
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: (_ for _ in ()).throw(AssertionError("double dial!")))
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_vision",
                        lambda video=False: (_ for _ in ()).throw(AssertionError("double dial!")))
    monkeypatch.setattr(comms_agent, "_wa_call_fallback_xy",
                        lambda video=False: (_ for _ in ()).throw(AssertionError("double dial!")))

    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert "laga diya" in r, r


def test_already_active_true_only_when_detected(monkeypatch):
    monkeypatch.setattr(comms_agent.time, "sleep", lambda *_: None)
    monkeypatch.setattr(comms_agent, "_wa_call_state_note",
                        lambda video=False, wait=None: ("detected", "end call"))
    assert comms_agent._wa_call_already_active(False) is True
    monkeypatch.setattr(comms_agent, "_wa_call_state_note",
                        lambda video=False, wait=None: ("absent", "none"))
    assert comms_agent._wa_call_already_active(False) is False


def test_coords_fallback_disabled_by_default(monkeypatch, tmp_path):
    cfg = tmp_path / "comms_config.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(comms_agent, "CONFIG_PATH", str(cfg))
    log = _install_fakes(monkeypatch)
    assert comms_agent._wa_call_fallback_xy(False) is None
    assert not [e for e in log if e[0] == "click"], "disabled fallback ne click kar diya"


def test_coords_fallback_uses_offsets_when_configured(monkeypatch, tmp_path):
    cfg = tmp_path / "comms_config.json"
    cfg.write_text('{"wa_call_button_offsets": {"voice": [80, 70], "video": [130, 70]}}',
                   encoding="utf-8")
    monkeypatch.setattr(comms_agent, "CONFIG_PATH", str(cfg))
    log = _install_fakes(monkeypatch)
    note = comms_agent._wa_call_fallback_xy(False)
    assert note, "configured fallback chala nahi"
    # window 1000 wide, left 0 -> x = 0 + 1000 - 80 = 920 ; y = 0 + 70
    assert ("click", 920, 70) in log, log
    note_v = comms_agent._wa_call_fallback_xy(True)
    assert note_v and ("click", 870, 70) in log, log


def test_vision_targets_exclude_chat_text():
    """VLM ko chat ke 'Voice call' message pe click karne se roko."""
    for video in (False, True):
        t = comms_agent._WA_CALL_VISION_TARGETS[video]
        assert "NOT text inside chat messages" in t, t
        assert "top header bar right side" in t, t
    assert "handset" in comms_agent._WA_CALL_VISION_TARGETS[False]
    assert "video camera" in comms_agent._WA_CALL_VISION_TARGETS[True]


def test_vision_layer_uses_active_window(monkeypatch):
    log = _install_fakes(monkeypatch)
    seen = {}

    class _VA:
        @staticmethod
        def vision_click(target, dry_run=False, use_active_window=True):
            seen.update(target=target, dry_run=dry_run, uaw=use_active_window)
            return {"ok": True, "x": 900, "y": 60}

    monkeypatch.setitem(sys.modules, "vision_agent", _VA)
    note = comms_agent._wa_click_call_button_vision(False)
    # Locate only; the comms guard rechecks foreground before the real click.
    assert note and seen["dry_run"] is True and seen["uaw"] is True, seen
    assert [item for item in log if item[0] == "click"] == [("click", 900, 60)]


def test_probe_dumps_without_clicking(monkeypatch):
    _install_fakes(monkeypatch)
    _install_uia(monkeypatch, _realistic_tree([]))
    monkeypatch.setattr(comms_agent, "_wa_call_state_note",
                        lambda video=False, wait=None: ("absent", "none"))
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: (_ for _ in ()).throw(AssertionError("probe me click nahi")))
    out = str(comms_agent.whatsapp_call({"contact": "Pinkesh", "probe": True}))
    assert "whatsapp_call probe" in out and "strict candidates" in out, out
    assert "header_voice_btn" not in out  # dump naam print karta hai, id nahi


def test_probe_video_flag(monkeypatch):
    _install_fakes(monkeypatch)
    _install_uia(monkeypatch, _realistic_tree([]))
    monkeypatch.setattr(comms_agent, "_wa_call_state_note",
                        lambda video=False, wait=None: ("unknown", "x"))
    out = str(comms_agent.whatsapp_call({"probe": True, "video": True}))
    assert "video call" in out, out


def test_probe_cli_entrypoint():
    """python comms_agent.py --call-probe chal sake (exit 0, dump print ho)."""
    r = subprocess.run([sys.executable, os.path.join(ROOT, "comms_agent.py"), "--call-probe"],
                       capture_output=True, text=True, timeout=120, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-400:]
    assert "whatsapp_call probe" in r.stdout, r.stdout[-400:]


def test_probe_flag_parsing():
    assert comms_agent._wa_call_wants_probe({"probe": True}) is True
    assert comms_agent._wa_call_wants_probe({"probe": "true"}) is True
    assert comms_agent._wa_call_wants_probe({}) is False


# ================= VIDEO CALL + CONTACT RESOLVE =================

def test_video_flag_parsing():
    assert comms_agent._wa_call_wants_video({}) is False
    assert comms_agent._wa_call_wants_video({"video": True}) is True
    assert comms_agent._wa_call_wants_video({"video": "true"}) is True
    assert comms_agent._wa_call_wants_video({"video": "video"}) is True
    assert comms_agent._wa_call_wants_video({"video": "false"}) is False
    assert comms_agent._wa_call_wants_video({"video_call": "haan"}) is True


def test_video_call_flow(monkeypatch):
    log = _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_DETECTED, "end video call")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: log.append(("ui_click", video)) or "uia invoke 'Video call'")
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
    _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_DETECTED, "calling")])
    monkeypatch.setattr(comms_agent, "_resolve_contact", lambda n: ("9876543210", ""))
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui",
                        lambda video=False: "uia invoke 'Voice call'")

    def fake_open(name, after_open=None, wait_load=12):
        called["name"] = name
        return after_open(None, None, "desktop")

    monkeypatch.setattr(comms_agent, "_wa_open_chat_and_run", fake_open)
    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert called["name"] == "Pinkesh"
    assert "Pinkesh" in r and "laga diya" in r, r


def test_verifier_hints_for_call():
    ok, _ = verifier.verify({"tool": "whatsapp_call"},
                            "WhatsApp me 'Pinkesh' ko voice call laga diya (desktop mode).")
    assert ok
    bad, _ = verifier.verify({"tool": "whatsapp_call"},
                             "'Pinkesh' ko voice call nahi laga paya - fail (test)")
    assert not bad


def test_success_reply_has_no_parentheses(monkeypatch):
    """bolo.py TTS parentheses strip karta hai - spoken reply clean hona chahiye."""
    _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    _stub_verify(monkeypatch, [(comms_agent.WA_CALL_DETECTED, "calling")])
    monkeypatch.setattr(comms_agent, "_wa_focus_call_window", lambda: "")
    monkeypatch.setattr(comms_agent, "_wa_click_call_button_ui", lambda video=False: "uia invoke")
    r = str(comms_agent.whatsapp_call({"contact": "Pinkesh"}))
    assert r == "WhatsApp me Pinkesh ko voice call laga diya. Ringing ho raha hoga.", r


# ================= f) POLICY: ASK + AGENT SAFEGUARD =================

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


# ================= g) PLANNER + THINK WIRING =================

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


# ================= h) RT_BRAIN ROUTING ("X ko call karo") =================

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


@pytest.mark.parametrize('video,name,rect', [
    (False, 'Voice call', (1578, 101, 1660, 183)),
    (True, 'Video call', (1465, 101, 1547, 183)),
])
@pytest.mark.parametrize('runtime_id', [None, (42, 197, 1)])
def test_real_windows_79_repeated_wrappers_are_one_candidate(monkeypatch, video, name, rect, runtime_id):
    els = [_FakeEl(str(i), name, 'Button', rect) for i in range(79)]
    for el in els:
        el.element_info.runtime_id = runtime_id
    els += [_FakeEl('history1', 'Voice call Accepted on another device 11:09 am'),
            _FakeEl('history2', 'Video call 2 minutes 12:18 am')]
    win = _install_uia(monkeypatch, els)
    win._rect = _FakeRect(951, 0, 1929, 1137)
    scan = comms_agent._wa_scan_call_controls(win, video=video)
    assert scan['raw'] == 79 and scan['descendants'] == 81
    assert len(scan['candidates']) == 1
    assert scan['candidates'][0][:3] == (14, name, 'button')
    assert len(scan['near_misses']) == 2
    assert comms_agent._wa_win_score('WhatsApp', (951, 0, 1929, 1137)) == 197


def test_failed_duplicate_call_control_is_not_retried(monkeypatch):
    log = []
    duplicates = [_FakeEl(str(i), 'Voice call', 'Button', (900, 60, 940, 100), log)
                  for i in range(79)]
    def fail_invoke():
        log.append('failed invoke')
        raise RuntimeError('dead control')
    def fail_click():
        log.append('failed click_input')
        raise RuntimeError('dead control')
    for el in duplicates:
        el.element_info.runtime_id = (1, 197)
        el.invoke, el.click_input = fail_invoke, fail_click
    # Same geometry, DISTINCT runtime ID: must survive dedup and get attempted.
    good = _FakeEl('second', 'Voice call', 'Button', (900, 60, 940, 100), log)
    good.element_info.runtime_id = (2, 197)
    _install_uia(monkeypatch, duplicates + [good])
    monkeypatch.setattr(comms_agent, '_wa_focus_call_window', lambda: 'test focus')
    monkeypatch.setattr(comms_agent.time, 'sleep', lambda *_: None)
    assert comms_agent._wa_click_call_button_ui()
    assert log == ['failed invoke', 'failed click_input', ('invoke', 'second')]


def test_chat_open_unverified_foreground_never_types(monkeypatch):
    log = _install_fakes(monkeypatch)
    monkeypatch.setattr(comms_agent, '_wa_foreground_info', lambda: (999, 'Terminal'))
    ok, note = comms_agent._wa_open_chat_and_run('Test Contact')
    assert not ok and 'foreground unverified' in note
    assert not [event for event in log if event[0] in ('hotkey', 'press', 'click', 'copy')]


def test_chat_open_activate_exception_can_still_be_verified(monkeypatch):
    log = _install_fakes(monkeypatch)
    def fail(self):
        raise RuntimeError('Error code from Windows: 0')
    monkeypatch.setattr(_FakeWindow, 'activate', fail)
    assert comms_agent._wa_open_chat_and_run('Test Contact') == (True, 'desktop')
    assert ('hotkey', ('ctrl', 'f')) in log
