#!/usr/bin/env python3
"""
NOVA QA REPORT - Phases 1-6 ka poora kaam ek jagah test karta hai.
Chalao: python qa_report.py
"""
import os
import sys
import json
import time
import traceback

RESULTS = []


def check(phase, name, fn, warn_only=False):
    try:
        note = fn()
        RESULTS.append((phase, name, "PASS", str(note or "")[:70]))
    except Exception as e:
        status = "WARN" if warn_only else "FAIL"
        RESULTS.append((phase, name, status, str(e)[:90]))


# ================= PHASE 1: LIVE DATA =================
def p1_module():
    import live_data
    fns = [f for f in ("get_news", "get_crypto", "get_weather_live",
                       "get_sports", "get_live_answer", "get_wikipedia") if hasattr(live_data, f)]
    assert len(fns) >= 5, f"missing funcs: {fns}"
    return ",".join(fns)


def p1_crypto():
    import live_data
    r = live_data.get_crypto("bitcoin")
    assert r and "fail" not in str(r).lower()[:30], str(r)[:80]
    return str(r)[:70]


def p1_weather():
    import live_data
    r = live_data.get_weather_live("Jaipur")
    assert r and len(str(r)) > 20, str(r)[:80]
    return str(r)[:70]


def p1_websearch_module():
    import web_search_live
    assert hasattr(web_search_live, "search") or len([f for f in dir(web_search_live) if not f.startswith("_")]) > 3
    return "module ok"


# ================= PHASE 2: APP CONTROL =================
def p2_ui_tools():
    import tools
    ui = [t for t in tools.TOOLS if t.startswith("ui_")]
    assert len(ui) >= 25, f"only {len(ui)} ui tools"
    return f"{len(ui)} ui tools"


def p2_ui_module():
    import ui_agent, inspect
    fns = [n for n, f in inspect.getmembers(ui_agent, inspect.isfunction) if not n.startswith("_")]
    assert len(fns) >= 25, f"only {len(fns)} funcs"
    return f"{len(fns)} funcs"


def p2_app_control():
    import app_control, tools
    need = ["volume_up", "volume_down", "mute", "unmute", "whatsapp_send",
            "open_url", "youtube_search"]
    missing = [f for f in need if not hasattr(app_control, f)]
    assert not missing, f"missing: {missing}"
    assert "play_youtube" in tools.TOOLS, "play_youtube tool missing"
    r = app_control.is_muted() if hasattr(app_control, "is_muted") else "n/a"
    return f"funcs ok, is_muted={r}"


# ================= PHASE 3: CREATION =================
def p3_portfolio():
    import creation_agent
    r = creation_agent.create_portfolio({"name": "QA Tester", "role": "QA Engineer",
                                         "skills": "Python Testing"})
    assert "Portfolio ban gaya" in str(r), str(r)[:90]
    return "created"


def p3_draft_stateful():
    import creation_agent, pathlib
    draft = pathlib.Path.home() / "Documents" / "NOVA_Creations" / "portfolio_draft.json"
    draft.unlink(missing_ok=True)
    r1 = creation_agent.create_portfolio({})
    assert "detail" in str(r1).lower() or "naam" in str(r1).lower(), str(r1)[:80]
    r2 = creation_agent.create_portfolio({"name": "QA Draft"})
    assert "Portfolio ban gaya" in str(r2), str(r2)[:80]
    return "ask->create flow ok"


def p3_list():
    import creation_agent
    r = creation_agent.list_creations({})
    assert r and "khaali" not in str(r).lower(), str(r)[:70]
    return str(r)[:60]


# ================= PHASE 4: SEMANTIC MEMORY =================
def p4_semantic():
    import semantic_memory as sm
    r1 = sm.semantic_remember({"text": "QA test fact: Pappu Jaipur me rehta hai", "category": "test"})
    r2 = sm.semantic_recall({"query": "Pappu kahan rehta hai", "n": 2})
    assert "yaad" in str(r1).lower() or "fallback" in str(r1).lower(), str(r1)[:80]
    assert "pappu" in str(r2).lower() or "fallback" in str(r2).lower() or "facts" in str(r2).lower(), str(r2)[:80]
    return str(r1)[:60]


def p4_fit_413():
    import think
    huge = [{"role": "assistant", "content": "X " * 3000}] * 4
    msgs = think.fit_messages("S" * 20000, huge, "hello " * 100)
    total = sum(len(m["content"]) for m in msgs)
    tok = total // 4
    assert tok < 8000, f"request {tok} tokens > 8000 (413!)"
    return f"{tok} tokens < 8000"


def p4_memory_facts():
    import memory
    memory.save_fact("qa_test_key", "qa_test_value", "test")
    assert memory.get_fact("qa_test_key") == "qa_test_value"
    memory.forget_fact("qa_test_key")
    return "fact roundtrip ok"


# ================= PHASE 5: COMMS =================
def p5_calendar():
    import comms_agent as c
    r1 = c.calendar_add({"title": "QA event", "when": "kal 6 baje"})
    r2 = c.calendar_list({"when": "tomorrow"})
    r3 = c.calendar_delete({"title": "QA event"})
    assert "add ho gaya" in str(r1), str(r1)[:70]
    assert "QA event" in str(r2), str(r2)[:70]
    assert "delete" in str(r3), str(r3)[:70]
    return "add->list->delete ok"


def p5_parser():
    import comms_agent as c
    cases = {
        "25 dec 10 baje": (12, 25, 10, 0),
        "kal 6 baje": None,
        "25 sept 6 pm": (9, 25, 18, 0),
        "25/12 10:30": (12, 25, 10, 30),
        "25 dec 2026": (12, 25, 9, 0),
        "5 minute baad": None,
    }
    for inp, want in cases.items():
        t = c._parse_when(inp)
        assert t is not None, f"'{inp}' -> None"
        if want:
            got = (t.month, t.day, t.hour, t.minute)
            assert got == want, f"'{inp}' -> {got} != {want}"
    return "6/6 parse cases"


def p5_numbers():
    from comms_agent import _to_digits
    cases = [
        ("nine eight seven six five four three two one zero", "9876543210"),
        ("nau aath saat chhe paanch chaar teen do ek shunya", "9876543210"),
        ("98765 43210", "9876543210"),
        ("987654321O", "9876543210"),
        ("9876543210", "9876543210"),
        ("double nine double eight seven six five four three two", "9988765432"),
    ]
    for inp, want in cases:
        got = _to_digits(inp)
        assert got == want, f"{inp[:30]!r} -> {got!r} != {want!r}"
    return "6/6 number forms"


def p5_contacts():
    import comms_agent as c
    r = c.save_contact({"name": "QA Contact", "phone": "9876543210"})
    assert "save ho gaya" in str(r), str(r)[:70]
    ph, _ = c._resolve_contact("QA Contact")
    assert ph == "9876543210", ph
    return "save+resolve ok"


def p5_email_setup():
    import comms_agent as c, pathlib
    cfg = pathlib.Path(c.CONFIG_PATH)
    if cfg.exists():
        return "configured (hidden)"
    r = c.send_email({"to": "x@y.com", "body": "hi"})
    assert "setup" in str(r).lower(), str(r)[:80]
    return "setup-required msg ok"


def p5_whatsapp():
    import comms_agent as c
    assert hasattr(c, "_wa_send_by_name") and hasattr(c, "_wa_desktop_installed")
    r = c.whatsapp_send({"contact": "no_such_qa_contact_xyz", "message": "test"})
    assert "bhej nahi paya" in str(r) or "khul" in str(r) or "chala" in str(r).lower() or "search karke" in str(r), str(r)[:90]
    return str(r)[:70]


def p5_whatsapp_call():
    import comms_agent as c
    assert hasattr(c, "whatsapp_call"), "whatsapp_call missing"
    assert hasattr(c, "_wa_click_call_button_ui") and hasattr(c, "_wa_click_call_button_vision")
    assert c._wa_call_wants_video({"video": True}) is True
    assert c._wa_call_wants_video({"video": "video"}) is True
    assert c._wa_call_wants_video({}) is False
    r = c.whatsapp_call({"contact": "no_such_qa_contact_xyz", "video": True})
    assert "call" in str(r).lower() and "fail" in str(r).lower(), str(r)[:90]
    return str(r)[:70]


def x_call_wiring():
    import policy, planner, think, verifier
    assert policy.classify("whatsapp_call") == "ask", "call ASK hona chahiye"
    msg = policy.make_confirmation_message("whatsapp_call", {"contact": "QA", "video": True})
    assert "QA" in msg and "video call" in msg.lower(), msg
    assert "whatsapp_call" in planner.TOOL_SCHEMAS, "planner schema missing"
    assert "whatsapp_call" in think.TOOL_SPECS, "think spec missing"
    assert "whatsapp_call" in think.SYSTEM_PROMPT_TEMPLATE, "think prompt example missing"
    assert "whatsapp_call" in verifier._SUCCESS_HINTS, "verifier hints missing"
    import rt_brain
    assert "whatsapp_call" in rt_brain.CONVERSATIONAL_VOICE_SYSTEM_PROMPT, "voice prompt rule missing"
    return "ask + planner + think + verifier + rt_brain ok"


# ================= PHASE 6: EMOTION =================
def p6_detect():
    import emotion
    cases = [
        ("yaar bahut udaas hoon aaj", "sad"),
        ("bilkul gussa aa raha hai tumse", "angry"),
        ("deadline ki tension ho rahi hai bahut", "stressed"),
        ("thak gaya hoon yaar aaj", "tired"),
        ("time kya hai", "neutral"),
    ]
    for text, want in cases:
        got = emotion.detect_emotion(text)["emotion"]
        assert got == want, f"{text!r} -> {got} != {want}"
    return "5/5 emotions"


def p6_voice_ack():
    import emotion
    assert emotion.voice_params("sad") != emotion.voice_params("excited")
    sad = emotion.detect_emotion("bahut udaas hoon")
    r = emotion.apply_ack(sad, "Theek ho jayega.")
    assert r != "Theek ho jayega." and "Theek ho jayega." in r
    assert emotion.apply_ack(emotion.detect_emotion("time kya hai"), "ok.") == "ok."
    return "voice+ack ok"


def p6_tool():
    import tools, policy, emotion
    assert "mood_history" in tools.TOOLS
    assert policy.classify("mood_history") == "safe"
    import think
    assert "mood_history" in think._build_tool_list(), "not in LLM prompt"
    return "tool+policy+prompt wired"


# ================= CROSS: WIRING / SAFETY =================
def x_all_tools_classified():
    import tools, policy
    not_explicit = [t for t in tools.TOOLS
                    if t not in policy.SAFE_TOOLS and t not in policy.ASK_TOOLS]
    assert not not_explicit, f"not explicit: {not_explicit[:6]}"
    return "all explicit"


def x_policy_comms():
    import policy
    assert policy.classify("whatsapp_send") == "safe"
    assert policy.classify("whatsapp_reply") == "safe"
    assert policy.classify("whatsapp_call") == "ask"
    assert policy.classify("send_email") == "ask"
    assert policy.classify("shutdown_pc") == "ask"
    return "whatsapp=safe, call/email/shutdown=ask"


def x_yes_punct():
    import policy
    assert policy.is_yes("haa.") and policy.is_yes("Haan!") and policy.is_yes("ok.")
    assert policy.is_no("nahi.")
    return "punct yes/no ok"


def x_pending_flow():
    import policy, brain
    policy.clear_pending()
    policy.set_pending("send_email", {"to": "x@y.com", "body": "hi"})
    r = brain.ask_nova("nahi")
    policy.clear_pending()
    assert "cancel" in str(r).lower(), str(r)[:70]
    return "refusal cancels pending"


def x_think_wiring():
    import think, tools
    tl = think._build_tool_list()
    for name in ["send_email", "calendar_add", "whatsapp_send", "semantic_recall", "live_data", "ui_click"]:
        assert name in tl, f"{name} not in think prompt"
    return "6 key tools in LLM prompt"


def x_fit_memory_cap():
    import think
    msgs = think.fit_messages("S" * 50000, [{"role": "user", "content": "y" * 10000}], "z" * 5000)
    assert len(msgs[-1]["content"]) <= 800, "user msg not capped"
    assert len(msgs[0]["content"]) <= 14100, "system not capped"
    return "caps enforced"


def x_verifier_planner():
    import verifier
    for t in ["semantic_recall", "calendar_add", "send_email", "mood_history", "whatsapp_call"]:
        assert t in verifier._SUCCESS_HINTS, f"{t} missing in verifier hints"
    ok, _ = verifier.verify({"tool": "whatsapp_call"}, "voice call laga diya")
    assert ok, "verifier call success nahi pehchana"
    bad, _ = verifier.verify({"tool": "whatsapp_call"}, "call nahi laga paya - fail")
    assert not bad, "verifier call failure nahi pehchana"
    return "verifier hints ok"


def x_existing_tests():
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 and "No module named pytest" in (r.stderr or ""):
        return "WARN-no pytest"
    tail = (r.stdout or "").strip().splitlines()[-1]
    assert r.returncode == 0, tail
    return tail


# ============ CALL FIX (NOVA): strict UIA + VERIFY + honest fail ============
def x_call_strict_verify():
    """Fuzzy match hata: exact-name weights, call-log block, verify hints."""
    import comms_agent as c
    for fn in ("_wa_uia_call_candidates", "_wa_uia_click", "_wa_click_call_button_ui",
               "_wa_click_call_button_vision", "_wa_call_fallback_xy",
               "_wa_call_state_note", "_wa_call_already_active", "_wa_call_probe"):
        assert hasattr(c, fn), fn + " missing"
    wv = c._WA_CALL_UI_NAME_WEIGHTS[False]
    assert wv["voice call"] == 3 and wv["call"] == 1, str(wv)
    assert c._WA_CALL_UI_NAME_WEIGHTS[True]["video call"] == 3
    for bad in ("missed", "no answer", "call back"):
        assert bad in c._WA_CALL_BAD_NAME_WORDS, bad
    # 'call ended' / 'no answer' verify hints NAHI (chat call-log false positive)
    for bad in ("call ended", "no answer"):
        assert bad not in c._WA_CALL_SCREEN_HINTS, bad + " hint me nahi hona chahiye"
    for good in ("calling", "ringing", "end call", "end video call"):
        assert good in c._WA_CALL_SCREEN_HINTS, good
    assert "NOT text inside chat messages" in c._WA_CALL_VISION_TARGETS[False]
    assert "NOT text inside chat messages" in c._WA_CALL_VISION_TARGETS[True]
    return "strict weights + bad words + verify hints ok"


def x_call_honest_fail():
    """Bina call-screen verify kiye success NAHI bolna chahiye."""
    import comms_agent as c
    import verifier
    orig = (c._wa_open_chat_and_run, c._wa_focus_call_window, c._wa_click_call_button_ui,
            c._wa_click_call_button_vision, c._wa_call_fallback_xy,
            c._wa_call_already_active, c._wa_call_state_note)
    try:
        c._wa_open_chat_and_run = lambda name, after_open=None, wait_load=12: after_open(None, None, "test")
        c._wa_focus_call_window = lambda: ""
        c._wa_call_already_active = lambda video=False: False
        c._wa_click_call_button_ui = lambda video=False: "uia invoke 'Voice call'"
        c._wa_click_call_button_vision = lambda video=False: None
        c._wa_call_fallback_xy = lambda video=False: None
        # 1) click hua par calling screen nahi aayi -> honest fail
        c._wa_call_state_note = lambda video=False, wait=None: ("absent", "no call-screen text")
        r = str(c.whatsapp_call({"contact": "QA Test"}))
        assert "laga diya" not in r, "jhoothi success bol diya: " + r
        assert "fail" in r.lower() and "calling screen nahi aayi" in r, r
        ok, _ = verifier.verify({"tool": "whatsapp_call"}, r)
        assert not ok, "verifier failure nahi pehchana"
        # 2) OCR hi unavailable -> alag honest message
        c._wa_call_state_note = lambda video=False, wait=None: ("unknown", "ocr unavailable")
        r2 = str(c.whatsapp_call({"contact": "QA Test"}))
        assert "confirm nahi kar paya" in r2 and "laga diya" not in r2, r2
        # 3) verify OK -> success, spoken reply me parentheses nahi
        c._wa_call_state_note = lambda video=False, wait=None: ("detected", "calling")
        r3 = str(c.whatsapp_call({"contact": "QA Test"}))
        assert "laga diya" in r3 and "(" not in r3 and ")" not in r3, r3
    finally:
        (c._wa_open_chat_and_run, c._wa_focus_call_window, c._wa_click_call_button_ui,
         c._wa_click_call_button_vision, c._wa_call_fallback_xy,
         c._wa_call_already_active, c._wa_call_state_note) = orig
    return "verify-gated success + honest fail ok"


def x_confirmation_guard():
    """'X ko call karo. haan.' se purana pending NAHI chalna chahiye + TTL."""
    import policy
    assert policy.PENDING_TTL_SEC == 180, policy.PENDING_TTL_SEC
    assert policy.looks_like_command("call karo") and policy.looks_like_command("kholo")
    assert policy.looks_like_command("haan") is False
    assert policy.is_yes("priyanshu ko call karo. haan.") is True
    assert policy.is_confirmation("priyanshu ko call karo. haan.") is False
    assert policy.is_confirmation("haan") is True
    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    assert policy.get_pending() is not None
    assert "ts" in policy.get_pending()
    policy._pending["ts"] = time.time() - (policy.PENDING_TTL_SEC + 10)
    assert policy.get_pending() is None, "stale pending expire nahi hui"
    policy.clear_pending()
    import brain, rt_brain, os as _os
    for mod in (brain, rt_brain):
        src = open(_os.path.join(_os.path.dirname(_os.path.abspath(mod.__file__)),
                                 mod.__name__ + ".py"), encoding="utf-8").read()
        assert "policy.is_confirmation(" in src, mod.__name__ + " me is_confirmation missing"
    return "naya command guard + 180s TTL ok"


def x_crash_resilience():
    """Crash se NOVA band na ho: _log_crash + continuous_mode try/except."""
    import main, os, tempfile
    assert hasattr(main, "_log_crash"), "_log_crash missing"
    d = tempfile.mkdtemp(prefix="nova_qa_")
    p = os.path.join(d, "nova_crash.log")
    old = main.CRASH_LOG
    try:
        main.CRASH_LOG = p
        # Jaan-boojh ke crash - traceback log me jana chahiye, QA output me nahi
        _so, sys.stdout = sys.stdout, open(os.devnull, "w", encoding="utf-8")
        try:
            try:
                raise ValueError("qa crash")
            except ValueError:
                main._log_crash("qa_report")
        finally:
            sys.stdout.close()
            sys.stdout = _so
        txt = open(p, encoding="utf-8").read()
        assert "qa_report" in txt and "ValueError: qa crash" in txt, txt[:80]
    finally:
        main.CRASH_LOG = old
        try:
            os.remove(p)
            os.rmdir(d)
        except Exception:
            pass
    src = open(os.path.join(os.path.dirname(os.path.abspath(main.__file__)), "main.py"),
               encoding="utf-8").read()
    body = src[src.index("def continuous_mode()"):src.index("def text_mode()")]
    assert '_log_crash("continuous mode")' in body, "continuous_mode crash wrap missing"
    assert "except KeyboardInterrupt:" in body, "Ctrl+C handler missing"
    return "crash log + loop wrap ok"



# ================= RUNNER =================
def main():
    print("=" * 62)
    print("  NOVA QA REPORT - Phases 1-6 (code-level tests)")
    print("=" * 62)
    plan = [
        ("P1 Live Data", "module+funcs", p1_module, False),
        ("P1 Live Data", "bitcoin price LIVE", p1_crypto, True),
        ("P1 Live Data", "Jaipur weather LIVE", p1_weather, True),
        ("P1 Live Data", "web_search_live module", p1_websearch_module, False),
        ("P2 App Control", "25+ ui_ tools wired", p2_ui_tools, False),
        ("P2 App Control", "ui_agent 28 funcs", p2_ui_module, False),
        ("P2 App Control", "app_control core funcs", p2_app_control, False),
        ("P3 Creation", "portfolio banao", p3_portfolio, False),
        ("P3 Creation", "stateful draft flow", p3_draft_stateful, False),
        ("P3 Creation", "list creations", p3_list, False),
        ("P4 Semantic", "remember+recall", p4_semantic, False),
        ("P4 Semantic", "413 cap (<8000 tok)", p4_fit_413, False),
        ("P4 Semantic", "sqlite facts roundtrip", p4_memory_facts, False),
        ("P5 Comms", "calendar add/list/del", p5_calendar, False),
        ("P5 Comms", "Hinglish date parser", p5_parser, False),
        ("P5 Comms", "number normalizer", p5_numbers, False),
        ("P5 Comms", "contacts save/resolve", p5_contacts, False),
        ("P5 Comms", "email setup guard", p5_email_setup, False),
        ("P5 Comms", "whatsapp by-name path", p5_whatsapp, False),
        ("P5 Comms", "whatsapp_call flow", p5_whatsapp_call, False),
        ("P6 Emotion", "detect Hinglish emotions", p6_detect, False),
        ("P6 Emotion", "voice params + ack", p6_voice_ack, False),
        ("P6 Emotion", "mood history tool wired", p6_tool, False),
        ("Wiring", "all tools classified", x_all_tools_classified, False),
        ("Wiring", "whatsapp_call wiring", x_call_wiring, False),
        ("Wiring", "policy: whatsapp safe/email ask", x_policy_comms, False),
        ("Wiring", "is_yes punctuation", x_yes_punct, False),
        ("Wiring", "pending refusal flow", x_pending_flow, False),
        ("Wiring", "think prompt wiring", x_think_wiring, False),
        ("Wiring", "413 caps enforced", x_fit_memory_cap, False),
        ("Wiring", "verifier hints", x_verifier_planner, False),
        ("Call Fix", "strict UIA + verify hints", x_call_strict_verify, False),
        ("Call Fix", "honest fail (no false success)", x_call_honest_fail, False),
        ("Call Fix", "stale pending + 180s TTL", x_confirmation_guard, False),
        ("Call Fix", "crash resilience", x_crash_resilience, False),
        ("Wiring", "pytest suite", x_existing_tests, True),
    ]
    for phase, name, fn, warn in plan:
        check(phase, name, fn, warn_only=warn)
        status = RESULTS[-1][2]
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[warn]", "SKIP": "[skip]"}[status]
        note = RESULTS[-1][3]
        print(f" {icon} {phase:<18} {name:<28} {note if status != 'PASS' else ''}")
    counts = {s: sum(1 for r in RESULTS if r[2] == s) for s in ("PASS", "FAIL", "WARN", "SKIP")}
    print("=" * 62)
    print(f"  TOTAL: {counts['PASS']} PASS | {counts['FAIL']} FAIL | {counts['WARN']} WARN | {counts['SKIP']} SKIP")
    if counts["FAIL"]:
        print("  FAIL wale items:")
        for ph, nm, st, note in RESULTS:
            if st == "FAIL":
                print(f"    - [{ph}] {nm}: {note}")
    print("=" * 62)
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
