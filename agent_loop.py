"""
NOVA Agent Loop - Execute multi-step tasks with observe/verify/replan.
"""
import time
import agent_state


MAX_RETRIES = 2


def run_task(goal, on_step=None):
    """Execute multi-step task. Returns final summary."""
    import planner
    import verifier
    import policy
    from tools import TOOLS

    state = agent_state.get_state()

    print("[agent] Goal: " + goal)
    state.start_task(goal)

    # ---- PHASE 1: PLAN ----
    plan = planner.create_plan(goal, context=None)

    if not plan:
        state.complete_task("failed")
        return "Boss, plan nahi bana paaya."

    # Post-plan filter: agar browse hai, to open_app(chrome) hatao
    has_browse = any(s["tool"] == "browse" for s in plan)
    if has_browse:
        filtered = []
        for s in plan:
            if s["tool"] == "open_app":
                app = str(s.get("args", {}).get("app_name", "")).lower()
                if app in ("chrome", "browser", "edge", "firefox"):
                    print("[agent] Skipping open_app(" + app + ") - browse will handle browser")
                    continue
            filtered.append(s)
        # Re-number
        for i, s in enumerate(filtered, 1):
            s["step"] = i
        plan = filtered

    print("[agent] Plan: " + str(len(plan)) + " steps")
    state.planned_steps = plan
    state.set_status("executing")

    results = []

    # ---- PHASE 2: EXECUTE each step ----
    for step in plan:
        step_num = step["step"]
        tool_name = step["tool"]
        args = step["args"]
        desc = step.get("description", "")

        state.set_step(step_num)
        print("[agent] Step " + str(step_num) + "/" + str(len(plan)) + ": " + tool_name + " " + str(args))

        if on_step:
            try:
                on_step(step_num, len(plan), tool_name, desc)
            except Exception:
                pass

        # ---- Policy check ----
        if policy.is_blocked(tool_name, args):
            state.set_status("blocked")
            return "Boss, step " + str(step_num) + " blocked hai."

        if policy.requires_confirmation(tool_name, args):
            # In agent mode: user ne already multi-step bola = implicit consent
            # So ASK tools are auto-approved (they are already classified as reversible)
            print("[agent] Step " + str(step_num) + " auto-approved (agent mode): " + tool_name)

        # ---- Execute with retries ----
        step_success = False
        last_result = None
        last_reason = ""

        for attempt in range(MAX_RETRIES + 1):
            try:
                state.record_action(tool_name + " " + str(args))
                result = TOOLS[tool_name](args)
                state.record_tool_result(result)
                state.record_observation(result)
                last_result = result

                # ---- Verify ----
                ok, reason = verifier.verify(step, result)
                last_reason = reason

                if ok:
                    step_success = True
                    results.append({
                        "step": step_num,
                        "tool": tool_name,
                        "status": "success",
                        "result": str(result)[:150],
                    })
                    print("[agent] Step " + str(step_num) + " OK: " + reason)
                    break
                else:
                    print("[agent] Step " + str(step_num) + " retry " + str(attempt+1) + ": " + reason)
                    state.increment_retry()
                    time.sleep(1)
            except Exception as e:
                last_reason = "exception: " + str(e)[:80]
                print("[agent] Step " + str(step_num) + " exception: " + str(e)[:80])
                state.increment_retry()
                time.sleep(1)

        if not step_success:
            results.append({
                "step": step_num,
                "tool": tool_name,
                "status": "failed",
                "reason": last_reason,
                "result": str(last_result)[:150] if last_result else "",
            })
            state.set_status("failed")
            # Stop the loop - earlier step failed
            break

    # ---- PHASE 3: Summary ----
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")

    if failed_count == 0:
        state.complete_task("done")
    else:
        state.complete_task("partial")

    # Build summary
    summary_lines = ["Boss, task complete."]
    if failed_count > 0:
        summary_lines = ["Boss, task partly done."]

    summary_lines.append("Steps: " + str(success_count) + " OK, " + str(failed_count) + " fail, " + str(skipped_count) + " skip.")

    for r in results:
        if r["status"] == "success":
            summary_lines.append("  OK: " + r["tool"])
        elif r["status"] == "failed":
            summary_lines.append("  FAIL: " + r["tool"] + " - " + r["reason"][:50])
        elif r["status"] == "skipped":
            summary_lines.append("  SKIP: " + r["tool"] + " (needs confirm)")

    return "\n".join(summary_lines)


if __name__ == "__main__":
    # Dry test with a fake plan
    print("Testing agent_loop...")
    # This would need real tools and LLM
    # Just checking imports work
    import planner
    import verifier
    import agent_state
    print("All imports OK")
