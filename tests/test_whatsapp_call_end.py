"""Offline regressions for real Windows window/OCR failures and hang-up flow."""
import sys
from types import SimpleNamespace

import pytest
import comms_agent as c
import policy
import planner
import think
import tools
import verifier
from tests.test_whatsapp_call import _FakeEl, _FakeUIAWindow


@pytest.mark.parametrize('marker', c._WA_OCR_SELF_MARKERS)
def test_terminal_markers_never_detect_calls(monkeypatch, marker):
    monkeypatch.setattr(c, '_wa_ocr_regions', lambda: [('active', None)])
    monkeypatch.setattr(c, '_wa_ocr_read', lambda *a: marker.upper() + ' Ringing')
    assert c._wa_call_state_note(wait=0)[0] == c.WA_CALL_UNKNOWN


def test_discard_then_real_call(monkeypatch):
    monkeypatch.setattr(c, '_wa_ocr_regions', lambda: [('active', None), ('full', None)])
    monkeypatch.setattr(c, '_wa_ocr_read', lambda label, region:
                        'contact resolved ringing' if label == 'active' else 'End call')
    assert c._wa_call_state_note(wait=0)[0] == c.WA_CALL_DETECTED


def test_window_scoring_and_enumeration(monkeypatch):
    hidden = _FakeUIAWindow([], (-32000, -32000, -31763, -31961))
    real = _FakeUIAWindow([], (0, 0, 1000, 800))
    for w in (hidden, real):
        w.window_text = lambda: 'WhatsApp'
    desktop = SimpleNamespace(windows=lambda **kw: [hidden, real])
    monkeypatch.setitem(sys.modules, 'ui_agent', SimpleNamespace(
        IS_WIN=True, _Desktop=lambda **kw: desktop))
    assert c._wa_uia_window() is real
    assert c._wa_win_score('WhatsApp', (0, 0, 1000, 800)) == 195
    assert c._wa_uia_window_candidates()[0][3] is real


def test_gw_select_restore_activate(monkeypatch):
    log = []
    hidden = SimpleNamespace(title='WhatsApp', left=-32000, top=-32000, width=237, height=39)
    real = SimpleNamespace(title='WhatsApp', left=0, top=0, width=1000, height=800,
                           isMinimized=True, restore=lambda: log.append('restore'),
                           activate=lambda: log.append('activate'))
    monkeypatch.setitem(sys.modules, 'pygetwindow', SimpleNamespace(
        getWindowsWithTitle=lambda _: [hidden, real]))
    monkeypatch.setattr(c, '_wa_foreground_info', lambda: (None, 'WhatsApp'))
    assert c._wa_gw_window() is real
    c._wa_focus_call_window()
    assert log == ['restore', 'activate']


@pytest.mark.parametrize('rect,valid', [((10, 20, 1000, 800), True),
    ((-32000, -32000, 237, 39), False), ((0, 0, 99, 800), False)])
def test_ocr_bbox(monkeypatch, rect, valid):
    l, t, w, h = rect
    monkeypatch.setattr(c, '_wa_gw_window', lambda: SimpleNamespace(left=l, top=t, width=w, height=h))
    regions = c._wa_ocr_regions()
    assert regions[-2:] == [('active', None), ('full', None)]
    assert (len(regions) == 3) is valid
    if valid:
        assert regions[0] == ('whatsapp', rect)


def test_custom_ocr(monkeypatch):
    calls = []
    def ocr(**kw):
        calls.append(kw)
        return [('End call', 0, 0, 10, 10)]
    monkeypatch.setitem(sys.modules, 'vision_control', SimpleNamespace(_ocr_screen=ocr))
    assert c._wa_ocr_read('whatsapp', (10, 20, 300, 400)) == 'End call'
    assert calls == [dict(region_mode='custom', region=(10, 20, 300, 400))]


def test_end_candidates_no_header_bonus_and_near_misses(monkeypatch):
    els = [_FakeEl('bottom', 'End call', 'Button', (500, 700, 550, 750)),
           _FakeEl('top', 'End call', 'Button', (900, 10, 950, 50)),
           _FakeEl('log', 'Missed end call'),
           _FakeEl('custom', 'Custom camera control')]
    monkeypatch.setattr(c, '_wa_uia_window', lambda: _FakeUIAWindow(els))
    candidates = c._wa_uia_end_call_candidates()
    assert len(candidates) == 2
    assert [x[0] for x in candidates] == [9, 9]
    assert 'Custom camera control' in [x[0] for x in c._wa_near_miss_names()]


@pytest.mark.parametrize('success_layer', [0, 1, 2])
def test_end_chain_verified(monkeypatch, success_layer):
    calls = []
    monkeypatch.setattr(c, '_wa_focus_call_window', lambda: None)
    states = iter(['detected'] + ['detected'] * success_layer + ['absent'])
    monkeypatch.setattr(c, '_wa_call_state_note', lambda **kw: (next(states), 'hint'))
    for idx, name in enumerate(('_wa_click_end_call_button_ui', '_wa_click_end_call_button_vision', '_wa_end_call_fallback_xy')):
        monkeypatch.setattr(c, name, lambda i=idx: calls.append(i) or 'clicked')
    assert c.whatsapp_call_end({}) == 'WhatsApp call kaat di.'
    assert calls == list(range(success_layer + 1))


@pytest.mark.parametrize('initial', ['absent', 'unknown'])
def test_no_call_no_click(monkeypatch, initial):
    monkeypatch.setattr(c, '_wa_focus_call_window', lambda: None)
    monkeypatch.setattr(c, '_wa_call_state_note', lambda **kw: (initial, 'hint'))
    monkeypatch.setattr(c, '_wa_click_end_call_button_ui', lambda: pytest.fail('must not click'))
    result = c.whatsapp_call_end()
    assert ('kaatne ko kuch nahi' if initial == 'absent' else '--end-call-probe') in result


def test_unknown_after_click_is_failure(monkeypatch):
    monkeypatch.setattr(c, '_wa_focus_call_window', lambda: None)
    states = iter(['detected', 'unknown', 'unknown', 'unknown'])
    monkeypatch.setattr(c, '_wa_call_state_note', lambda **kw: (next(states), 'OCR unavailable'))
    for name in ('_wa_click_end_call_button_ui', '_wa_click_end_call_button_vision', '_wa_end_call_fallback_xy'):
        monkeypatch.setattr(c, name, lambda: 'clicked')
    assert c.whatsapp_call_end().startswith('Call kaat nahi paya, fail:')


def test_coords_disabled_and_configured(monkeypatch):
    monkeypatch.setattr(c, '_load_json', lambda _: {})
    assert c._wa_end_call_fallback_xy() is None
    monkeypatch.setattr(c, '_load_json', lambda _: {'wa_end_call_button_offsets': [500, 60]})
    monkeypatch.setattr(c, '_wa_gw_window', lambda: SimpleNamespace(title='WhatsApp', _hWnd=197, left=10, top=20, width=1000, height=800))
    calls = []
    monkeypatch.setitem(sys.modules, 'pyautogui', SimpleNamespace(click=lambda *xy: calls.append(xy)))
    monkeypatch.setattr(c, '_wa_foreground_info', lambda: (197, 'WhatsApp'))
    assert c._wa_end_call_fallback_xy()
    assert calls == [(510, 760)]


@pytest.mark.parametrize('command', ['call kaato', 'call kaat do', 'kaato', 'kaat do', 'cut karo', 'call cut'])
def test_end_command_not_confirmation(command):
    assert policy.looks_like_command(command)
    assert not policy.is_confirmation('haan ' + command)


def test_end_tool_wiring():
    assert policy.classify('whatsapp_call_end') == policy.SAFE
    assert policy.classify('whatsapp_call') == policy.ASK
    assert policy.classify('whatsapp_send') == policy.SAFE
    assert 'whatsapp_call_end' in tools.TOOLS
    assert 'whatsapp_call_end' in think.TOOL_SPECS
    assert 'whatsapp_call_end' in planner.TOOL_SCHEMAS
    assert verifier._SUCCESS_HINTS['whatsapp_call_end'] == ['whatsapp call kaat di']


@pytest.mark.parametrize('runtime_id', [None, (42, 197, 1)])
def test_end_call_79_repeated_wrappers_are_one_candidate(monkeypatch, runtime_id):
    els = [_FakeEl(str(i), 'End call', 'Button', (500, 700, 550, 750)) for i in range(79)]
    for el in els:
        el.element_info.runtime_id = runtime_id
    win = _FakeUIAWindow(els)
    monkeypatch.setattr(c, '_wa_uia_window', lambda: win)
    assert len(c._wa_uia_end_call_candidates()) == 1
    scan = c._wa_scan_call_controls(win, end_call=True)
    assert scan['raw'] == 79 and scan['candidates'][0][0] == 9


def test_failed_duplicate_end_control_is_not_retried(monkeypatch):
    from tests.test_whatsapp_call import _install_uia
    calls = []
    els = [_FakeEl(str(i), 'End call', 'Button', (500, 700, 550, 750)) for i in range(79)]
    def fail_invoke():
        calls.append('failed invoke')
        raise RuntimeError('stale control')
    def fail_click():
        calls.append('failed click_input')
        raise RuntimeError('stale control')
    for el in els:
        el.invoke, el.click_input = fail_invoke, fail_click
    good = _FakeEl('other', 'Hang up', 'Button', (600, 700, 650, 750), calls)
    _install_uia(monkeypatch, els + [good])
    assert c._wa_click_end_call_button_ui()
    assert calls == ['failed invoke', 'failed click_input', ('invoke', 'other')]
