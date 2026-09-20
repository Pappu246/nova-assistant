"""
Phase 11 tests - Replanning + Verifier LLM fallback.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import verifier
import agent_loop


# ---- Verifier tests (LLM disabled) ----

def test_verify_with_llm_disabled_failure():
    ok, _ = verifier.verify({"tool": "open_app"}, "nahi mila", use_llm=False)
    assert ok is False


def test_verify_with_llm_disabled_success():
    ok, _ = verifier.verify({"tool": "open_app"}, "chrome khol diya", use_llm=False)
    assert ok is True


def test_verify_no_hint_lenient_no_llm():
    ok, _ = verifier.verify({"tool": "unknown_tool"}, "some result", use_llm=False)
    assert ok is True  # No hints = lenient default


def test_verify_known_tool_no_hint_no_llm():
    # Known tool with hints, no hint matched, no LLM
    ok, reason = verifier.verify({"tool": "open_app"}, "xyz abc", use_llm=False)
    assert ok is False
    assert "llm unavailable" in reason.lower() or "no success" in reason.lower()


def test_llm_verify_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = verifier._llm_verify({"tool": "open_app"}, "test")
    assert result is None


# ---- Agent loop replan context tests ----

def test_build_replan_context():
    all_results = [
        {"step": 1, "tool": "open_app", "status": "success", "reason": "ok", "result": ""},
        {"step": 2, "tool": "browse", "status": "failed", "reason": "nahi mila", "result": ""},
    ]
    failed_step = {"step": 2, "tool": "browse", "args": {"task": "test"}}
    ctx = agent_loop._build_replan_context(all_results, failed_step, "nahi mila")
    assert "Previous attempt" in ctx
    assert "open_app" in ctx
    assert "browse" in ctx
    assert "nahi mila" in ctx


def test_filter_plan_removes_chrome_open_app():
    plan = [
        {"step": 1, "tool": "open_app", "args": {"app_name": "Chrome"}},
        {"step": 2, "tool": "browse", "args": {"task": "test"}},
    ]
    filtered = agent_loop._filter_plan(plan)
    tools = [s["tool"] for s in filtered]
    assert "open_app" not in tools
    assert "browse" in tools


def test_filter_plan_keeps_non_chrome_open_app():
    plan = [
        {"step": 1, "tool": "open_app", "args": {"app_name": "notepad"}},
        {"step": 2, "tool": "browse", "args": {"task": "test"}},
    ]
    filtered = agent_loop._filter_plan(plan)
    tools = [s["tool"] for s in filtered]
    assert "open_app" in tools


def test_filter_plan_no_browse():
    plan = [
        {"step": 1, "tool": "open_app", "args": {"app_name": "notepad"}},
    ]
    filtered = agent_loop._filter_plan(plan)
    assert len(filtered) == 1
