with open("agent_loop.py", "r", encoding="utf-8") as f:
    src = f.read()

# New complete agent_loop.py content
new_content = '''"""
NOVA Agent Loop - Execute multi-step tasks with observe/verify/replan.
"""
import time
import agent_state


MAX_RETRIES_PER_STEP = 2
MAX_REPLANS = 2


def _execute_single_step(step):
    """Execute a single step with retries. Returns (success, result, reason)."""
    import verifier
    from tools import TOOLS

    tool_name = step["tool"]
    args = step.get("args", {}) or {}

    last_result = None
    last_reason = ""

    for attempt in range(MAX_RETRIES_PER_STEP + 1):
        try:
            result = TOOLS[tool_name](args)
            last_result = result
            ok, reason = verifier.verify(step, result)
            last_reason = reason

            if ok:
                return True, result, reason
            print("[agent] Step " + str(step["step"]) + " retry " + str(attempt + 1) + ": " + reason)
        except Exception as e:
            last_reason = "exception: " + str(e)[:80]
            last_result = None
            print("[agent] Step " + str(step["step"]) + " exception: " + str(e)[:80])
        time.sleep(1)

    return False, last_result, last_reason


def _build_replan_context(all_results, failed_step, failure_reason):
    """Build human-readable context for the planner to replan."""
    lines = []
    lines.append("Previous attempt summary:")
    for r in all_results:
        status = r.get("status", "?").upper()
        lines.append("- Step " + str(r.get("step", "?")) + " (" + str(r.get("tool", "?")) + "): " + status)
        if r.get("status") == "failed":
            lines.append("    Failed reason: " + str(r.get("reason", "unknown"))[:80])

    lines.append("")
    lines.append("Failed step: " + str(failed_step.get("tool")) + " " + str(failed_step.get("args", {})))
    lines.append("Failure reason: " + str(failure_reason)[:100])
    lines.append("")
    lines.append("Instructions for the NEW plan:")
    lines.append("1. Do NOT repeat tool calls that already succeeded.")
    lines.append("2. Try a DIFFERENT approach for the failed step.")
    lines.append("3. If the goal is impossible, return an empty plan []. Otherwise, continue toward the goal.")
    return "\\n".join(lines)


def _filter_plan(plan):
    """Remove redundant open_app(chrome) if browse exists."""
    has_browse = any(s["tool"] == "browse" for s in plan)
    if has_browse:
        filtered = []
        for s in plan:
            if s["tool"] == "open_app":
                app = str(s.get("args", {}).get("app_name", "")).lower()
                if app in ("chrome", "browser", "edge", "firefox"):
                    print("[agent] Skipping open_app(" + app + ") - browse handles browser")
                    continue
            filtered.append(s)
        for i, s in enumerate(filtered, 1):
            s["step"] = i
        return filtered
    return plan


def run_task(goal, on_step=None):
    """Execute multi-step task with replanning. Returns final summary."""
    import planner
    import policy
    from tools import TOOLS

    state = agent_state.get_state()
    print("[agent] Goal: " + goal)
    state.start_task(goal)

    all_results = []
    replan_count = 0

    # First plan
    plan = planner.create_plan(goal, context=None)

    while True:
        if not plan:
            state.complete_task("failed")
            return "Boss, plan nahi bana paaya."

        plan = _filter_plan(plan)
        if not plan:
            state.complete_task("failed")
            return "Boss, plan ke saare steps skip ho gaye."

        print("[agent] Plan: " + str(len(plan)) + " steps")
        state.planned_steps = plan
        state.set_status("executing")

        failed_step = None
        failure_reason = ""

        for step in plan:
            state.set_step(step["step"])
            print("[agent] Step " + str(step["step"]) + "/" + str(len(plan)) + ": " + step["tool"] + " " + str(step.get("args", {})))

            if on_step:
                try:
                    on_step(step["step"], len(plan), step["tool"], step.get("description", ""))
                except Exception:
                    pass

            # Policy check
            if policy.is_blocked(step["tool"], step.get("args")):
                all_results.append({
                    "step": step["step"],
                    "tool": step["tool"],
                    "status": "failed",
                    "reason": "blocked by policy",
                    "result": "",
                })
                state.set_status("blocked")
                failed_step = step
                failure_reason = "blocked by policy"
                break

            if policy.requires_confirmation(step["tool"], step.get("args")):
                print("[agent] Step " + str(step["step"]) + " auto-approved (agent mode): " + step["tool"])

            # Execute with retries
            success, result, reason = _execute_single_step(step)
            state.record_action(step["tool"] + " " + str(step.get("args")))
            state.record_tool_result(result)

            all_results.append({
                "step": step["step"],
                "tool": step["tool"],
                "status": "success" if success else "failed",
                "reason": reason,
                "result": str(result)[:150] if result else "",
            })

            if success:
                print("[agent] Step " + str(step["step"]) + " OK: " + reason)
            else:
                print("[agent] Step " + str(step["step"]) + " FAILED: " + reason)
                failed_step = step
                failure_reason = reason
                break

        # All steps in this plan succeeded
        if failed_step is None:
            break

        # Try replanning
        if replan_count >= MAX_REPLANS:
            print("[agent] Max replans (" + str(MAX_REPLANS) + ") reached, giving up")
            break

        replan_count += 1
        print("[agent] Replanning (attempt " + str(replan_count) + "/" + str(MAX_REPLANS) + ")")
        state.increment_retry()

        context = _build_replan_context(all_results, failed_step, failure_reason)
        new_plan = planner.create_plan(goal, context=context)

        if not new_plan:
            print("[agent] Planner returned empty. Giving up.")
            break

        plan = new_plan

    # Build summary
    success_count = sum(1 for r in all_results if r["status"] == "success")
    failed_count = sum(1 for r in all_results if r["status"] == "failed")

    if failed_count == 0:
        state.complete_task("done")
        summary_lines = ["Boss, task complete."]
    else:
        state.complete_task("partial")
        summary_lines = ["Boss, task partly done."]

    summary_lines.append("Steps: " + str(success_count) + " OK, " + str(failed_count) + " fail.")

    for r in all_results:
        if r["status"] == "success":
            summary_lines.append("  OK: " + r["tool"])
        else:
            summary_lines.append("  FAIL: " + r["tool"] + " - " + str(r.get("reason", ""))[:50])

    return "\\n".join(summary_lines)


if __name__ == "__main__":
    print("Testing agent_loop imports...")
    import planner
    import verifier
    import agent_state
    print("All imports OK")
'''

with open("agent_loop.py", "w", encoding="utf-8") as f:
    f.write(new_content)
print("agent_loop.py rewritten with replanning")
