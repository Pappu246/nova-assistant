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

## Name-based chat verification

Used by `whatsapp_send` (no phone number saved) and `whatsapp_call`. Both open the
chat by name, so both must prove they are in the right chat first.

- **Open:** Ctrl+F, then Ctrl+A and Backspace. The search box UIA value must be
  empty before the name is pasted, and must equal the name before Enter. Any
  miss returns without Enter, typing or clicks. Esc is no longer pressed: the
  global Esc listeners in `bolo.py` and `rt_speak.py` would stop NOVA's speech.
- **Header:** after Enter, the chat header must EXACTLY match the target (case and
  whitespace normalised; no partial match). The UIA header band is checked
  first, then OCR of the same band. A phone-number target compares the last 10
  digits. Unknown counts as a mismatch.
- **Message:** the header is checked again before Enter. Enter is pressed only
  when the composer UIA text shows the message (when readable). The reply says
  "bhej diya" only after the composer is empty again. If the composer cannot be
  read, the reply says the send was not verified.
- **Call start:** the header is checked before the click, and again after a call
  hint is seen. A header that changed stops further clicks. "absent" after a click
  means "not verified", never success.
- **Call end:** OCR "absent" is not proof of "no call". "Koi call nahi" needs
  positive proof: exactly one visible WhatsApp window (title or owner process
  says WhatsApp, so a call window titled with the contact's name still counts),
  not call-titled, showing the chat search or composer box, and with no strict
  End-call control in its UIA tree. Without proof, only the UIA End button is
  tried; if that is not possible the reply is "call state verify nahi hua".
  Vision and coordinate clickers run only after a detected call.
- **Auto-send:** name-based messages are sent by default after verification.
  `auto_send: false` types the message and leaves Enter to the user.

OCR regions: an off-screen or partly off-screen window is clamped to its visible
part instead of skipped (a maximized Windows 10/11 window reports -8,-8). A
fully minimized window (-32000) still gives no region. The custom OCR crop width
is recomputed from the clamped edges, and a custom region that cannot be
captured returns nothing instead of the full screen. The probe output is
cp1252-safe, so piping it to a file no longer crashes.

Limits (not verified on Windows): the search box, composer and header must
expose readable UIA values or text in the header band. If they do not, NOVA
blocks the action. Two contacts with the exact same name are not told apart: the
first search result is opened, and the header check only confirms the title.
The header band and layout constants assume the default WhatsApp Desktop layout.
A call window whose title and owner process are both not WhatsApp cannot be seen
by the "no call" proof; the call-recipient check on the Calls tab stays the final
verification.

## Validation and fresh-process probes

Offline tests replay the reported coordinates and duplicate wrappers. Native
Windows CI tests check DPI scope nesting, exception restoration, unchanged
process awareness and isolation between threads, including on Python 3.14.
They do **not** make live calls or validate a real 150%-scaled WhatsApp desktop.
Process-default checks use an independent observer and
`GetDpiAwarenessContextForProcess` with a real handle to the test process.
Current-process shortcuts can reflect the caller's thread override (observed
on CI even with `GetCurrentProcess()`); `GetProcessDpiAwareness(NULL)` is also
documented in terms of the current thread. Neither is a reliable process-default
measurement inside the scope. The observer checks before, during and after it.

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

Chat-open verification, read-only (focuses the window; never types or clicks):

```powershell
py -3.14 comms_agent.py --chat-probe
```

It prints the header names the verifier can see, whether the search box and
composer UIA values are readable, and the header OCR lines. Review or redact
names before sharing the output.
Review/redact contact names and OCR text before sharing output.

**Actual Windows live-call start/end success remains unverified.**
