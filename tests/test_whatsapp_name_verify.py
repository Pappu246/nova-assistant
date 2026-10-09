"""WhatsApp NAME verification regressions (mock UIA/OCR, runs on Linux).

Name-based chat open must: NOT press Esc, clear the search box and verify it is
empty (UIA value) before pasting, verify the search box shows the name before
Enter, and verify the chat header EXACTLY matches the target before any message
or call action. A message says 'bhej diya' only after a verified send.

No real WhatsApp, pyautogui, pywinauto or OCR runs here: the fake chat model in
tests/test_whatsapp_call.py answers for search box / composer / header.
"""
import io
import sys
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import app_control
import comms_agent as c
import verifier
from tests.test_whatsapp_call import (_FakeEl, _FakeUIAWindow, _install_fakes,
                                      _install_uia, _stub_no_active, _stub_verify)


# ================= helpers =================

class _FakeInput(_FakeEl):
    """Edit/Document control with a UIA Value pattern (get_value) and focus flag."""

    def __init__(self, el_id, value, rect, focused=False, control_type="Edit", readable=True):
        super().__init__(el_id, "message input", control_type, rect)
        self._value, self._focused, self._readable = value, focused, readable

    def get_value(self):
        if not self._readable:
            raise RuntimeError("ValuePattern not supported")
        return self._value

    def has_keyboard_focus(self):
        return self._focused


@pytest.fixture
def ocr(monkeypatch):
    """Fake vision_control: header OCR returns whatever the test puts in state['items']."""
    state = {"items": [], "regions": []}

    def _ocr_screen(region_mode="active", region=None):
        state["regions"].append((region_mode, region))
        return list(state["items"])

    monkeypatch.setitem(sys.modules, "vision_control", SimpleNamespace(
        _ocr_screen=_ocr_screen, read_screen=lambda region_mode="active": ""))
    return state


def _win(elements, rect=(0, 0, 1000, 800)):
    """WhatsApp window 1000x800. Header band = top 16% and x 30%..80%."""
    return _FakeUIAWindow(elements, rect=rect)


HEADER_TITLE = (320, 30, 420, 60)     # inside header band
CHAT_LIST_ITEM = (20, 200, 200, 220)  # left pane: NOT the header
BUBBLE = (400, 400, 600, 420)         # message area: NOT the header


# ================= 1. NORMALISATION + NAME MATCH =================

def test_norm_ignores_case_whitespace_and_bidi_marks():
    assert c._wa_norm("  PINKESH \u200e\n") == "pinkesh"
    assert c._wa_norm("Pinkesh\u00a0Sharma") == "pinkesh sharma"


def test_name_match_is_exact_not_partial():
    assert c._wa_name_matches("Pinkesh", " pinkesh ")
    assert not c._wa_name_matches("Pinkesh", "Pinkesh Sharma")
    assert not c._wa_name_matches("Pinkesh Sharma", "Pinkesh")
    assert not c._wa_name_matches("", "Pinkesh")
    assert not c._wa_name_matches("Pinkesh", "")


def test_name_match_compares_phone_digits_for_number_targets():
    assert c._wa_name_matches("9876543210", "+91 98765 43210")
    assert not c._wa_name_matches("9876543210", "+91 98765 43211")
    assert not c._wa_name_matches("9876543210", "Pinkesh")


# ================= 2. HEADER CHECK (UIA band + OCR fallback) =================

def test_header_exact_name_in_header_band_is_verified(monkeypatch, ocr):
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(True))
    win = _win([_FakeEl("hdr", "Pinkesh", "Text", HEADER_TITLE)])
    ok, detail = c._wa_chat_header_check("pinkesh", window=win)
    assert ok is True and "UIA" in detail, detail


def test_chat_list_and_message_names_never_count_as_header(monkeypatch, ocr):
    """Left-pane search hit / old chat bubble with the same name is NOT the open chat."""
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(True))
    win = _win([_FakeEl("list", "Pinkesh", "Text", CHAT_LIST_ITEM),
                _FakeEl("msg", "Pinkesh", "Text", BUBBLE)])
    ok, _ = c._wa_chat_header_check("Pinkesh", window=win)
    assert ok is False


def test_header_partial_or_longer_name_is_mismatch(monkeypatch, ocr):
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(True))
    win = _win([_FakeEl("hdr", "Pinkesh Sharma", "Text", HEADER_TITLE)])
    ocr["items"] = [("Pinkesh Sharma", 330, 35, 200, 25)]
    ok, _ = c._wa_chat_header_check("Pinkesh", window=win)
    assert ok is False


def test_header_falls_back_to_ocr_when_uia_exposes_no_name(monkeypatch, ocr):
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(True))
    win = _win([_FakeEl("btn", "Voice call", "Button", (850, 30, 890, 60))])
    ocr["items"] = [("Pinkesh", 330, 35, 100, 25), ("online", 330, 70, 60, 20)]
    ok, detail = c._wa_chat_header_check("Pinkesh", window=win)
    assert ok is True and "OCR" in detail, detail
    # OCR only looked at the header band of the WhatsApp window
    mode, region = ocr["regions"][-1]
    assert mode == "custom" and region[1] == 0 and region[2] < 1000 and region[3] <= 128


def test_header_unknown_without_uia_or_ocr_blocks(monkeypatch, ocr):
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(True))
    monkeypatch.setattr(c, "_wa_uia_window", lambda: None)
    monkeypatch.setattr(c, "_wa_gw_window", lambda: None)
    ok, _ = c._wa_chat_header_check("Pinkesh")
    assert ok is False


def test_header_phone_target_matches_formatted_header(monkeypatch, ocr):
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(True))
    win = _win([_FakeEl("hdr", "+91 98765 43210", "Text", HEADER_TITLE)])
    ok, _ = c._wa_chat_header_check("9876543210", window=win)
    assert ok is True


def test_header_check_fails_closed_without_dpi_context(monkeypatch, ocr):
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(False))
    win = _win([_FakeEl("hdr", "Pinkesh", "Text", HEADER_TITLE)])
    ok, detail = c._wa_chat_header_check("Pinkesh", window=win)
    assert ok is False and "DPI" in detail


def test_chat_layout_reads_header_names_and_inputs_in_one_pass(monkeypatch):
    monkeypatch.setattr(c, "_wa_physical_pixels", lambda _op: nullcontext(True))
    search = _FakeInput("search", "Pinkesh", (20, 60, 250, 100), focused=True)
    composer = _FakeInput("composer", "draft text", (300, 700, 900, 760))
    win = _win([_FakeEl("hdr", "Pinkesh", "Text", HEADER_TITLE), search, composer])
    snapshots = []
    win.descendants = lambda: snapshots.append(1) or [
        _FakeEl("hdr", "Pinkesh", "Text", HEADER_TITLE), search, composer]
    layout = c._wa_chat_layout(win)
    assert snapshots == [1], "chat layout must use ONE descendants snapshot"
    assert layout["header"] == ["Pinkesh"]
    assert layout["search"] == (1, "Pinkesh")
    assert layout["composer"] == (1, "draft text")


# ================= 3. SEARCH BOX + COMPOSER VALUE (UIA) =================

def test_search_value_is_focused_top_left_input(monkeypatch):
    search = _FakeInput("s", "", (20, 60, 250, 100), focused=True)
    composer = _FakeInput("m", "hi", (300, 700, 900, 760), focused=False)
    monkeypatch.setattr(c, "_wa_uia_window", lambda: _win([search, composer]))
    assert c._wa_search_box_value() == ""
    assert c._wa_composer_text() == "hi"


def test_ambiguous_or_unreadable_inputs_are_unknown(monkeypatch):
    two_search = [_FakeInput("a", "x", (20, 60, 250, 100)), _FakeInput("b", "y", (20, 110, 250, 150))]
    monkeypatch.setattr(c, "_wa_uia_window", lambda: _win(two_search))
    assert c._wa_search_box_value() is None
    unreadable = [_FakeInput("u", "", (20, 60, 250, 100), focused=True, readable=False)]
    monkeypatch.setattr(c, "_wa_uia_window", lambda: _win(unreadable))
    assert c._wa_search_box_value() is None
    monkeypatch.setattr(c, "_wa_uia_window", lambda: None)
    assert c._wa_search_box_value() is None and c._wa_composer_text() is None


# ================= 4. CHAT OPEN (name path) =================

def test_chat_open_never_presses_esc(monkeypatch):
    log = _install_fakes(monkeypatch)
    c._wa_open_chat_and_run("Pinkesh")
    assert ("hotkey", ("esc",)) not in log and ("press", "esc") not in log, log


def test_chat_open_clears_search_before_pasting_the_name(monkeypatch):
    log = _install_fakes(monkeypatch)
    log.search = "Ravi old search"  # leftover text from an earlier search
    ok, _ = c._wa_open_chat_and_run("Pinkesh")
    assert ok is True and log.header == "Pinkesh", log.header
    i_select = log.index(("hotkey", ("ctrl", "a")))
    i_clear = log.index(("press", "backspace"))
    i_paste = log.index(("copy", "Pinkesh"))
    assert i_select < i_clear < i_paste, log


def test_chat_open_aborts_without_enter_when_search_not_cleared(monkeypatch):
    log = _install_fakes(monkeypatch)
    log.clear_fails = True
    log.search = "old"
    called = []
    res = c._wa_open_chat_and_run("Pinkesh", after_open=lambda *a: called.append(a) or (True, "x"))
    assert res[0] is False and not called
    assert ("copy", "Pinkesh") not in log and ("press", "enter") not in log, log


def test_chat_open_aborts_without_enter_when_search_value_unreadable(monkeypatch):
    log = _install_fakes(monkeypatch)
    log.search_readable = False
    ok, note = c._wa_open_chat_and_run("Pinkesh")
    assert ok is False and "verify nahi hua" in note, note
    assert ("press", "enter") not in log


def test_chat_open_aborts_without_enter_when_paste_missed_search(monkeypatch):
    log = _install_fakes(monkeypatch)
    log.paste_lands = False
    called = []
    res = c._wa_open_chat_and_run("Pinkesh", after_open=lambda *a: called.append(a) or (True, "x"))
    assert res[0] is False and not called
    assert ("press", "enter") not in log, log


def test_chat_open_blocks_when_header_still_shows_previous_chat(monkeypatch):
    """Enter with no result leaves the old chat open: header must NOT match -> block."""
    log = _install_fakes(monkeypatch)
    log.results = {"Pinkesh": None}
    called = []
    res = c._wa_open_chat_and_run("Pinkesh", after_open=lambda *a: called.append(a) or (True, "x"))
    assert res[0] is False and res[2] == c.WA_CHAT_HEADER_UNVERIFIED, res
    assert not called and not log.sent


def test_chat_open_checks_header_after_enter_and_before_callback(monkeypatch):
    log = _install_fakes(monkeypatch)
    seen = []
    real_check = log.header_check

    def _check(target, window=None):
        seen.append(("header", log.header))
        return real_check(target, window)

    monkeypatch.setattr(c, "_wa_chat_header_check", _check)
    ok, _ = c._wa_open_chat_and_run(
        "Pinkesh", after_open=lambda pg, cb, mode: seen.append(("callback", log.header)) or (True, mode))
    assert ok is True
    assert seen[0][0] == "header" and seen[-1] == ("callback", "Pinkesh"), seen


# ================= 5. NAME-PATH MESSAGE SEND =================

@pytest.fixture
def send_env(monkeypatch):
    monkeypatch.setattr(c, "_resolve_contact", lambda _name: ("", ""))  # name path only
    return _install_fakes(monkeypatch)


def test_name_send_says_bhej_diya_only_after_verified_send(send_env):
    log = send_env
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert log.sent == [("Pinkesh", "hello")], log.sent
    assert "bhej diya" in r and "verify" in r.lower(), r
    ok, _ = verifier.verify({"tool": "whatsapp_send"}, r)
    assert ok is True


def test_name_send_header_mismatch_never_pastes_or_sends(send_env):
    log = send_env
    log.results = {"Pinkesh": "Pinkesh Sharma"}  # the first result is someone else
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert log.sent == [] and ("copy", "hello") not in log, log
    assert "bhej diya" not in r and "nahi hua" in r, r
    ok, _ = verifier.verify({"tool": "whatsapp_send"}, r)
    assert ok is False, "honest failure must fail verification: " + r


def test_name_send_search_not_cleared_never_sends(send_env):
    log = send_env
    log.clear_fails = True
    log.search = "old"
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert log.sent == [] and ("press", "enter") not in log, log
    assert "bhej diya" not in r and "fail" in r.lower(), r


def test_name_send_unverified_when_composer_not_cleared(send_env):
    log = send_env
    log.send_clears = False  # Enter pressed, but the composer still holds the text
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert log.sent == [("Pinkesh", "hello")]
    assert "bhej diya" not in r and "send verify nahi hua" in r, r
    ok, _ = verifier.verify({"tool": "whatsapp_send"}, r)
    assert ok is False


def test_name_send_unverified_when_enter_is_ignored(send_env):
    log = send_env
    log.enter_sends = False
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert log.sent == []
    assert "bhej diya" not in r and "nahi hua" in r, r


def test_name_send_blocks_enter_when_composer_paste_not_visible(send_env):
    log = send_env
    log.composer_paste_lands = False  # message never reached the composer
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert log.sent == [] and ("press", "enter") not in log[log.index(("copy", "hello")):]
    assert "bhej diya" not in r and "fail" in r.lower(), r


def test_name_send_unreadable_composer_is_never_claimed_as_sent(send_env):
    log = send_env
    log.composer_readable = False  # UIA can't prove the send
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert "bhej diya" not in r and "send verify nahi hua" in r, r
    ok, _ = verifier.verify({"tool": "whatsapp_send"}, r)
    assert ok is False


def test_name_send_auto_send_false_types_but_never_presses_enter(send_env):
    log = send_env
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello", "auto_send": False}))
    assert log.sent == [] and log.composer == "hello", log
    assert "bhej diya" not in r and "Enter tum daba do" in r, r


def test_name_send_default_auto_sends_after_header_verified(send_env):
    log = send_env
    c.whatsapp_send({"contact": "Pinkesh", "message": "hello"})
    assert log.sent == [("Pinkesh", "hello")]


# ================= 6. CALL START (name path gating) =================

def _record_clicks(monkeypatch, calls):
    """Clickers/double-dial guard record their use instead of raising (the call
    chain swallows exceptions, which would hide a wrong click)."""
    monkeypatch.setattr(c, "_wa_call_already_active", lambda video=False: calls.append("guard") or False)
    monkeypatch.setattr(c, "_wa_click_call_button_ui", lambda video=False: calls.append("ui") or "ui")
    monkeypatch.setattr(c, "_wa_click_call_button_vision", lambda video=False: calls.append("vision") or "v")
    monkeypatch.setattr(c, "_wa_call_fallback_xy", lambda video=False: calls.append("xy") or "xy")


def test_call_header_mismatch_never_clicks_or_checks_double_dial(monkeypatch):
    log = _install_fakes(monkeypatch)
    log.results = {"Pinkesh": "Pinkesh Sharma"}
    monkeypatch.setattr(c, "_wa_focus_call_window", lambda: "")
    calls = []
    _record_clicks(monkeypatch, calls)
    r = str(c.whatsapp_call({"contact": "Pinkesh"}))
    assert calls == [], "header mismatch: nothing may be clicked or probed: %r" % calls
    assert "laga diya" not in r and "nahi laga paya" in r and "fail" in r.lower(), r
    assert "verify nahi hua" in r, r
    ok, _ = verifier.verify({"tool": "whatsapp_call"}, r)
    assert ok is False


def test_call_header_unknown_blocks_click(monkeypatch):
    log = _install_fakes(monkeypatch)
    log.header_readable = False
    monkeypatch.setattr(c, "_wa_focus_call_window", lambda: "")
    calls = []
    _record_clicks(monkeypatch, calls)
    r = str(c.whatsapp_call({"contact": "Pinkesh"}))
    assert calls == [], calls
    assert "laga diya" not in r and "nahi laga paya" in r, r


def test_call_header_change_after_click_stops_further_clicks(monkeypatch):
    log = _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    monkeypatch.setattr(c, "_wa_focus_call_window", lambda: "")
    _stub_verify(monkeypatch, [(c.WA_CALL_DETECTED, "calling")])

    def _ui_click(video=False):
        log.header = "Ravi"          # the open chat changed under us
        return "uia invoke 'Voice call'"

    monkeypatch.setattr(c, "_wa_click_call_button_ui", _ui_click)
    calls = []
    monkeypatch.setattr(c, "_wa_click_call_button_vision", lambda video=False: calls.append("vision") or "v")
    monkeypatch.setattr(c, "_wa_call_fallback_xy", lambda video=False: calls.append("xy") or "xy")
    r = str(c.whatsapp_call({"contact": "Pinkesh"}))
    assert calls == [], "no further clicks after a header change: %r" % calls
    assert "laga diya" not in r and "confirm nahi kar paya" in r, r


def test_call_absent_after_every_click_is_verify_not_success(monkeypatch):
    _install_fakes(monkeypatch)
    _stub_no_active(monkeypatch)
    monkeypatch.setattr(c, "_wa_focus_call_window", lambda: "")
    _stub_verify(monkeypatch, [(c.WA_CALL_ABSENT, "no call-screen text")])
    monkeypatch.setattr(c, "_wa_click_call_button_ui", lambda video=False: "uia invoke")
    monkeypatch.setattr(c, "_wa_click_call_button_vision", lambda video=False: "vision_click (900,60)")
    monkeypatch.setattr(c, "_wa_call_fallback_xy", lambda video=False: None)
    r = str(c.whatsapp_call({"contact": "Pinkesh"}))
    assert "laga diya" not in r and "verify nahi hua" in r, r


# ================= 7. OCR REGIONS: off-screen clamp + crop width =================

def test_ocr_region_clamps_maximized_window_at_minus_8(monkeypatch):
    """Windows 10/11 maximized windows report (-8,-8): clamp, don't drop the region."""
    monkeypatch.setattr(c, "_wa_gw_window", lambda: SimpleNamespace(
        title="WhatsApp", left=-8, top=-8, width=1000, height=800))
    regions = c._wa_ocr_regions()
    assert regions[0] == ("whatsapp", (0, 0, 992, 792)), regions


def test_ocr_region_still_rejects_fully_minimized_window(monkeypatch):
    monkeypatch.setattr(c, "_wa_gw_window", lambda: SimpleNamespace(
        title="WhatsApp", left=-32000, top=-32000, width=237, height=39))
    assert [r[0] for r in c._wa_ocr_regions()] == ["active", "full"]


def _fake_pag(monkeypatch, screen=(1920, 1080)):
    import vision_control as vc
    shots = []

    class _PG:
        def size(self):
            return screen

        def screenshot(self, region=None):
            shots.append(region)
            return object()

    monkeypatch.setattr(vc, "_pag", _PG())
    return vc, shots


def test_ocr_custom_crop_width_is_right_after_left_clamp(monkeypatch):
    vc, shots = _fake_pag(monkeypatch)
    monkeypatch.setattr(vc, "_OCR", lambda arr: ([([[10, 10], [50, 10], [50, 30], [10, 30]],
                                                   "Calling", 0.9)], 0.0))
    items = vc._ocr_screen(region_mode="custom", region=(-8, -8, 1000, 800))
    assert shots == [(0, 0, 992, 792)], shots  # old code captured (0, 0, 1000, 800)
    assert items == [("Calling", 10, 10, 40, 20)], items


def test_ocr_custom_crop_clamps_right_and_bottom_edges(monkeypatch):
    vc, shots = _fake_pag(monkeypatch)
    monkeypatch.setattr(vc, "_OCR", lambda arr: ([], 0.0))
    vc._ocr_screen(region_mode="custom", region=(1500, 900, 1000, 800))
    assert shots == [(1500, 900, 420, 180)], shots


def test_ocr_custom_region_off_screen_never_falls_back_to_full_screen(monkeypatch):
    vc, shots = _fake_pag(monkeypatch)
    monkeypatch.setattr(vc, "_OCR", lambda arr: ([([[0, 0], [5, 0], [5, 5], [0, 5]], "Ringing", 1)], 0))
    assert vc._ocr_screen(region_mode="custom", region=(-32000, -32000, 237, 39)) == []
    assert shots == [], "custom region must never capture the full screen"


def test_ocr_active_window_at_minus_8_has_correct_width(monkeypatch):
    vc, shots = _fake_pag(monkeypatch)
    monkeypatch.setattr(vc, "_OCR", lambda arr: ([], 0.0))
    monkeypatch.setattr(vc, "_active_region", lambda: (-8, -8, 1000, 800))
    vc._ocr_screen(region_mode="active")
    assert shots == [(0, 0, 992, 792)], shots


# ================= 8. PROBE OUTPUT: cp1252 pipes must not crash =================

def test_wa_print_survives_cp1252_pipe(monkeypatch):
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="cp1252", errors="strict", write_through=True)
    monkeypatch.setattr(sys, "stdout", stream)
    c._wa_print("name=%r ok" % "\u4e2d\u6587")
    stream.flush()
    out = buf.getvalue().decode("cp1252")
    assert "\\u4e2d" in out and "ok" in out, out


def test_call_probe_with_unicode_names_survives_cp1252(monkeypatch):
    _install_fakes(monkeypatch)
    els = [_FakeEl("hdr", "Voice call", "Button", (900, 60, 940, 100)),
           _FakeEl("nm", "\u4e2d\u6587 call \u2713", "Text", (100, 400, 300, 420))]
    _install_uia(monkeypatch, els)
    monkeypatch.setattr(c, "_wa_focus_call_window", lambda: "foreground verified (test)")
    win = _FakeUIAWindow(els)
    monkeypatch.setattr(c, "_wa_uia_window_candidates", lambda: [(195, "WhatsApp", (0, 0, 1000, 800), win)])
    monkeypatch.setattr(c, "_wa_ocr_regions", lambda: [])
    monkeypatch.setattr(c, "_wa_call_state_note", lambda *a, **kw: ("unknown", "test"))
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="cp1252", errors="strict", write_through=True)
    monkeypatch.setattr(sys, "stdout", stream)
    out = str(c._wa_call_probe(video=False))  # must not raise UnicodeEncodeError
    assert "whatsapp_call probe" in out


# ================= 9. focus_window: no silent pass =================

def test_focus_window_fallback_failure_is_reported(monkeypatch, capsys):
    monkeypatch.setattr(app_control, "IS_WIN", True)

    class _Win:
        isMinimized = False

        def activate(self):
            raise RuntimeError("activate denied")

        def minimize(self):
            raise RuntimeError("minimize denied")

        def restore(self):
            raise RuntimeError("restore denied")

    monkeypatch.setattr(app_control, "_get_gw", lambda: SimpleNamespace(
        getWindowsWithTitle=lambda title: [_Win()]))
    app_control.focus_window("WhatsApp")
    out = capsys.readouterr().out
    assert "minimize denied" in out or "minimize/restore" in out, out


def test_name_send_waits_for_composer_uia_to_show_pasted_text(send_env, monkeypatch):
    """UIA can lag a moment behind the paste: a late-but-correct composer is still verified."""
    log = send_env
    real = log.composer_text
    reads = []

    def _lagging_read():
        reads.append(1)
        return "" if len(reads) == 1 else real()

    monkeypatch.setattr(c, "_wa_composer_text", _lagging_read)
    r = str(c.whatsapp_send({"contact": "Pinkesh", "message": "hello"}))
    assert log.sent == [("Pinkesh", "hello")], log.sent
    assert "bhej diya" in r, r


@pytest.mark.parametrize("raw,expected", [
    (None, True), ("", True), ("true", True), ("haan", True), (True, True),
    ("false", False), ("False", False), ("no", False), ("0", False), (False, False),
])
def test_auto_send_flag_parsing_on_name_path(raw, expected):
    args = {} if raw is None else {"auto_send": raw}
    assert c._wa_send_auto_name(args) is expected


def test_clamp_capture_uses_clamped_origin_when_screen_size_unknown(monkeypatch):
    import vision_control as vc

    class _NoSize:
        def size(self):
            raise RuntimeError("no screen size")

        def screenshot(self, region=None):
            return region

    monkeypatch.setattr(vc, "_pag", _NoSize())
    assert vc._clamp_capture((-8, -8, 1000, 800))[0] == (0, 0, 992, 792)
