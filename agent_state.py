"""
NOVA Agent State - single source of truth for runtime state.

Used by:
  - main.py     (mode + conversation tracking)
  - brain.py    (task context for LLM)
  - tools.py    (last action + result)
  - future: planner, verifier, permission layer
"""
import threading
import datetime


class AgentState:
    def __init__(self):
        self._lock = threading.Lock()
        self._reset_fields()

    def _reset_fields(self):
        self.current_mode = "idle"
        self.current_task = None
        self.task_goal = None
        self.current_step = 0
        self.planned_steps = []
        self.current_app = None
        self.last_action = None
        self.last_observation = None
        self.last_tool_result = None
        self.pending_confirmation = None
        self.task_status = "idle"
        self.retry_count = 0
        self.conversation_context = []
        self.started_at = datetime.datetime.now().isoformat()

    def reset(self):
        with self._lock:
            self._reset_fields()

    # -------- Mode --------
    def set_mode(self, mode):
        with self._lock:
            self.current_mode = mode

    def get_mode(self):
        with self._lock:
            return self.current_mode

    # -------- Task --------
    def start_task(self, goal, steps=None):
        with self._lock:
            self.current_task = goal
            self.task_goal = goal
            self.planned_steps = list(steps) if steps else []
            self.current_step = 0
            self.task_status = "planning"
            self.retry_count = 0

    def set_step(self, step_num):
        with self._lock:
            self.current_step = step_num

    def set_status(self, status):
        with self._lock:
            self.task_status = status

    def complete_task(self, status="done"):
        with self._lock:
            self.task_status = status
            self.current_task = None
            self.task_goal = None
            self.planned_steps = []

    def increment_retry(self):
        with self._lock:
            self.retry_count += 1
            return self.retry_count

    # -------- Observations / Actions --------
    def record_action(self, action):
        with self._lock:
            self.last_action = action

    def record_observation(self, obs):
        with self._lock:
            self.last_observation = obs

    def record_tool_result(self, result):
        with self._lock:
            self.last_tool_result = result

    def set_current_app(self, app):
        with self._lock:
            self.current_app = app

    # -------- Confirmation --------
    def set_pending_confirmation(self, conf):
        with self._lock:
            self.pending_confirmation = conf

    def clear_pending_confirmation(self):
        with self._lock:
            self.pending_confirmation = None

    # -------- Conversation --------
    def add_to_context(self, role, content):
        with self._lock:
            self.conversation_context.append({"role": role, "content": content})
            if len(self.conversation_context) > 20:
                self.conversation_context = self.conversation_context[-20:]

    def get_context(self):
        with self._lock:
            return list(self.conversation_context)

    def clear_context(self):
        with self._lock:
            self.conversation_context = []

    # -------- Snapshot --------
    def get_snapshot(self):
        with self._lock:
            return {
                "current_mode": self.current_mode,
                "current_task": self.current_task,
                "task_goal": self.task_goal,
                "current_step": self.current_step,
                "planned_steps": list(self.planned_steps),
                "current_app": self.current_app,
                "last_action": self.last_action,
                "last_observation": self.last_observation,
                "last_tool_result": self.last_tool_result,
                "pending_confirmation": self.pending_confirmation,
                "task_status": self.task_status,
                "retry_count": self.retry_count,
                "conversation_context_len": len(self.conversation_context),
            }


# ---- Singleton ----
_state = AgentState()


def get_state():
    return _state


def reset_state():
    _state.reset()


if __name__ == "__main__":
    s = get_state()
    print("Initial mode:", s.get_mode())
    s.set_mode("listening")
    s.start_task("Chrome kholo", ["launch chrome"])
    s.record_action("open_app(chrome)")
    s.record_tool_result("Chrome opened")
    s.set_status("executing")
    s.add_to_context("user", "chrome kholo")
    print()
    print("Snapshot:")
    for k, v in s.get_snapshot().items():
        print(f"  {k}: {v}")
    s.complete_task()
    print()
    print("After complete:", s.get_snapshot()["task_status"])
    print("Mode still:", s.get_mode())
