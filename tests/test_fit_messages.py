"""
413 fix tests (Problem 1 / P4) - think.fit_messages
Request strictly < 8000 tokens (~4 chars/token), system msg hamesha rahe,
purane history messages pehle drop hon.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import think


def _total_tokens(msgs):
    return sum(len(m["content"]) for m in msgs) // 4


def test_huge_request_fits_under_8000_tokens():
    huge = [{"role": "assistant", "content": "X " * 3000}] * 4
    msgs = think.fit_messages("S" * 20000, huge, "hello " * 100)
    assert _total_tokens(msgs) < 8000
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"


def test_caps_system_and_user():
    msgs = think.fit_messages("S" * 50000, [{"role": "user", "content": "y" * 10000}], "z" * 5000)
    assert len(msgs[0]["content"]) <= think.SYSTEM_CHAR_CAP
    assert len(msgs[-1]["content"]) <= think.USER_CHAR_CAP
    assert _total_tokens(msgs) < 8000


def test_system_always_kept_oldest_history_dropped():
    history = [{"role": "user", "content": f"msg-{i} " + "x" * 5000} for i in range(20)]
    msgs = think.fit_messages("SYSTEM PROMPT", history, "latest question")
    assert msgs[0]["content"] == "SYSTEM PROMPT"
    assert msgs[-1]["content"] == "latest question"
    kept = [m["content"] for m in msgs[1:-1]]
    # Jo bhi history bachi hai, wo NEWEST messages hone chahiye (purane drop)
    assert kept, "kuch history to rehni chahiye"
    assert any(k.startswith("msg-19") for k in kept)
    assert not any(k.startswith("msg-0 ") for k in kept)
    # order preserved (oldest->newest)
    idx = [int(k.split()[0].split("-")[1]) for k in kept]
    assert idx == sorted(idx)


def test_empty_history_ok():
    msgs = think.fit_messages("sys", [], "hi")
    assert len(msgs) == 2
    msgs = think.fit_messages("sys", None, "hi")
    assert len(msgs) == 2
