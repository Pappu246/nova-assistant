# WhatsApp follow-up hardening

## Evidence vs. assumptions

The Windows report used Python 3.14, WhatsApp Desktop and 150% display scaling.
The real header controls were exact `Voice call` / `Video call` buttons and
already scored **14**. No call-name weights or `wa_call_names` behavior were
changed to fix this.

One lookup returned 79 repeated wrappers for the video button; the full tree
contained 8,596 descendants. Chat-history labels with durations/timestamps are
not exact names and must not be accepted. An `activate()` exception with Windows
error 0 was reported in a run that still had WhatsApp active-window OCR.

Different fresh processes produced logical GW bounds and physical UIA bounds;
loading pywinauto coincided with alignment in one process. This is **not a
confirmed root cause**. A first missing-window probe also does not establish why
the window was missing: subsequent fresh-process lookup succeeded.

## Safety and diagnostics

- Start/end-call candidates share one scanner. Identity is the UIA runtime ID
  when available, otherwise normalized name/type/rectangle. Distinct runtime
  IDs are never collapsed just because their rectangles match. A failed
  duplicate control does not consume the click retry budget repeatedly.
- Probes use one descendants snapshot, strict **raw/unique** counts, at most ten
  unique near-miss descriptions, window scores/rectangles, focus results and
  the appropriate start- or **END-call** weights/bad words.
- Enumeration, backend fallback and activation failures produce diagnostics;
  an empty result is not proof that WhatsApp was not installed or running.
- Foreground verification prefers matching HWNDs. An exact title is a fallback
  only when a handle is unavailable; it cannot override a known HWND mismatch.
  Activation success strings are not proof, and activation exceptions are not
  automatic failures: the actual foreground is checked in both cases.
- UIA `invoke()` stays coordinate-free. `click_input`, VLM and configured screen
  clicks require verified foreground. The VLM only locates (`dry_run=True`);
  foreground and unchanged window bounds are checked again before a real click.
- Windows screen work uses `SetThreadDpiAwarenessContext` with per-monitor-v2
  physical pixels, pointer-sized ctypes signatures and `finally` restoration.
  Both bounds retrieval and screenshot/click consumption run in that context.
  Nested contexts restore correctly. Setup failure skips screen work and makes
  OCR state **unknown**, never a fabricated call success or successful hang-up.
- No process-wide DPI setter or import-order workaround was added. Existing
  libraries may have their own process DPI defaults; the thread override does
  not depend on which one was imported first.
- Call/end-call offsets remain **disabled unless configured**, with exclusive
  right/bottom bounds checks. If configured locally, offsets are physical
  pixels. Do not copy personal config or contacts into Git.

The OCR verification chain, terminal-discard markers, call confirmation policy,
agent safeguard, successful-only dedup, pending TTL, planner rules, crash/segfault
fixes and barge-in tuning are unchanged. Shared chat opening also checks actual
foreground before typing and guards its web-search screen coordinates.

## Validation and fresh-process probes

Offline tests replay the reported coordinates and duplicate wrappers. Native
Windows CI tests check DPI scope nesting, exception restoration, unchanged
process awareness and isolation between threads, including on Python 3.14.
They do **not** make live calls or validate a real 150%-scaled WhatsApp desktop.
Process-default checks use `GetDpiAwarenessContextForProcess` with an explicit
process handle: the legacy `GetProcessDpiAwareness(NULL)` query is documented to
reflect the current thread, so it intentionally reports per-monitor awareness
inside the scope and cannot prove whether the process default changed.

After updating the local checkout, keep the desired WhatsApp chat open and run
from the repo directory (each command starts a fresh Python process):

```powershell
py -3.14 comms_agent.py --call-probe --video
```

Voice-header probe: omit `--video`. For an already-open call screen:

```powershell
py -3.14 comms_agent.py --end-call-probe
```

Probes may focus the window and read the screen but never click call controls.
Review/redact contact names and OCR text before sharing output.

**Actual Windows live-call start/end success remains unverified.**
