"""
rt_main.py full-flow simulation (Problem 2 wiring):
listen -> STT -> brain -> speak -> barge-in captured audio -> turant
agla turn (pending_audio) - bina dobara listen kiye.
"""
import sys
import os
import types

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rt_main


class _FakeListen:
    SAMPLE_RATE = 16000

    def __init__(self, first_audio, barge_in_audio):
        self.first_audio = first_audio
        self.barge_in_audio = barge_in_audio
        self.listen_calls = 0
        self.stop_calls = 0

    def listen_vad(self, timeout_sec=60, debug=False):
        self.listen_calls += 1
        if self.listen_calls == 1:
            return self.first_audio, 1.0
        return None, 0

    def stop_barge_in_monitor(self):
        self.stop_calls += 1
        captured, self.barge_in_audio = self.barge_in_audio, None
        return captured


class _FakeSTT:
    def __init__(self, first_audio, barge_in_audio):
        self.first_audio = first_audio
        self.barge_in_audio = barge_in_audio
        self.seen = []

    def transcribe(self, audio):
        self.seen.append(audio)
        if audio is self.first_audio:
            return "kya haal hai"
        if audio is self.barge_in_audio:
            return "bye"
        return ""


class _FakeBrain:
    def __init__(self):
        self.queries = []

    def stream_reply(self, text, history=None):
        self.queries.append(text)
        yield ("token", "Sab badhiya Boss.")
        yield ("done", "Sab badhiya Boss.")


class _FakeSpeak:
    def __init__(self):
        self.spoken = []
        self.stopped = 0

    def speak(self, text, done_callback=None, block=False):
        self.spoken.append(text)
        if done_callback:
            done_callback()

    def speak_streaming(self, token_stream, done_callback=None):
        parts = []
        for item in token_stream:
            if isinstance(item, tuple) and item[0] == "token":
                parts.append(str(item[1]))
        full = "".join(parts)
        self.spoken.append(full)
        return full

    def stop_speaking(self):
        self.stopped += 1


def test_rt_main_barge_in_audio_becomes_next_turn(monkeypatch):
    first_audio = np.full(16000, 2000, dtype=np.int16)
    barge_audio = np.full(8000, 2000, dtype=np.int16)

    fake_listen = _FakeListen(first_audio, barge_audio)
    fake_stt = _FakeSTT(first_audio, barge_audio)
    fake_brain = _FakeBrain()
    fake_speak = _FakeSpeak()

    monkeypatch.setattr(rt_main, "rt_listen", fake_listen)
    monkeypatch.setattr(rt_main, "rt_stt", fake_stt)
    monkeypatch.setattr(rt_main, "rt_brain", fake_brain)
    monkeypatch.setattr(rt_main, "rt_speak", fake_speak)
    # reminders watcher ko no-op karo
    monkeypatch.setitem(sys.modules, "reminders",
                        types.SimpleNamespace(start_watcher=lambda cb: None))

    rt_main.realtime_loop()

    # Sirf EK baar mic listen hua - dusra turn barge-in captured audio se aaya
    assert fake_listen.listen_calls == 1
    assert fake_listen.stop_calls >= 1

    # Dono turns STT se gaye: pehla normal, dusra barge-in audio
    assert fake_stt.seen[0] is first_audio
    assert fake_stt.seen[1] is barge_audio

    # Brain sirf pehle turn pe chala, 'bye' pe exit ho gaya
    assert fake_brain.queries == ["kya haal hai"]
    assert any("Alvida" in s for s in fake_speak.spoken)
    assert fake_speak.stopped >= 1
