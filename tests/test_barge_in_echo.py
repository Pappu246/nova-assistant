"""
Barge-in ECHO fix tests (Problem 2) - rt_listen.py
NOVA apni hi TTS awaaz se interrupt NA ho:
  - BARGE_IN_THRESHOLD 0.90
  - 400ms grace period (start_monitor_time check)
  - >= 5 consecutive speech frames
  - captured audio pe energy check (echo discard) before STT
Fake sounddevice stream se real monitor code ko synthetic frames feed karte hain.
"""
import sys
import os
import time
import threading

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rt_listen


# ---------- Fake sounddevice ----------
class _FakeStream:
    """InputStream jo pre-set frames deta hai, khatam hone pe silence."""
    frames = []  # class-level script, tests set karte hain

    def __init__(self, *a, **kw):
        self._i = 0

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass

    def read(self, n):
        # Real InputStream.read ~32ms block karta hai - simulate pacing
        time.sleep(0.005)
        if self._i < len(_FakeStream.frames):
            f = _FakeStream.frames[self._i]
            self._i += 1
        else:
            f = np.zeros((n, 1), dtype=np.int16)
        return f, False


class _FakeSD:
    InputStream = _FakeStream


def _frame(amplitude, n=512):
    """Constant-amplitude int16 frame; RMS == amplitude."""
    return np.full((n, 1), int(amplitude), dtype=np.int16)


LOUD = 1500    # user speech: prob=1.0, rms 1500 >= 500
ECHO = 700     # NOVA echo jaisa: prob 0.875 < 0.90 threshold
QUIET = 0


@pytest.fixture
def fake_mic(monkeypatch):
    monkeypatch.setattr(rt_listen, "sd", _FakeSD, raising=False)
    monkeypatch.setattr(rt_listen, "_SD", True)
    monkeypatch.setattr(rt_listen, "_SILERO", False)   # energy-prob fallback
    monkeypatch.setattr(rt_listen, "_vad_model", None)
    _FakeStream.frames = []
    # ensure clean state
    rt_listen._barge_in_active = False
    rt_listen._barge_in_thread = None
    rt_listen._barge_in_audio_captured = None
    yield
    rt_listen.stop_barge_in_monitor()


def _run_monitor(frames, wait_sec):
    """Monitor chalao, barge-in callback hua ya nahi return karo."""
    _FakeStream.frames = frames
    fired = threading.Event()
    rt_listen.start_barge_in_monitor(fired.set)
    fired.wait(wait_sec)
    captured = rt_listen.stop_barge_in_monitor()
    return fired.is_set(), captured


def test_constants_tuned_for_echo():
    assert rt_listen.BARGE_IN_THRESHOLD == 0.90
    assert rt_listen.BARGE_IN_GRACE_MS == 400
    assert rt_listen.BARGE_IN_MIN_FRAMES == 5
    assert rt_listen.BARGE_IN_MIN_RMS > 0


def test_grace_period_blocks_initial_echo(fake_mic, monkeypatch):
    """TTS start ke pehle 400ms me loud frames aayein to bhi trigger NA ho."""
    # Sirf grace window ke andar hi loud frames (phir silence)
    frames = [_frame(LOUD)] * 25  # ~25 frames, sab grace ke andar consume honge
    _FakeStream.frames = frames
    fired = threading.Event()
    rt_listen.start_barge_in_monitor(fired.set)
    time.sleep(0.30)  # < 400ms grace
    assert not fired.is_set(), "Grace period me barge-in trigger nahi hona chahiye"
    rt_listen.stop_barge_in_monitor()


def test_sustained_loud_user_speech_triggers(fake_mic, monkeypatch):
    """Grace ke baad 5+ consecutive loud frames -> barge-in trigger."""
    monkeypatch.setattr(rt_listen, "BARGE_IN_GRACE_MS", 50)  # test ko fast rakho
    frames = [_frame(LOUD)] * 400
    fired, captured = _run_monitor(frames, wait_sec=3.0)
    assert fired, "Sustained user speech pe barge-in hona chahiye"
    assert captured is not None and len(captured) > 0
    assert rt_listen._audio_rms(captured) >= rt_listen.BARGE_IN_MIN_RMS


def test_echo_level_audio_does_not_trigger(fake_mic, monkeypatch):
    """NOVA ki echo jaisi medium-prob awaaz (prob < 0.90) -> koi trigger nahi."""
    monkeypatch.setattr(rt_listen, "BARGE_IN_GRACE_MS", 50)
    frames = [_frame(ECHO)] * 300
    fired, captured = _run_monitor(frames, wait_sec=1.2)
    assert not fired, "Echo-level audio se barge-in NAHI hona chahiye (threshold 0.90)"
    assert captured is None


def test_short_bursts_below_5_frames_do_not_trigger(fake_mic, monkeypatch):
    """4-frame ke chhote bursts (echo blips) kabhi 5 consecutive nahi bante."""
    monkeypatch.setattr(rt_listen, "BARGE_IN_GRACE_MS", 50)
    pattern = ([_frame(LOUD)] * 4 + [_frame(QUIET)] * 6) * 25
    fired, captured = _run_monitor(pattern, wait_sec=1.5)
    assert not fired, "<5 consecutive frames pe barge-in NAHI hona chahiye"


def test_captured_echo_audio_discarded_before_stt(fake_mic):
    """stop_barge_in_monitor low-energy (echo) captured audio ko STT pe NAHI bhejta."""
    # Low-RMS captured audio (echo) -> None
    rt_listen._barge_in_active = False
    rt_listen._barge_in_thread = None
    rt_listen._barge_in_audio_captured = np.full(14000, 100, dtype=np.int16)  # rms 100 < 500
    assert rt_listen.stop_barge_in_monitor() is None

    # High-RMS captured audio (real user) -> wapas milta hai
    rt_listen._barge_in_audio_captured = np.full(14000, 2000, dtype=np.int16)
    out = rt_listen.stop_barge_in_monitor()
    assert out is not None and len(out) == 14000


def test_is_probable_user_speech_helper():
    assert not rt_listen._is_probable_user_speech(np.zeros(1000, dtype=np.int16))
    assert not rt_listen._is_probable_user_speech(np.full(1000, 100, dtype=np.int16))
    assert rt_listen._is_probable_user_speech(np.full(1000, 2000, dtype=np.int16))


@pytest.mark.parametrize("count, expected", [(4, False), (5, True)])
def test_exact_five_frame_boundary(fake_mic, monkeypatch, count, expected):
    monkeypatch.setattr(rt_listen, "BARGE_IN_GRACE_MS", 0)
    fired, _ = _run_monitor([_frame(LOUD)] * count, wait_sec=0.5)
    assert fired is expected
