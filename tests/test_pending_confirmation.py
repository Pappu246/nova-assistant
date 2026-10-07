"""
STALE PENDING + CRASH RESILIENCE tests (NOVA).

Do real bugs cover hote hain:

1) PURANI CONFIRMATION ZINDA REH JATI THI
   NOVA: "whatsapp kholna hai? Haan ya nahi bolo."   (pending open_app)
   Boss: "priyanshu ko call karo. haan."
   -> 'haan' match hoke PURANA open_app chal jata tha, call command gayab.
   Ab policy.is_confirmation() naya command detect karta hai aur pending
   execute nahi hoti; saath hi pending 3 min (PENDING_TTL_SEC) me expire hoti hai.

2) CRASH SE NOVA BAND HO JATA THA
   continuous_mode() ke ek turn ka exception poora loop tod deta tha.
   Ab main._log_crash() traceback nova_crash.log me likhta hai aur loop chalta
   rehta hai.
"""
import sys
import time
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import policy


# ================= policy.looks_like_command / is_confirmation =================

@pytest.mark.parametrize("text", [
    "call karo", "call lagao", "call kar do", "video call", "voice call",
    "phone karo", "kholo", "khol do", "open karo", "chala do",
    "message karo", "message bhejo", "bhejo", "send karo",
    "bajao", "chalao", "play karo", "search karo", "google karo",
    "dikhao", "banao", "band karo", "close karo", "type karo",
    "lagao", "laga do", "remind karo", "yaad dila",
])
def test_every_command_pattern_detected(text):
    assert policy.looks_like_command(text) is True, text


@pytest.mark.parametrize("text", [
    "haan", "haan.", "ha", "yes", "ok", "okay", "theek", "sure",
    "chalega", "theek hai", "kar do haan",
])
def test_plain_yes_is_not_a_command(text):
    assert policy.looks_like_command(text) is False, text


@pytest.mark.parametrize("text", [
    "haan", "haan.", "Haan!", "yes", "ok", "theek hai", "sure", "chalega",
])
def test_is_confirmation_true_for_plain_yes(text):
    assert policy.is_confirmation(text) is True, text


@pytest.mark.parametrize("text", [
    "priyanshu ko call karo. haan.",
    "whatsapp kholo haan",
    "Pinkesh ko video call karo haan",
    "chrome khol do haan",
    "message bhejo haan",
    "spotify chalao haan",
    "yaad dila dena haan",
])
def test_is_confirmation_false_when_new_command_present(text):
    """'haan' + naya command = confirmation NAHI (purana pending nahi chalega)."""
    assert policy.is_yes(text) is True, "is_yes to True hona chahiye: " + text
    assert policy.looks_like_command(text) is True, text
    assert policy.is_confirmation(text) is False, text


def test_is_confirmation_signature_accepts_pending():
    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    p = policy.get_pending()
    assert policy.is_confirmation("haan", p) is True
    assert policy.is_confirmation("priyanshu ko call karo. haan.", p) is False
    policy.clear_pending()


def test_is_no_still_works_for_commands():
    assert policy.is_no("nahi") is True
    assert policy.is_no("priyanshu ko call karo. haan.") is False


def test_empty_text_is_not_confirmation():
    assert policy.is_confirmation("") is False
    assert policy.looks_like_command("") is False


# ================= pending TTL =================

def test_set_pending_stores_timestamp():
    policy.clear_pending()
    before = time.time()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    p = policy.get_pending()
    assert p is not None and "ts" in p, p
    assert p["ts"] >= before
    policy.clear_pending()


def test_pending_ttl_constant():
    assert policy.PENDING_TTL_SEC == 180


def test_fresh_pending_is_returned():
    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    assert policy.get_pending()["tool"] == "open_app"
    policy.clear_pending()


def test_stale_pending_expires_and_clears():
    """3 min se purani pending expire + clear honi chahiye."""
    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    policy._pending["ts"] = time.time() - (policy.PENDING_TTL_SEC + 20)
    assert policy.get_pending() is None
    # clear bhi ho gaya (dobara set na karna pade)
    assert policy._pending == {}
    policy.clear_pending()


def test_pending_just_inside_ttl_still_valid():
    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    policy._pending["ts"] = time.time() - (policy.PENDING_TTL_SEC - 30)
    assert policy.get_pending() is not None
    policy.clear_pending()


def test_pending_without_ts_still_works():
    """Purane pickled/legacy pending me ts na ho to crash nahi hona chahiye."""
    policy.clear_pending()
    policy._pending["tool"] = "open_app"
    policy._pending["args"] = {"app_name": "whatsapp"}
    assert policy.get_pending()["tool"] == "open_app"
    policy.clear_pending()


def test_real_clock_expiry(monkeypatch):
    """time.time() aage badhao -> pending expire."""
    policy.clear_pending()
    policy.set_pending("whatsapp_call", {"contact": "Pinkesh"})
    base = time.time()
    monkeypatch.setattr(policy.time, "time", lambda: base + 400)
    assert policy.get_pending() is None
    policy.clear_pending()


# ================= BRAIN: purana pending naya command pe NAHI chale ===========

def _stub_think_call(monkeypatch, contact="Priyanshu"):
    import brain
    seen = []

    def _fake_think(msg, history=None, **kw):
        seen.append(msg)
        return {"mode": "tool", "tool": "whatsapp_call", "args": {"contact": contact}}

    monkeypatch.setattr(brain, "think", _fake_think)
    return seen


def test_brain_new_command_with_haan_ignores_stale_pending(monkeypatch):
    """REAL BUG: pending open_app + 'priyanshu ko call karo. haan.'
    -> open_app NAHI chalna chahiye, naya call command chale."""
    import brain
    import tools

    opened, called = [], []
    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: opened.append(dict(a)) or "whatsapp khol diya")
    monkeypatch.setitem(tools.TOOLS, "whatsapp_call",
                        lambda a: called.append(dict(a)) or "call laga diya")
    _stub_think_call(monkeypatch)

    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})

    r = str(brain.ask_nova("priyanshu ko call karo. haan."))

    assert not opened, "PURANA open_app chal gaya - bug wapas aa gaya! " + str(opened)
    # Naya call command ASK tool hai -> confirm maanga jayega
    assert policy.get_pending()["tool"] == "whatsapp_call", str(policy.get_pending())
    assert "Priyanshu" in r and "call" in r.lower(), r
    policy.clear_pending()


def test_brain_plain_haan_runs_pending(monkeypatch):
    """Sirf 'haan' bolo -> pending open_app chale (purana behaviour preserve)."""
    import brain
    import tools

    opened = []
    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: opened.append(dict(a)) or "whatsapp khol diya")
    _stub_think_call(monkeypatch)

    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})

    r = str(brain.ask_nova("haan"))
    assert opened == [{"app_name": "whatsapp"}], opened
    assert "khol diya" in r, r
    assert policy.get_pending() is None


def test_brain_stale_pending_ttl_expiry(monkeypatch):
    """Pending expire ho gayi -> 'haan' pe purana tool NAHI chale."""
    import brain
    import tools

    opened = []
    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: opened.append(dict(a)) or "whatsapp khol diya")
    monkeypatch.setattr(brain, "think",
                        lambda msg, history=None, **kw: {"mode": "chat", "reply": "Haan Boss?"})

    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    policy._pending["ts"] = time.time() - (policy.PENDING_TTL_SEC + 30)

    r = str(brain.ask_nova("haan"))
    assert not opened, "Expired pending chal gayi!"
    assert r == "Haan Boss?", r


def test_brain_pending_whatsapp_call_same_command_repeats(monkeypatch):
    """Pending call + wahi call command dobara -> call chale (special case preserve)."""
    import brain
    import tools

    called = []
    monkeypatch.setitem(tools.TOOLS, "whatsapp_call",
                        lambda a: called.append(dict(a)) or "call laga diya")
    _stub_think_call(monkeypatch)

    policy.clear_pending()
    policy.set_pending("whatsapp_call", {"contact": "Pinkesh", "video": False})
    r = str(brain.ask_nova("Pinkesh ko call karo"))
    assert called == [{"contact": "Pinkesh", "video": False}], called
    assert policy.get_pending() is None


def test_brain_nahi_cancels_pending(monkeypatch):
    import brain
    import tools

    opened = []
    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: opened.append(a) or "khol diya")
    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    r = str(brain.ask_nova("nahi"))
    assert not opened
    assert "cancel" in r.lower(), r
    assert policy.get_pending() is None


# ================= RT_BRAIN: same bug, voice path =============================

class _FakeResp:
    def __init__(self, content):
        msg = type("M", (), {"content": content})()
        self.choices = [type("C", (), {"message": msg})()]


class _FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kw):
        return _FakeResp(self.content)


def _stub_groq(monkeypatch, content):
    import rt_brain
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(rt_brain, "_GROQ", True)
    monkeypatch.setattr(rt_brain, "Groq",
                        lambda api_key=None: type("C", (), {
                            "chat": type("Ch", (), {"completions": _FakeCompletions(content)})()
                        })(), raising=False)


def test_rt_brain_new_command_with_haan_ignores_stale_pending(monkeypatch):
    import rt_brain
    import tools

    opened = []
    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: opened.append(dict(a)) or "whatsapp khol diya")
    _stub_groq(monkeypatch,
               '{"mode": "tool", "tool": "whatsapp_call", "args": {"contact": "Priyanshu"}}')

    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})

    out = [t for k, t in rt_brain.stream_reply("priyanshu ko call karo. haan.", [])]
    assert not opened, "PURANA open_app chal gaya! " + str(opened)
    assert policy.get_pending()["tool"] == "whatsapp_call", str(policy.get_pending())
    assert "Priyanshu" in out[-1], str(out)
    policy.clear_pending()


def test_rt_brain_plain_haan_runs_pending(monkeypatch):
    import rt_brain
    import tools

    opened = []
    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: opened.append(dict(a)) or "whatsapp khol diya")
    _stub_groq(monkeypatch, '{"mode": "chat", "reply": "Haan Boss?"}')

    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    out = [t for k, t in rt_brain.stream_reply("haan", [])]
    assert opened == [{"app_name": "whatsapp"}], opened
    assert "khol diya" in out[-1], str(out)
    assert policy.get_pending() is None


def test_rt_brain_stale_pending_ttl_expiry(monkeypatch):
    import rt_brain
    import tools

    opened = []
    monkeypatch.setitem(tools.TOOLS, "open_app",
                        lambda a: opened.append(dict(a)) or "whatsapp khol diya")
    _stub_groq(monkeypatch, '{"mode": "chat", "reply": "Haan Boss?"}')

    policy.clear_pending()
    policy.set_pending("open_app", {"app_name": "whatsapp"})
    policy._pending["ts"] = time.time() - (policy.PENDING_TTL_SEC + 30)

    out = [t for k, t in rt_brain.stream_reply("haan", [])]
    assert not opened, "Expired pending chal gayi!"
    assert out[-1] == "Haan Boss?", str(out)


def test_rt_brain_uses_is_confirmation_not_is_yes():
    """Regression guard: rt_brain/brain me seedha is_yes wapas nahi aana chahiye."""
    import io
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fname in ("brain.py", "rt_brain.py"):
        src = io.open(os.path.join(root, fname), encoding="utf-8").read()
        assert "policy.is_confirmation(" in src, fname + " me is_confirmation missing"
        assert "policy.is_yes(" not in src, fname + " me purana policy.is_yes( wapas aa gaya"


# ================= MAIN: crash resilience =====================================

class _FakeSuno:
    """suno.listen_continuous jaisa - scripted utterances deta hai."""
    script = []

    @classmethod
    def listen_continuous(cls, chunk_sec=3.0):
        if cls.script:
            return cls.script.pop(0), True
        return "bye", True

    @staticmethod
    def listen_for_stop(ev, timeout_sec=90):
        try:
            ev.set()
        except Exception:
            pass


def _prep_main(monkeypatch, tmp_path, ask_nova):
    import main

    _FakeSuno.script = ["pehla kaam", "doosra kaam", "bye"]
    monkeypatch.setitem(sys.modules, "suno", _FakeSuno)
    monkeypatch.setitem(sys.modules, "reminders",
                        type("R", (), {"start_watcher": staticmethod(lambda cb: None)}))
    monkeypatch.setattr(main, "ask_nova", ask_nova)
    monkeypatch.setattr(main, "_HUD", False)
    monkeypatch.setattr(main, "start_esc_listener", lambda *a, **k: None)
    monkeypatch.setattr(main, "speak_with_interrupt", lambda t: None)
    monkeypatch.setattr(main, "_text_input_reader", lambda: None)
    log = tmp_path / "nova_crash.log"
    monkeypatch.setattr(main, "CRASH_LOG", str(log))
    return main, log


def test_continuous_mode_survives_exception(monkeypatch, tmp_path):
    """Ek turn crash ho to NOVA band NAHI hona chahiye - agla turn chale."""
    done = []

    def _ask(text, history=None):
        if text == "pehla kaam":
            raise RuntimeError("boom")
        done.append(text)
        return "ok"

    main, log = _prep_main(monkeypatch, tmp_path, _ask)
    main.continuous_mode()

    assert done == ["doosra kaam"], "crash ke baad loop ruk gaya: " + str(done)
    assert log.exists(), "nova_crash.log bana hi nahi"
    content = log.read_text(encoding="utf-8")
    assert "continuous mode" in content, content
    assert "RuntimeError: boom" in content, content


def test_log_crash_writes_traceback(monkeypatch, tmp_path):
    import main
    log = tmp_path / "nova_crash.log"
    monkeypatch.setattr(main, "CRASH_LOG", str(log))
    try:
        raise ValueError("test crash")
    except ValueError:
        main._log_crash("unit test")
    content = log.read_text(encoding="utf-8")
    assert "unit test" in content and "ValueError: test crash" in content, content
    assert "Traceback" in content, content


def test_log_crash_appends_not_overwrites(monkeypatch, tmp_path):
    import main
    log = tmp_path / "nova_crash.log"
    monkeypatch.setattr(main, "CRASH_LOG", str(log))
    for i in (1, 2):
        try:
            raise RuntimeError("crash %d" % i)
        except RuntimeError:
            main._log_crash("loop")
    content = log.read_text(encoding="utf-8")
    assert "crash 1" in content and "crash 2" in content, content


def test_crash_log_is_gitignored():
    """nova_crash.log public repo me commit NAHI hona chahiye."""
    import io
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gi = io.open(os.path.join(root, ".gitignore"), encoding="utf-8-sig").read()
    assert "nova_crash.log" in gi or "*.log" in gi, gi


def test_continuous_loop_body_is_wrapped():
    """Regression guard: continuous_mode ka while body try/except me rahe."""
    import io
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(root, "main.py"), encoding="utf-8").read()
    body = src[src.index("def continuous_mode()"):src.index("def text_mode()")]
    assert "_log_crash(\"continuous mode\")" in body, "crash handler missing"
    assert "except KeyboardInterrupt:" in body, "Ctrl+C handler missing"
    assert "except Exception:" in body, "generic crash handler missing"
