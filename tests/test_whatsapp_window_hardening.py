"""No live calls: dedup, compact probes, fail-closed foreground/DPI guards.

Native Windows tests at the end exercise only thread DPI APIs (not input).
The 150% desktop evidence is reproduced using logical/physical fake bounds.
"""
import ctypes
import sys
import threading
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import comms_agent as c
from tests.test_whatsapp_call import _FakeEl, _FakeUIAWindow, _install_fakes, _install_uia


@pytest.mark.parametrize('end_call', [False, True])
def test_runtime_ids_are_authoritative_not_geometry(monkeypatch, end_call):
    name = 'End call' if end_call else 'Voice call'
    a, b, no_id = [_FakeEl(str(i), name, 'Button', (500, 100, 540, 140)) for i in range(3)]
    a.element_info.runtime_id = [42, 1]
    b.element_info.runtime_id = [42, 2]
    scan = c._wa_scan_call_controls(_FakeUIAWindow([a, a, b, no_id, no_id]), end_call=end_call)
    assert scan['raw'] == 5
    assert [item[3] for item in scan['candidates']] == [a, b, no_id]


def test_same_runtime_id_with_changed_rectangle_still_deduplicates():
    els = [_FakeEl('a', 'Video call', 'Button', (500, 10, 550, 50)),
           _FakeEl('b', 'Video call', 'Button', (600, 10, 650, 50))]
    for el in els:
        el.element_info.runtime_id = lambda: [42, 1]
    scan = c._wa_scan_call_controls(_FakeUIAWindow(els), video=True)
    assert scan['raw'] == 2 and len(scan['candidates']) == 1


def test_broken_runtime_id_uses_name_type_rect_fallback():
    class Info:
        name, control_type = 'Video call', 'Button'
        @property
        def runtime_id(self):
            raise RuntimeError('provider does not expose runtime ID')
    els = [_FakeEl(str(i), 'Video call', 'Button', (500, 10, 550, 50)) for i in range(79)]
    for el in els:
        el.element_info = Info()
    assert len(c._wa_scan_call_controls(_FakeUIAWindow(els), video=True)['candidates']) == 1


@pytest.mark.parametrize('end_call', [False, True])
def test_probe_is_compact_single_snapshot_and_uses_matching_weights(monkeypatch, capsys, end_call):
    name = 'End call' if end_call else 'Video call'
    els = [_FakeEl(str(i), name, 'Button', (700, 100, 740, 140)) for i in range(79)]
    near = [_FakeEl(str(i), 'Video call %d minutes 12:18 am' % i) for i in range(25)]
    els += (near * 341)[:8596 - 79]
    assert len(els) == 8596
    win = _FakeUIAWindow(els)
    snapshots = []
    win.descendants = lambda: snapshots.append('read') or els
    monkeypatch.setattr(c, '_wa_uia_window_candidates', lambda: [(195, 'WhatsApp', (0, 0, 1000, 800), win)])
    monkeypatch.setattr(c, '_wa_focus_call_window', lambda: 'foreground verified (test HWND)')
    monkeypatch.setattr(c, '_wa_ocr_regions', lambda: [('active', None)])
    monkeypatch.setattr(c, '_wa_ocr_read', lambda *a: 'contact resolved Ringing')
    monkeypatch.setattr(c, '_wa_call_state_note', lambda *a, **kw: ('unknown', 'terminal discarded'))
    monkeypatch.setattr(c, '_load_json', lambda _: {})
    out = c._wa_call_probe(video=True, end_call=end_call)
    assert snapshots == ['read']
    assert 'descendants count: 8596' in out
    assert 'STRICT candidates: raw=79 unique=1' in out
    assert 'focus-result: foreground verified' in out
    assert 'window score=195' in out and 'rect=(0, 0, 1000, 800)' in out
    assert out.count('near-miss name=') == c._WA_PROBE_LIMIT
    assert 'near-miss unique=25 (showing 10)' in out
    assert 'DISCARD terminal=contact resolved' in out
    assert len(out.splitlines()) < 35
    assert capsys.readouterr().out.count('STRICT candidates:') == 1
    weights = c._WA_END_CALL_UI_NAME_WEIGHTS if end_call else c._wa_call_name_weights(True)
    bad_words = c._WA_END_CALL_BAD_NAME_WORDS if end_call else c._WA_CALL_BAD_NAME_WORDS
    assert 'name weights: %s' % weights in out
    assert 'bad words: %s' % list(bad_words) in out
    if end_call:
        assert 'END-call name weights:' in out
        assert 'END-call bad words:' in out
        assert "'voice call':" not in out


@pytest.mark.parametrize('end_call', [False, True])
def test_descendants_failure_is_diagnostic(monkeypatch, capsys, end_call):
    def fail():
        raise RuntimeError('UIA provider disconnected')
    win = _FakeUIAWindow([])
    win.descendants = fail
    monkeypatch.setattr(c, '_wa_uia_window', lambda: win)
    fn = c._wa_uia_end_call_candidates if end_call else c._wa_uia_call_candidates
    assert fn(dump=True) == []
    output = capsys.readouterr().out
    assert 'descendants fail' in output and 'UIA provider disconnected' in output


def test_uia_and_win32_fallback_failures_are_not_swallowed(monkeypatch, capsys):
    def desktop(backend):
        raise RuntimeError(backend + ' backend broken')
    monkeypatch.setitem(sys.modules, 'ui_agent', SimpleNamespace(IS_WIN=True, _Desktop=desktop))
    assert c._wa_uia_window() is None
    out = capsys.readouterr().out
    assert 'uia window enumeration fail' in out and 'uia backend broken' in out
    assert 'win32 window enumeration fail' in out and 'win32 backend broken' in out


def test_uia_item_failure_does_not_hide_good_window(monkeypatch, capsys):
    def bad_title():
        raise RuntimeError('stale title')
    bad = SimpleNamespace(window_text=bad_title)
    good = _FakeUIAWindow([])
    desktop = SimpleNamespace(windows=lambda **kw: [bad, good])
    monkeypatch.setitem(sys.modules, 'ui_agent', SimpleNamespace(IS_WIN=True, _Desktop=lambda **kw: desktop))
    assert c._wa_uia_window() is good
    assert 'stale title' in capsys.readouterr().out


def test_gw_enumeration_failure_is_diagnostic(monkeypatch, capsys):
    def fail(_):
        raise RuntimeError('GW enumeration denied')
    monkeypatch.setitem(sys.modules, 'pygetwindow', SimpleNamespace(getWindowsWithTitle=fail))
    assert c._wa_gw_window() is None
    out = capsys.readouterr().out
    assert 'GW window enumeration fail' in out and 'GW enumeration denied' in out


def test_gw_item_failure_does_not_hide_good_window(monkeypatch, capsys):
    class Stale:
        @property
        def title(self):
            raise RuntimeError('stale HWND')
    good = SimpleNamespace(title='WhatsApp', left=951, top=0, width=978, height=1137)
    monkeypatch.setitem(sys.modules, 'pygetwindow', SimpleNamespace(getWindowsWithTitle=lambda _: [Stale(), good]))
    assert c._wa_gw_window() is good
    assert 'stale HWND' in capsys.readouterr().out


@pytest.mark.parametrize('target,foreground,expected', [
    ((197, 'WhatsApp'), (197, 'different title'), True),
    ((197, 'WhatsApp'), (198, 'WhatsApp'), False),  # no title override of HWND mismatch
    ((None, 'WhatsApp'), (None, 'whatsapp'), True),
    ((197, 'WhatsApp'), (None, 'WhatsApp'), True),
    ((None, 'WhatsApp'), (None, 'PowerShell WhatsApp debug'), False),
    ((None, 'WhatsApp'), (None, ''), False),
])
def test_foreground_hwnd_preferred_title_fallback(monkeypatch, target, foreground, expected):
    window = SimpleNamespace(_hWnd=target[0], title=target[1])
    monkeypatch.setattr(c, '_wa_foreground_info', lambda: foreground)
    assert c._wa_foreground_status(window)[0] is expected


def test_activate_error_zero_but_actual_foreground_verified(monkeypatch, capsys):
    def activate():
        raise RuntimeError('Error code from Windows: 0 - The operation completed success')
    window = SimpleNamespace(_hWnd=197, title='WhatsApp', activate=activate)
    monkeypatch.setattr(c, '_wa_gw_window', lambda: window)
    monkeypatch.setattr(c, '_wa_foreground_info', lambda: (197, 'WhatsApp'))
    monkeypatch.setitem(sys.modules, 'app_control', SimpleNamespace(
        focus_window=lambda _: pytest.fail('already foreground; no fallback allowed')))
    result = c._wa_focus_call_window()
    assert result.startswith('foreground verified')
    assert 'activate exception:' in result
    assert 'Windows: 0' in capsys.readouterr().out
    # The same run can still have valid active-window OCR after that exception.
    monkeypatch.setattr(c, '_wa_ocr_regions', lambda: [('active', None)])
    monkeypatch.setattr(c, '_wa_ocr_read', lambda *args: 'End call')
    assert c._wa_call_state_note(wait=0)[0] == c.WA_CALL_DETECTED


def test_successful_activate_and_fallback_strings_are_not_foreground_proof(monkeypatch):
    window = SimpleNamespace(_hWnd=197, title='WhatsApp', activate=lambda: None)
    monkeypatch.setattr(c, '_wa_gw_window', lambda: window)
    monkeypatch.setattr(c, '_wa_foreground_info', lambda: (198, 'Terminal'))
    monkeypatch.setitem(sys.modules, 'app_control', SimpleNamespace(focus_window=lambda _: 'WhatsApp focused'))
    assert c._wa_focus_call_window().startswith('foreground UNVERIFIED')


def test_focus_fallback_failure_is_diagnostic(monkeypatch, capsys):
    def fail(_):
        raise RuntimeError('fallback refused')
    monkeypatch.setattr(c, '_wa_gw_window', lambda: None)
    monkeypatch.setattr(c, '_wa_foreground_status', lambda *a: (False, 'unknown'))
    monkeypatch.setitem(sys.modules, 'app_control', SimpleNamespace(focus_window=fail))
    assert 'UNVERIFIED' in c._wa_focus_call_window()
    assert 'fallback refused' in capsys.readouterr().out


_SCREEN_LAYERS = ['voice_vision', 'end_vision', 'voice_coords', 'end_coords', 'uia_input']


def _screen_layer(monkeypatch, layer):
    log = _install_fakes(monkeypatch)
    monkeypatch.setattr(c, '_load_json', lambda _: {
        'wa_call_button_offsets': {'voice': [80, 70]}, 'wa_end_call_button_offsets': [500, 60]})
    monkeypatch.setitem(sys.modules, 'vision_agent', SimpleNamespace(
        vision_click=lambda *a, **kw: log.append(('vision_find', kw)) or dict(ok=True, x=900, y=60)))
    el = _FakeEl('noinvoke', 'Voice call', 'Button', (900, 60, 940, 100), log, can_invoke=False)
    _install_uia(monkeypatch, [el])
    fns = dict(voice_vision=c._wa_click_call_button_vision,
               end_vision=c._wa_click_end_call_button_vision,
               voice_coords=c._wa_call_fallback_xy,
               end_coords=c._wa_end_call_fallback_xy,
               uia_input=lambda: c._wa_uia_click(el))
    return log, fns[layer]


@pytest.mark.parametrize('layer', _SCREEN_LAYERS)
def test_unverified_foreground_blocks_every_screen_click(monkeypatch, capsys, layer):
    log, fn = _screen_layer(monkeypatch, layer)
    monkeypatch.setattr(c, '_wa_foreground_info', lambda: (999, 'WhatsApp'))
    result = fn()
    assert result is None or result[0] is False
    assert not log
    assert 'foreground unverified' in capsys.readouterr().out


@pytest.mark.parametrize('layer', _SCREEN_LAYERS)
def test_dpi_setup_failure_blocks_every_screen_click(monkeypatch, layer):
    log, fn = _screen_layer(monkeypatch, layer)
    monkeypatch.setattr(c, '_wa_physical_pixels', lambda _: nullcontext(False))
    result = fn()
    assert result is None or result[0] is False
    assert not log


def test_invoke_preserved_without_foreground_or_dpi(monkeypatch):
    log = []
    el = _FakeEl('coordinate-free', 'Video call', 'Button', log=log)
    monkeypatch.setattr(c, '_wa_physical_pixels', lambda _: pytest.fail('invoke needs no DPI'))
    monkeypatch.setattr(c, '_wa_foreground_status', lambda *a: (False, 'unknown'))
    assert c._wa_uia_click(el) == (True, 'invoke')
    assert log == [('invoke', 'coordinate-free')]


@pytest.mark.parametrize('end_call', [False, True])
@pytest.mark.parametrize('change', ['foreground', 'bounds', 'outside'])
def test_vision_revalidates_after_slow_vlm_lookup(monkeypatch, end_call, change):
    log, fn = _screen_layer(monkeypatch, 'end_vision' if end_call else 'voice_vision')
    window = c._wa_gw_window()
    monkeypatch.setattr(c, '_wa_gw_window', lambda: window)
    def locate(*args, **kw):
        assert kw == dict(dry_run=True, use_active_window=True)
        if change == 'foreground':
            monkeypatch.setattr(c, '_wa_foreground_info', lambda: (999, 'Terminal'))
        elif change == 'bounds':
            window.left += 100
        return dict(ok=True, x=1200 if change == 'outside' else 900, y=60)
    monkeypatch.setitem(sys.modules, 'vision_agent', SimpleNamespace(vision_click=locate))
    assert fn() is None
    assert not log


@pytest.mark.parametrize('end_call', [False, True])
@pytest.mark.parametrize('offset', [(-1, 70), (2000, 70), (80, -1), (80, 900), ('bad', 70)])
def test_invalid_configured_offsets_never_click(monkeypatch, end_call, offset):
    log = _install_fakes(monkeypatch)
    assert c._wa_offset_click(offset, end_call=end_call) is None
    assert not log


@pytest.mark.parametrize('end_call,offset', [(False, (0, 70)), (True, (500, 0))])
def test_right_and_bottom_exclusive_bounds(monkeypatch, end_call, offset):
    log = _install_fakes(monkeypatch)
    assert c._wa_offset_click(offset, end_call=end_call) is None
    assert not log


@pytest.mark.parametrize('bounds', [(-32000, -32000, 237, 39), (0, 0, 0, 800), (-10, 0, 1000, 800)])
def test_invalid_window_bounds_never_click(monkeypatch, bounds):
    log = _install_fakes(monkeypatch)
    l, t, w, h = bounds
    window = SimpleNamespace(_hWnd=197, title='WhatsApp', left=l, top=t, width=w, height=h)
    monkeypatch.setattr(c, '_wa_gw_window', lambda: window)
    assert c._wa_offset_click([80, 70]) is None
    assert not log


def _fake_dpi(monkeypatch, initial=0x1234567800000001):
    state = {'context': initial, 'calls': []}
    def setter(value):
        old = state['context']
        state['calls'].append(value)
        state['context'] = value
        return old
    monkeypatch.setattr(c, '_wa_on_windows', lambda: True)
    monkeypatch.setattr(c, '_wa_dpi_api', lambda: setter)
    return state


def test_dpi_api_binds_pointer_sized_handles(monkeypatch):
    def setter(value):
        return value
    monkeypatch.setattr(ctypes, 'WinDLL', lambda *a, **kw: SimpleNamespace(
        SetThreadDpiAwarenessContext=setter), raising=False)
    assert c._wa_dpi_api() is setter
    assert setter.argtypes == [ctypes.c_void_p]
    assert setter.restype is ctypes.c_void_p


def test_dpi_nested_scopes_and_exception_restore_exact_previous_context(monkeypatch):
    original = 0x1234567800000001
    state = _fake_dpi(monkeypatch, initial=original)
    with pytest.raises(ValueError, match='body error'):
        with c._wa_physical_pixels('outer') as ready:
            assert ready and state['context'] == -4
            with c._wa_physical_pixels('inner') as inner_ready:
                assert inner_ready and state['context'] == -4
            assert state['context'] == -4
            raise ValueError('body error')
    assert state == {'context': original, 'calls': [-4, -4, -4, original]}


@pytest.mark.parametrize('failure', ['null', 'exception', 'missing_api'])
def test_dpi_failure_is_fail_closed_without_global_fallback(monkeypatch, capsys, failure):
    calls = []
    def setter(value):
        calls.append(value)
        if failure == 'exception':
            raise OSError('access denied')
        return None
    def api():
        if failure == 'missing_api':
            raise AttributeError('SetThreadDpiAwarenessContext unavailable')
        return setter
    monkeypatch.setattr(c, '_wa_on_windows', lambda: True)
    monkeypatch.setattr(c, '_wa_dpi_api', api)
    with c._wa_physical_pixels('test operation') as ready:
        assert ready is False
    assert calls == ([] if failure == 'missing_api' else [-4])
    assert 'DPI setup fail; unsafe screen operation skipped' in capsys.readouterr().out


def test_dpi_restore_failure_is_reported(monkeypatch, capsys):
    calls = []
    def setter(value):
        calls.append(value)
        return 42 if len(calls) == 1 else None
    monkeypatch.setattr(c, '_wa_on_windows', lambda: True)
    monkeypatch.setattr(c, '_wa_dpi_api', lambda: setter)
    with c._wa_physical_pixels('test operation') as ready:
        assert ready
    assert calls == [-4, 42]
    assert 'DPI restore fail' in capsys.readouterr().out


def test_non_windows_dpi_scope_is_noop(monkeypatch):
    monkeypatch.setattr(c, '_wa_on_windows', lambda: False)
    monkeypatch.setattr(c, '_wa_dpi_api', lambda: pytest.fail('Windows API on non-Windows'))
    with c._wa_physical_pixels('portable') as ready:
        assert ready


@pytest.mark.parametrize('layer', _SCREEN_LAYERS)
def test_screen_layers_consume_coordinates_in_physical_scope(monkeypatch, layer):
    log, fn = _screen_layer(monkeypatch, layer)
    state = _fake_dpi(monkeypatch, initial=42)
    assertions = []
    def record(*args, **kwargs):
        assert state['context'] == -4
        assertions.append(args)
        return dict(ok=True, x=900, y=60)
    monkeypatch.setitem(sys.modules, 'pyautogui', SimpleNamespace(click=record))
    monkeypatch.setitem(sys.modules, 'vision_agent', SimpleNamespace(vision_click=record))
    if layer == 'uia_input':
        win = c._wa_uia_window()
        win._desc[0].click_input = record
    assert fn()
    assert assertions
    assert state['context'] == 42


def test_150_percent_gw_bbox_and_ocr_consumption_share_physical_pixels(monkeypatch):
    state = _fake_dpi(monkeypatch, initial=42)
    class ScaledWindow:
        title, _hWnd = 'WhatsApp', 197
        @property
        def left(self):
            return 951 if state['context'] == -4 else 634
        top = 0
        @property
        def width(self):
            return 978 if state['context'] == -4 else 652
        @property
        def height(self):
            return 1137 if state['context'] == -4 else 758
    monkeypatch.setitem(sys.modules, 'pygetwindow', SimpleNamespace(
        getWindowsWithTitle=lambda _: [ScaledWindow()]))
    regions = []
    def ocr(**kw):
        assert state['context'] == -4
        regions.append(kw['region'])
        return [('Calling', 0, 0, 1, 1)]
    monkeypatch.setitem(sys.modules, 'vision_control', SimpleNamespace(_ocr_screen=ocr))
    assert c._wa_call_state_note(wait=0) == ('detected', 'calling')
    assert regions == [(951, 0, 978, 1137)]
    assert state['context'] == 42
    clicks = []
    def click(x, y):
        assert state['context'] == -4
        clicks.append((x, y))
    monkeypatch.setitem(sys.modules, 'pyautogui', SimpleNamespace(click=click))
    monkeypatch.setattr(c, '_wa_foreground_info', lambda: (197, 'WhatsApp'))
    assert c._wa_offset_click([80, 70])
    assert clicks == [(1849, 70)]
    assert state['context'] == 42


def test_dpi_failure_skips_all_ocr_and_bbox_work(monkeypatch):
    monkeypatch.setattr(c, '_wa_physical_pixels', lambda _: nullcontext(False))
    def unsafe(*args, **kwargs):
        pytest.fail('unsafe capture/enumeration must not run')
    monkeypatch.setitem(sys.modules, 'vision_control', SimpleNamespace(_ocr_screen=unsafe, read_screen=unsafe))
    monkeypatch.setitem(sys.modules, 'pygetwindow', SimpleNamespace(getWindowsWithTitle=unsafe))
    assert c._wa_gw_window() is None
    assert c._wa_ocr_regions() == []
    with pytest.raises(RuntimeError, match='DPI context unavailable'):
        c._wa_ocr_read('active', None)
    state, note = c._wa_call_state_note(wait=0)
    assert state == c.WA_CALL_UNKNOWN and 'DPI' in note


# Real Windows API regressions: no WhatsApp, desktop input or third-party GUI
# imports. These run on the Windows CI matrix, including Python 3.14.
def _native_dpi_functions():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    get = user32.GetThreadDpiAwarenessContext
    get.argtypes, get.restype = [], ctypes.c_void_p
    equal = user32.AreDpiAwarenessContextsEqual
    equal.argtypes, equal.restype = [ctypes.c_void_p, ctypes.c_void_p], ctypes.c_bool
    awareness = user32.GetAwarenessFromDpiAwarenessContext
    awareness.argtypes, awareness.restype = [ctypes.c_void_p], ctypes.c_int
    return get, equal, awareness


@pytest.mark.skipif(sys.platform != 'win32', reason='native Windows thread DPI API')
def test_windows_native_dpi_scope_restores_after_exception():
    get, equal, awareness = _native_dpi_functions()
    setter = c._wa_dpi_api()
    initial = setter(-1)  # simulate an unaware caller (e.g. before GUI imports)
    assert initial
    try:
        before = get()
        with pytest.raises(ValueError, match='test body'):
            with c._wa_physical_pixels('native test') as ready:
                assert ready and awareness(get()) == 2
                with c._wa_physical_pixels('native nested') as nested:
                    assert nested and awareness(get()) == 2
                raise ValueError('test body')
        assert equal(get(), before)
    finally:
        assert setter(initial)


@pytest.mark.skipif(sys.platform != 'win32', reason='native Windows thread DPI API')
def test_windows_native_dpi_does_not_change_process_default():
    # Current-process shortcuts (including GetCurrentProcess's pseudo handle)
    # can report the calling thread's override on Windows. An independent
    # observer with a real handle to THIS process measures the process default,
    # not its own DPI context or the overridden test thread's context.
    import os
    import subprocess
    get, _, awareness = _native_dpi_functions()
    script = """
import ctypes, sys
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_bool
user32 = ctypes.WinDLL('user32', use_last_error=True)
context = user32.GetDpiAwarenessContextForProcess
context.argtypes, context.restype = [ctypes.c_void_p], ctypes.c_void_p
awareness = user32.GetAwarenessFromDpiAwarenessContext
awareness.argtypes, awareness.restype = [ctypes.c_void_p], ctypes.c_int
process = kernel32.OpenProcess(0x1000, False, int(sys.argv[1]))
assert process, ctypes.get_last_error()
try:
    value = context(process)
    assert value, ctypes.get_last_error()
    print(awareness(value))
finally:
    assert kernel32.CloseHandle(process)
"""
    def process_default():
        result = subprocess.run([sys.executable, '-c', script, str(os.getpid())],
                                capture_output=True, text=True, check=True,
                                timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        value = int(result.stdout.strip())
        assert value in (0, 1, 2)
        return value
    before = process_default()
    with c._wa_physical_pixels('native process check') as ready:
        assert ready and awareness(get()) == 2
        assert process_default() == before
    assert process_default() == before


@pytest.mark.skipif(sys.platform != 'win32', reason='native Windows thread DPI API')
def test_windows_native_dpi_is_thread_local():
    from concurrent.futures import ThreadPoolExecutor
    get, equal, awareness = _native_dpi_functions()
    setter = c._wa_dpi_api()
    initial = setter(-1)
    assert initial
    entered, release = threading.Event(), threading.Event()
    def worker():
        before = get()
        with c._wa_physical_pixels('native worker') as ready:
            assert ready and awareness(get()) == 2
            entered.set()
            assert release.wait(10)
        assert equal(get(), before)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker)
            try:
                assert entered.wait(10)
                assert awareness(get()) == 0  # caller thread remains unaware
            finally:
                release.set()
            future.result(timeout=10)
    finally:
        assert setter(initial)


@pytest.mark.parametrize('blocked_by', ['foreground', 'dpi', 'bounds'])
def test_shared_web_chat_screen_click_is_also_guarded(monkeypatch, blocked_by):
    log = _install_fakes(monkeypatch)
    window = c._wa_gw_window()
    if blocked_by == 'foreground':
        monkeypatch.setattr(c, '_wa_foreground_info', lambda: (999, 'Terminal'))
    if blocked_by == 'dpi':
        monkeypatch.setattr(c, '_wa_physical_pixels', lambda _: nullcontext(False))
    xy = [2000, 20] if blocked_by == 'bounds' else None
    assert not c._wa_web_search_click(window, xy, sys.modules['pyautogui'])
    assert not log


def test_shared_web_chat_bounds_and_click_are_in_physical_scope(monkeypatch):
    log = _install_fakes(monkeypatch)
    state = _fake_dpi(monkeypatch, initial=42)
    class Window:
        _hWnd = 197
        @property
        def left(self):
            assert state['context'] == -4
            return 951
        top, width, height = 0, 978, 1137
    def click(x, y):
        assert state['context'] == -4
        log.append((x, y))
    assert c._wa_web_search_click(Window(), None, SimpleNamespace(click=click))
    assert log == [(1101, 130)]
    assert state['context'] == 42
