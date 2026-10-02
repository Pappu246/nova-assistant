# -*- coding: utf-8 -*-
# NOVA Segfault Fix (mini patcher) - October 2026
# ------------------------------------------------------------
# Problem: rt_main.py Voice Barge-In par "Segmentation fault"
# Root cause:
#   1) rt_speak.stop_speaking() mein sd.stop() tha - ise BARGE-IN
#      MONITOR THREAD call karta tha, jabki playback worker thread
#      bhi sd.play/sd.stop (sounddevice ka GLOBAL player) chhed
#      raha tha. Do threads ka global player race -> Windows
#      PortAudio C-level crash.
#   2) rt_speak._play() mein sd.get_stream() (global) tha.
#   3) rt_listen.stop_barge_in_monitor() monitor thread ka JOIN
#      nahi lete the - purani mic stream band hone se pehle nayi
#      khul jaati thi (dual InputStream crash).
#
# Usage:  python fix_crash.py     (NOVA repo root me chalana)
# Backup: nova_backup_<timestamp>/ folder me automatic banega.
# Ye script IDEMPOTENT hai - dobara chalane se kuch nahi bigadta.
# ------------------------------------------------------------
import os
import re
import shutil
import datetime
import py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
MARK = "SEGFAULT FIX (NOVA)"

_bdir = None


def read(fname):
    with open(os.path.join(ROOT, fname), "r", encoding="utf-8") as f:
        return f.read()


def write(fname, content):
    with open(os.path.join(ROOT, fname), "w", encoding="utf-8") as f:
        f.write(content)


def backup(fname):
    global _bdir
    if _bdir is None:
        _bdir = os.path.join(
            ROOT, "nova_backup_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(_bdir, exist_ok=True)
    dst = os.path.join(_bdir, fname)
    if not os.path.exists(dst):
        shutil.copy2(os.path.join(ROOT, fname), dst)


def ok_compile(fname):
    try:
        py_compile.compile(os.path.join(ROOT, fname), doraise=True)
        return True
    except Exception as e:
        print("[FAIL] " + fname + " syntax error! backup restore karo - " + str(e)[:60])
        try:
            shutil.copy2(os.path.join(_bdir, fname), os.path.join(ROOT, fname))
        except Exception:
            pass
        return False


def replace_func(src, name, new_text):
    """Column-0 'def name(...)' function ko new_text se replace karo."""
    m = re.search(r"(?ms)^def " + name + r"\(.*?(?=^def |^if __name__|\Z)", src)
    if not m:
        return None
    return src[:m.start()] + new_text + "\n\n\n" + src[m.end():]


# ============================================================
# FIX 1 + 2: rt_speak.py
# ============================================================
def patch_rt_speak():
    try:
        s = read("rt_speak.py")
    except FileNotFoundError:
        print("[SKIP] rt_speak.py - file nahi mili")
        return

    if MARK in s:
        print("[OK]   rt_speak.py - already patched")
        return

    changed = []

    # --- FIX 1: stop_speaking() se cross-thread sd.stop() hatao ---
    old1 = ("    _do_stop()\n"
            "    try:\n"
            "        if _SD:\n"
            "            sd.stop()\n"
            "    except Exception:\n"
            "        pass\n"
            "    _speaking_flag.clear()")
    new1 = ("    _do_stop()\n"
            "    # " + MARK + ": global sounddevice stop yahan se kabhi NAHI\n"
            "    # hota - barge-in monitor thread se global player touch karna\n"
            "    # hi Windows PortAudio crash tha. Worker apni stream khud\n"
            "    # band kar deta hai (~30ms).\n"
            "    _speaking_flag.clear()")
    if old1 in s:
        s = s.replace(old1, new1, 1)
        changed.append("stop_speaking: sd.stop removed")
    else:
        s2, n = re.subn(
            r"\n    try:\n        if _SD:\n            sd\.stop\(\)\n"
            r"    except Exception:\n        pass\n", "\n", s, count=1)
        if n:
            s = s2
            changed.append("stop_speaking: sd.stop removed (regex)")
        else:
            print("[SKIP] rt_speak.py - stop_speaking pattern match nahi hua")

    # --- FIX 2: _play() mein global get_stream access hatao ---
    old2 = ("        sd.play(data, sr)\n"
            "        stream = sd.get_stream()\n"
            "        while stream is not None and stream.active:\n"
            "            if _stop_flag.is_set():\n"
            "                sd.stop()\n"
            "                break\n"
            "            time.sleep(0.02)")
    new2 = ("        # " + MARK + ": global stream handle access hata diya -\n"
            "        # duration-based wait. Stop sirf isi worker thread se.\n"
            "        sd.play(data, sr)\n"
            "        duration = len(data) / float(sr)\n"
            "        start_t = time.time()\n"
            "        while (time.time() - start_t) < duration:\n"
            "            if _stop_flag.is_set():\n"
            "                break\n"
            "            time.sleep(0.03)\n"
            "        try:\n"
            "            sd.stop()\n"
            "        except Exception:\n"
            "            pass")
    if old2 in s:
        s = s.replace(old2, new2, 1)
        changed.append("_play: get_stream removed")
    else:
        print("[SKIP] rt_speak.py - _play pattern match nahi hua")

    if changed:
        backup("rt_speak.py")
        write("rt_speak.py", s)
        if ok_compile("rt_speak.py"):
            for c in changed:
                print("[PATCH] rt_speak.py - " + c)


# ============================================================
# FIX 3 + 4: rt_listen.py
# ============================================================
NEW_STOP = '''def stop_barge_in_monitor():
    """Stop barge-in monitor and return any audio captured during interruption.

    """ + "SEGFAULT FIX (NOVA): monitor thread apni InputStream finally block" + """
    me khud band karta hai - yahan JOIN lete hain taaki stream 100% band ho,
    tabhi listen_vad nayi kholta hai (dual-InputStream crash fix).
    """
    global _barge_in_active, _barge_in_thread, _barge_in_audio_captured
    _barge_in_active = False
    if _barge_in_thread is not None and _barge_in_thread.is_alive():
        for _ in range(6):
            try:
                _barge_in_thread.join(timeout=0.25)
            except Exception:
                pass
            if not _barge_in_thread.is_alive():
                break
    _barge_in_thread = None
    captured = _barge_in_audio_captured
    _barge_in_audio_captured = None
    return captured'''


def patch_rt_listen():
    try:
        s = read("rt_listen.py")
    except FileNotFoundError:
        print("[SKIP] rt_listen.py - file nahi mili")
        return

    if MARK in s:
        print("[OK]   rt_listen.py - already patched")
        return

    changed = []

    # --- FIX 3: stop_barge_in_monitor join ke saath ---
    s2 = replace_func(s, "stop_barge_in_monitor", NEW_STOP)
    if s2:
        s = s2
        changed.append("stop_barge_in_monitor: join added")

    # --- FIX 4: listen_vad shuru me purana monitor pakka band ho ---
    old4 = ("    if not _SD:\n"
            "        return None, 0\n"
            "\n"
            "    model = _load_vad()")
    new4 = ("    if not _SD:\n"
            "        return None, 0\n"
            "\n"
            "    # " + MARK + ": purana barge-in monitor join karke band karo,\n"
            "    # phir hi nayi InputStream open karo (dual-open crash fix)\n"
            "    try:\n"
            "        stop_barge_in_monitor()\n"
            "    except Exception:\n"
            "        pass\n"
            "\n"
            "    model = _load_vad()")
    if old4 in s:
        s = s.replace(old4, new4, 1)
        changed.append("listen_vad: defensive monitor stop")

    if changed:
        backup("rt_listen.py")
        write("rt_listen.py", s)
        if ok_compile("rt_listen.py"):
            for c in changed:
                print("[PATCH] rt_listen.py - " + c)
    elif MARK not in s:
        print("[SKIP] rt_listen.py - patterns match nahi hue")


# ============================================================
# VERIFY
# ============================================================
def verify():
    print("\n--- VERIFY ---")
    good = True
    try:
        s_sp = read("rt_speak.py")
        s_li = read("rt_listen.py")
        checks = [
            ("stop_speaking me sd.stop nahi",
             "def stop_speaking" in s_sp and "sd.stop" not in s_sp.split("def stop_speaking")[1].split("def ")[0]),
            ("_play me get_stream nahi",
             "get_stream" not in s_sp),
            ("stop_barge_in_monitor join karta hai",
             "join" in s_li.split("def stop_barge_in_monitor")[1][:900]),
        ]
        for name, okk in checks:
            print(("  [PASS] " if okk else "  [FAIL] ") + name)
            good = good and okk
    except Exception as e:
        print("  [WARN] verify fail:", str(e)[:70])
        good = False
    return good


def main():
    print("=" * 60)
    print("  NOVA Segfault Fix (mini patcher)")
    print("=" * 60)
    if not os.path.exists(os.path.join(ROOT, "rt_main.py")):
        print("\n[ERROR] rt_main.py nahi mili - ye script NOVA repo root")
        print("me rakhi aur chalai jaati hai (jahan rt_main.py hai).")
        return
    patch_rt_speak()
    patch_rt_listen()
    if _bdir:
        print("\nBackup folder: " + os.path.basename(_bdir) + "/")
    if verify():
        print("\n>>> SEGFAULT FIX LAG GAYA! Ab test karo:  python rt_main.py")
        print(">>> (Barge-in karo - ab crash nahi aana chahiye)")
    else:
        print("\n>>> Kuch checks fail - ye output Arena chat me bhej dena.")


if __name__ == "__main__":
    main()
