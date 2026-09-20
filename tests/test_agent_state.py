import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_state


@pytest.fixture
def fresh_state():
    agent_state.reset_state()
    yield agent_state.get_state()
    agent_state.reset_state()


def test_initial_mode(fresh_state):
    assert fresh_state.get_mode() == "idle"


def test_set_mode(fresh_state):
    fresh_state.set_mode("listening")
    assert fresh_state.get_mode() == "listening"


def test_start_task(fresh_state):
    fresh_state.start_task("Chrome kholo", ["open app", "search"])
    snap = fresh_state.get_snapshot()
    assert snap["current_task"] == "Chrome kholo"
    assert snap["task_goal"] == "Chrome kholo"
    assert len(snap["planned_steps"]) == 2
    assert snap["task_status"] == "planning"


def test_complete_task(fresh_state):
    fresh_state.start_task("Test")
    fresh_state.complete_task("done")
    snap = fresh_state.get_snapshot()
    assert snap["task_status"] == "done"
    assert snap["current_task"] is None


def test_record_action(fresh_state):
    fresh_state.record_action("open_app(chrome)")
    assert fresh_state.get_snapshot()["last_action"] == "open_app(chrome)"


def test_record_observation(fresh_state):
    fresh_state.record_observation("Chrome opened")
    assert fresh_state.get_snapshot()["last_observation"] == "Chrome opened"


def test_context_add(fresh_state):
    fresh_state.add_to_context("user", "hi")
    fresh_state.add_to_context("assistant", "hello")
    ctx = fresh_state.get_context()
    assert len(ctx) == 2
    assert ctx[0]["role"] == "user"


def test_context_limit(fresh_state):
    for i in range(30):
        fresh_state.add_to_context("user", f"msg {i}")
    ctx = fresh_state.get_context()
    assert len(ctx) <= 20


def test_clear_context(fresh_state):
    fresh_state.add_to_context("user", "hi")
    fresh_state.clear_context()
    assert len(fresh_state.get_context()) == 0


def test_retry_counter(fresh_state):
    assert fresh_state.increment_retry() == 1
    assert fresh_state.increment_retry() == 2


def test_pending_confirmation(fresh_state):
    assert fresh_state.get_snapshot()["pending_confirmation"] is None
    fresh_state.set_pending_confirmation({"tool": "shutdown"})
    assert fresh_state.get_snapshot()["pending_confirmation"] == {"tool": "shutdown"}
    fresh_state.clear_pending_confirmation()
    assert fresh_state.get_snapshot()["pending_confirmation"] is None
