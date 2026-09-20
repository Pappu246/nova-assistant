with open("agent_loop.py", "r", encoding="utf-8") as f:
    src = f.read()

# Add post-plan filter
old_start = '''    print("[agent] Plan: " + str(len(plan)) + " steps")
    state.planned_steps = plan
    state.set_status("executing")'''

new_start = '''    # Post-plan filter: agar browse hai, to open_app(chrome) hatao
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
    state.set_status("executing")'''

if old_start in src:
    src = src.replace(old_start, new_start)
    with open("agent_loop.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("agent_loop.py updated")
else:
    print("Pattern not found")
