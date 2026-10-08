"""
NOVA Comms Agent - Phase 5: Email, Calendar, WhatsApp.
Sab kuch local config se (Gmail App Password), credentials kabhi code me nahi.
"""
import os
import sys
import json
import re
import time
import datetime
import threading
import webbrowser
import urllib.parse
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "comms_config.json")   # gmail + app_password (gitignored)
CONTACTS_PATH = os.path.join(BASE_DIR, "contacts.json")      # name -> phone/email
CALENDAR_PATH = os.path.join(BASE_DIR, "calendar.json")      # events


def _load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[comms] load {path} fail: {e}")
    return default if default is not None else {}


def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[comms] save {path} fail: {e}")
        return False


# ================= EMAIL =================

def setup_email(args):
    """Gmail + App Password save karo. Args: {email, app_password}"""
    email = (args.get("email") or "").strip().lower()
    app_password = (args.get("app_password") or args.get("password") or "").strip()
    if "@" not in email:
        return "Gmail address do, jaise: pappu210089@gmail.com"
    if len(app_password) < 10:
        return ("App password chahiye (normal password nahi). "
                "Google Account -> Security -> 2-Step Verification -> App passwords se banao "
                "(16 char, xxxx xxxx format).")
    cfg = _load_json(CONFIG_PATH)
    cfg["gmail"] = email
    cfg["app_password"] = app_password.replace(" ", "")
    if _save_json(CONFIG_PATH, cfg):
        return f"Email setup ho gaya: {email} (app password saved). Ab send_email bol sakte ho."
    return "Save fail - file permission check karo."


def send_email(args):
    """Gmail SMTP se email bhejo. Args: {to, subject, body}"""
    to = (args.get("to") or args.get("recipient") or args.get("email") or "").strip()
    subject = (args.get("subject") or args.get("sub") or "NOVA message").strip()
    body = (args.get("body") or args.get("message") or args.get("text") or "").strip()
    if not to or "@" not in to:
        contacts = _load_json(CONTACTS_PATH)
        for name, info in contacts.items():
            if name.lower() == to.lower() and "@" in str(info.get("email", "")):
                to = info["email"]
                break
    if not to or "@" not in to:
        return "Kisko bhejna hai? Email address ya saved contact bolo."
    if not body:
        return "Email ka content (body) kya hai?"

    cfg = _load_json(CONFIG_PATH)
    gmail = cfg.get("gmail")
    app_password = cfg.get("app_password")
    if not gmail or not app_password:
        return ("Email setup nahi hua. Bolo: 'setup email <gmail> <app password>' "
                "ya tool setup_email use karo (Google me App Password banao).")
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = gmail
        msg["To"] = to
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(gmail, app_password)
            s.sendmail(gmail, [to], msg.as_string())
        return f"Email bhej diya: {to} (subject: {subject})"
    except smtplib.SMTPAuthenticationError:
        return ("Gmail login fail. App password sahi hai? "
                "Normal password nahi, 16-digit App Password chahiye.")
    except Exception as e:
        return f"Email fail: {str(e)[:120]}"


_EMAIL_NOISE = ("learn more", "get started", "unsubscribe", "view in browser",
                "terms of service", "privacy policy", "help us improve",
                "this email was sent", "manage your", "preferences", "reset password")


def _clean_email_body(body, max_len=170):
    """Raw email body -> voice-friendly snippet (URL/noise lines hata ke)."""
    body = re.sub(r"https?://\S+|www\.\S+", " ", str(body or ""))
    body = re.sub(r"\[([^\]]{1,40})\]\([^)]*\)", r"\1", body)
    body = re.sub(r"\s+", " ", body).strip()
    sents = re.split(r"(?<=[.!])\s+", body)
    keep = []
    for s in sents:
        sl = s.lower().strip()
        if len(sl) < 12 or any(n in sl for n in _EMAIL_NOISE):
            continue
        keep.append(s.strip())
        if sum(len(x) for x in keep) >= max_len:
            break
    snippet = " ".join(keep)[:max_len].strip(" ,;:-")
    if not snippet:
        snippet = body[:max_len]
    return snippet or "(koi text nahi)"


def read_email(args):
    """Inbox se latest emails - voice-friendly compact format. Args: {n}"""
    n = int(args.get("n") or args.get("limit") or 5)
    cfg = _load_json(CONFIG_PATH)
    gmail = cfg.get("gmail")
    app_password = cfg.get("app_password")
    if not gmail or not app_password:
        return send_email({})
    try:
        import imaplib
        import email as email_lib
        from email.header import decode_header
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(gmail, app_password)
        mail.select("inbox")
        status, data = mail.search(None, "ALL")
        if status != "OK":
            return "Inbox read fail."
        ids = data[0].split()[-n:][::-1]
        out = [f"Inbox ke latest {len(ids)} emails:"]
        for i, mid in enumerate(ids, 1):
            st, msg_data = mail.fetch(mid, "(BODY.PEEK[])")
            if st != "OK":
                continue
            msg = email_lib.message_from_bytes(msg_data[0][1])
            frm, _ = decode_header(msg.get("From", ""))[0] if msg.get("From") else (b"", None)
            if isinstance(frm, bytes):
                frm = frm.decode("utf-8", "ignore")
            subj, _ = decode_header(msg.get("Subject", ""))[0] if msg.get("Subject") else (b"", None)
            if isinstance(subj, bytes):
                subj = subj.decode("utf-8", "ignore")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", "ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", "ignore")
            body = " ".join(body.split())[:1200]
            subj = re.sub(r"\s+", " ", str(subj)).strip()[:70]
            frm = re.sub(r"\s+", " ", str(frm)).strip()
            if "<" in frm:
                frm = frm.split("<")[0].strip() or frm
            snippet = _clean_email_body(body, max_len=170)
            out.append(f"{i}. {subj or '(no subject)'} | {frm[:40]}: {snippet}")
        mail.logout()
        return "\n".join(out)
    except Exception as e:
        return f"Read email fail: {str(e)[:120]}"


# ================= CALENDAR =================

def _parse_when(when_text):
    """Natural Hinglish time -> datetime.
    Order: 1) '25 dec 10 baje' date+time  2) explicit formats  3) kal/tomorrow
           4) reminders parser (relative)  5) date-only.
    Year hamesha explicit inject hota hai (Py3.14 DeprecationWarning avoid)."""
    if not when_text:
        return None
    now = datetime.datetime.now()
    low = when_text.lower().strip()
    low = re.sub(r"\bsept\b", "sep", low)          # sept -> sep (strptime friendly)
    titled = re.sub(r"(?i)\bsept\b", "Sep", when_text.strip())

    def _with_year(dt):
        if dt < now:
            dt = dt.replace(year=dt.year + 1)
        return dt

    # 1. "25 dec 10 baje" / "25 sep 6 pm" / "25/12 10:30" - date + time
    m = re.match(r"^(\d{1,2}(?:\s+[a-z]{3,9}|/\d{1,2}))\s+(\d{1,2})(?::(\d{2}))?\s*(baje|am|pm|oclock)?$", low)
    if m and not re.search(r"\d{4}", low):
        date_part, hh, mm, ap = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        if hh <= 23 and (mm is None or int(mm) <= 59):
            if ap == "pm" and hh < 12:
                hh += 12
            elif ap == "am" and hh == 12:
                hh = 0
            mn = int(mm) if mm else 0
            for fmt in ("%d %b %Y", "%d %B %Y"):
                try:
                    base = datetime.datetime.strptime(f"{date_part.title()} {now.year}", fmt)
                    return _with_year(base.replace(hour=hh, minute=mn))
                except ValueError:
                    continue
            try:
                base = datetime.datetime.strptime(f"{date_part}/{now.year}", "%d/%m/%Y")
                return _with_year(base.replace(hour=hh, minute=mn))
            except ValueError:
                pass

    # 2. Explicit year-wala formats: "25 dec 2026 18:30", "2026-12-25 18:30"
    for fmt in ("%d %b %Y %H:%M", "%d %B %Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return _with_year(datetime.datetime.strptime(titled, fmt))
        except ValueError:
            continue
    # Year-less time: "25 dec 10:30" -> year inject
    for fmt in ("%d %b %H:%M", "%d %B %H:%M", "%d/%m %H:%M"):
        try:
            return _with_year(datetime.datetime.strptime(f"{titled} {now.year}", fmt + " %Y"))
        except ValueError:
            continue

    # 3. "kal subah 9 baje" / "tomorrow 9 am" - kal pehle, time baad me
    if "tomorrow" in low or "kal" in low:
        base = now + datetime.timedelta(days=1)
        m = re.search(r"(\d{1,2})[:.h]?(\d{2})?\s*(baje|am|pm|oclock)?", low)
        if m and (m.group(3) or m.group(2)):
            h = int(m.group(1))
            mn = int(m.group(2)) if m.group(2) else 0
            if m.group(3) == "pm" and h < 12:
                h += 12
            if m.group(3) == "am" and h == 12:
                h = 0
            if h <= 23:
                return base.replace(hour=h, minute=mn, second=0, microsecond=0)
        return base.replace(hour=9, minute=0, second=0, microsecond=0)

    # 4. Relative / baje / next week - reminders ka proven parser
    try:
        import reminders
        t = reminders._parse_time(when_text)
        if t:
            return t
    except Exception:
        pass
    if "next week" in low or "agle hafte" in low:
        return now + datetime.timedelta(days=7)

    # 5. Date-only: "25 sep", "25/12", "25 sep 2026" -> 9 AM
    for fmt in ("%d %b %Y", "%d %B %Y", "%d/%m/%Y"):
        try:
            return _with_year(datetime.datetime.strptime(titled, fmt).replace(hour=9, minute=0))
        except ValueError:
            continue
    for fmt in ("%d %b", "%d %B", "%d/%m"):
        try:
            base = datetime.datetime.strptime(f"{titled} {now.year}", fmt + " %Y")
            return _with_year(base.replace(hour=9, minute=0))
        except ValueError:
            continue
    return None


def calendar_add(args):
    """Calendar event add karo. Args: {title, when, notes}"""
    title = (args.get("title") or args.get("text") or args.get("event") or "").strip()
    when_text = (args.get("when") or args.get("time") or args.get("date") or "").strip()
    notes = (args.get("notes") or args.get("details") or "").strip()
    if not title:
        return "Event ka naam kya hai?"
    if not when_text:
        return "Kab hai? Jaise: 'kal 6 baje', '25 sept 10 baje', '5 minute baad'."
    target = _parse_when(when_text)
    if not target:
        return f"'{when_text}' samajh nahi aaya. Aise bolo: 'kal subah 9 baje', '25 sept 6 baje'."
    events = _load_json(CALENDAR_PATH, [])
    events.append({
        "title": title,
        "when": target.isoformat(),
        "notes": notes,
        "created": datetime.datetime.now().isoformat(),
    })
    _save_json(CALENDAR_PATH, events)
    when_str = target.strftime("%d %b %I:%M %p")
    return f"Calendar me add ho gaya: '{title}' - {when_str}"


def calendar_list(args):
    """Events list karo. Args: {when: today|tomorrow|week|all}"""
    filter_ = (args.get("when") or args.get("filter") or "upcoming").lower()
    events = _load_json(CALENDAR_PATH, [])
    if not events:
        return "Calendar khaali hai. 'kal 6 baje meeting' bolo, add kar dunga."
    now = datetime.datetime.now()
    start = now
    end = None
    if filter_ == "today":
        end = now.replace(hour=23, minute=59, second=59)
    elif filter_ == "tomorrow":
        start = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0)
        end = start.replace(hour=23, minute=59, second=59)
    elif filter_ == "week":
        end = now + datetime.timedelta(days=7)
    out_ev = []
    for e in events:
        try:
            t = datetime.datetime.fromisoformat(e["when"])
        except Exception:
            continue
        if t >= start and (end is None or t <= end):
            out_ev.append((t, e))
    out_ev.sort(key=lambda x: x[0])
    if not out_ev:
        return f" '{filter_}' me koi event nahi."
    lines = [f"Calendar ({len(out_ev)} events):"]
    for t, e in out_ev:
        when_str = t.strftime("%a %d %b %I:%M %p")
        lines.append(f"  {when_str} - {e['title']}" + (f" ({e['notes']})" if e.get("notes") else ""))
    return "\n".join(lines)


def calendar_delete(args):
    """Event delete. Args: {title}"""
    title = (args.get("title") or args.get("text") or "").strip().lower()
    if not title:
        return "Ksa event delete karna hai? Title bolo."
    events = _load_json(CALENDAR_PATH, [])
    keep = [e for e in events if title not in e.get("title", "").lower()]
    removed = len(events) - len(keep)
    if not removed:
        return f"'{title}' jaisa koi event nahi."
    _save_json(CALENDAR_PATH, keep)
    return f"{removed} event delete kar diya: '{title}'"


# ================= NUMBER NORMALIZER (STT fix) =================
# Whisper number-words ko garble karta hai: "nine eight seven..." / "nau aath..." /
# "987654321O" -> sab 10-digit me lao.

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_WORD_DIGITS = {
    # English
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    # Romanized Hindi / Hinglish
    "shunya": "0", "sunya": "0", "sifar": "0",
    "ek": "1", "do": "2", "teen": "3", "tin": "3", "char": "4", "chaar": "4",
    "panch": "5", "paanch": "5", "pach": "5",
    "chhe": "6", "chah": "6", "che": "6", "chey": "6",
    "saat": "7", "sat": "7",
    "aath": "8", "ath": "8",
    "nau": "9",
    # Devanagari words
    "शून्य": "0",
    "एक": "1", "दो": "2", "तीन": "3",
    "चार": "4", "पांच": "5",
    "पाँच": "5", "छह": "6",
    "सात": "7", "आठ": "8", "नौ": "9",
}
_MULTIPLIERS = {"double": 2, "duple": 2, "doublet": 2, "triple": 3, "druble": 2}


def _to_digits(text):
    """STT text -> digits string. English/Hinglish/Devanagari digit-words sab pakadta hai.
    10+ digits mile toh last 10, warna jitna mila wapas."""
    if not text:
        return ""
    t = str(text).lower().translate(_DEV_DIGITS)
    out = []
    tokens = re.findall(r"[a-z0-9ऀ-ॿ]+", t)
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        # numeric/alphanumeric token (letter confusions: O->0, l->1, S->5)
        if re.search(r"\d", tok):
            fixed = tok.translate(str.maketrans({"o": "0", "l": "1", "s": "5", "b": "6", "g": "9", "z": "2"}))
            out.append(re.sub(r"\D", "", fixed))
            i += 1
            continue
        # multiplier: "double nine" -> 99
        if tok in _MULTIPLIERS and i + 1 < len(tokens) and tokens[i + 1] in _WORD_DIGITS:
            out.append(_WORD_DIGITS[tokens[i + 1]] * _MULTIPLIERS[tok])
            i += 2
            continue
        # word digit
        if tok in _WORD_DIGITS:
            out.append(_WORD_DIGITS[tok])
            i += 1
            continue
        i += 1
    digits = "".join(out)
    return digits


# ================= WHATSAPP =================

def save_contact(args):
    """Contact save. Args: {name, phone, email} - STT number-words auto-normalize."""
    name = (args.get("name") or args.get("contact") or "").strip()
    phone = (args.get("phone") or args.get("number") or "").strip()
    email = (args.get("email") or "").strip()
    if not name:
        return "Contact ka naam kya hai?"
    if not phone and not email:
        return "Phone number ya email do."
    if phone:
        digits = _to_digits(phone)
        if len(digits) < 10:
            # LLM ne number kisi aur field me daala ho toh poora scan karo
            scan = " ".join(str(v) for v in args.values())
            d2 = _to_digits(scan)
            if len(d2) >= 10:
                digits = d2
        if len(digits) >= 10:
            phone = digits[-10:]
        elif digits:
            return (f"Number adhoora sunai diya: '{digits}' (10 digit chahiye). "
                    f"Dobara bolo, ya TYPE karo: save contact {name} number 9876543210")
        else:
            return (f"Number samajh nahi aaya ('{phone[:40]}'). "
                    f"Dobara bolo, ya TYPE karo: save contact {name} number 9876543210")
    contacts = _load_json(CONTACTS_PATH)
    contacts[name] = {"phone": phone, "email": email, "saved": datetime.datetime.now().isoformat()}
    _save_json(CONTACTS_PATH, contacts)
    return f"Contact save ho gaya: {name} ({phone or email})"


def _resolve_contact(name_or_phone):
    """name ya number -> (phone, email)."""
    raw = (name_or_phone or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) < 10:
        d = _to_digits(raw)
        if len(d) >= 10:
            digits = d
    if len(digits) >= 10:
        return digits[-10:], ""
    contacts = _load_json(CONTACTS_PATH)
    for name, info in contacts.items():
        if name.lower() == raw.lower() or raw.lower() in name.lower():
            return str(info.get("phone", "")).strip(), str(info.get("email", "")).strip()
    try:
        import memory
        val = memory.get_fact(raw.lower().replace(" ", "_"))
        if val:
            d = "".join(ch for ch in val if ch.isdigit())
            if len(d) >= 10:
                return d, ""
    except Exception:
        pass
    return "", ""


def _wa_desktop_installed():
    """WhatsApp Desktop installed hai?"""
    import glob
    try:
        if glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Packages\5319275A.WhatsAppDesktop_*")):
            return True
        for pat in (r"%ProgramFiles%\WhatsApp\WhatsApp.exe",
                    r"%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe"):
            if os.path.exists(os.path.expandvars(pat)):
                return True
    except Exception:
        pass
    return False


def _wa_activate(w):
    try:
        w.activate()
    except Exception as e:
        _wa_diagnostic("chat activate fail; checking actual foreground", e)
        if _wa_foreground_status(w)[0]:
            return True
        try:
            w.minimize()
            time.sleep(0.3)
            w.maximize()
        except Exception as fallback_error:
            _wa_diagnostic("chat activation fallback fail", fallback_error)
    return _wa_foreground_status(w)[0]


def _wa_open_chat_and_run(name, after_open=None, wait_load=12):
    """WhatsApp kholo + NAAM se chat search karke kholo (search -> type naam ->
    enter), phir optional after_open(pyautogui, pyperclip, mode) chalao.
    Desktop: Ctrl+F search. Web: search box click (coords override wa_web_search_xy).
    Returns (ok, note)."""
    try:
        import pyautogui
        import pygetwindow as gw
        import pyperclip
    except Exception as e:
        return False, f"automation lib missing: {e}"
    desktop = _wa_desktop_installed()
    mode = "desktop" if desktop else "web"
    try:
        if desktop:
            os.system("start whatsapp://")
        else:
            webbrowser.open("https://web.whatsapp.com/")
    except Exception as e:
        _wa_diagnostic("WhatsApp launch fail; checking existing window", e)
    # Window ka wait karo
    wins = []
    deadline = time.time() + wait_load
    while time.time() < deadline:
        time.sleep(1)
        try:
            wins = [w for w in gw.getWindowsWithTitle("WhatsApp") if w.visible]
        except Exception as e:
            _wa_diagnostic("chat GW enumeration fail", e)
            wins = []
        if wins:
            break
    if not wins:
        return False, "WhatsApp window khula nahi (app install / QR login check karo)"
    # Desktop app ko prefer karo exact title se
    exact = [w for w in wins if (w.title or "").strip() == "WhatsApp"]
    w = exact[0] if exact else wins[0]
    if not _wa_activate(w):
        return False, "WhatsApp foreground unverified; chat input blocked"
    time.sleep(1.2)
    old_pause, old_failsafe = pyautogui.PAUSE, pyautogui.FAILSAFE
    pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = False
    try:
        if not _wa_screen_click_allowed("chat search input", w):
            return False, "WhatsApp foreground unverified; chat input blocked"
        pyautogui.hotkey("esc")
        time.sleep(0.4)
        if mode == "desktop":
            pyautogui.hotkey("ctrl", "f")   # Desktop: search chats
        else:
            # Web: search box click (configurable coords) fallback keyboard combo
            cfg = _load_json(CONFIG_PATH)
            xy = cfg.get("wa_web_search_xy")
            if not _wa_web_search_click(w, xy, pyautogui):
                if not _wa_screen_click_allowed("web keyboard search", w):
                    return False, "WhatsApp foreground unverified; chat input blocked"
                pyautogui.hotkey("ctrl", "alt", "/")
        time.sleep(0.8)
        # Naam paste (unicode safe) -> pehla result khulta hai
        pyperclip.copy(str(name))
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(1.2)
        if callable(after_open):
            r = after_open(pyautogui, pyperclip, mode)
            # after_open 2-tuple (ok, note) ya 3-tuple (ok, note, state) dono
            # de sakta hai - dono pass-through, warna coerce karo.
            if isinstance(r, tuple) and len(r) in (2, 3):
                return r
            return True, str(r), "unknown"
        return True, mode
    except Exception as e:
        return False, f"automation fail: {str(e)[:80]}"
    finally:
        pyautogui.PAUSE, pyautogui.FAILSAFE = old_pause, old_failsafe


def _wa_send_by_name(name, message, wait_load=12):
    """WhatsApp me NAAM se search karke message bhejo - number save ki zaroorat Nahi.
    Returns (ok, note)."""
    def _type_and_send(pg, clipboard, mode):
        # Message paste + Enter = send
        clipboard.copy(str(message))
        pg.hotkey("ctrl", "v")
        time.sleep(0.5)
        pg.press("enter")
        return True, mode

    return _wa_open_chat_and_run(name, after_open=_type_and_send, wait_load=wait_load)


def whatsapp_send(args):
    """WhatsApp message ready karo + best-effort auto-send.
    Args: {contact|phone, message, auto_send}"""
    target = (args.get("contact") or args.get("phone") or args.get("to") or "").strip()
    message = (args.get("message") or args.get("text") or args.get("msg") or "").strip()
    auto = str(args.get("auto_send", "")).lower() in ("1", "true", "yes", "haan", "ha")
    if not target:
        return "Kisko bhejna hai? Contact naam ya number bolo."
    if not message:
        return "Message kya bhejna hai?"
    phone, _email = _resolve_contact(target)
    if not phone:
        # Number ki zaroorat nahi - WhatsApp me naam se search karke khud bhejo
        ok, note = _wa_send_by_name(target, message)
        if ok:
            return (f"WhatsApp me '{target}' search karke message bhej diya ({note} mode, best-effort). "
                    f"Chat khol ke check kar lo.")
        return (f"Naam se bhej nahi paya ({note}). "
                f"Ya toh WhatsApp login/app check karo, ya number save karo: "
                f"save contact {target} number <10 digit>")
    if len(phone) == 10:
        phone = "91" + phone
    text = urllib.parse.quote(message)
    app_url = f"whatsapp://send?phone={phone}&text={text}"
    web_url = f"https://web.whatsapp.com/send?phone={phone}&text={text}"
    opened = False
    try:
        opened = webbrowser.open(app_url)
    except Exception:
        opened = False
    if not opened:
        try:
            opened = webbrowser.open(web_url)
        except Exception:
            opened = False
    if not opened:
        return "WhatsApp khul hi nahi paaya - WhatsApp installed hai check karo."
    result = f"WhatsApp khola: {target} (+{phone}), message ready - \"{message[:50]}\""
    if auto:
        def _send():
            try:
                time.sleep(4)
                import pyautogui
                import pygetwindow as gw
                wins = [w for w in gw.getWindowsWithTitle("WhatsApp") if w.visible]
                if wins:
                    w = wins[0]
                    try:
                        w.activate()
                    except Exception:
                        w.minimize(); w.maximize()
                    time.sleep(0.5)
                    pyautogui.press("enter")
            except Exception as e:
                print(f"[whatsapp auto-send skip] {e}")
        threading.Thread(target=_send, daemon=True).start()
        result += " | Auto-send: 4 sec me Enter dabega (best-effort)."
    else:
        result += " | Enter daba do ya bolo 'auto send on'."
    return result


# ================= WHATSAPP CALL (voice / video) =================
# CALL FIX (NOVA): purana flow ui_agent.click_element ka FUZZY match use karta
# tha ("Clicked fuzzy: Voice call"). Wo chat list ke call-log message
# ("Voice call" / "Missed voice call") pe click kar deta tha, asli header
# button pe nahi - aur bina verify kiye success bol deta tha.
#
# Ab 3 cheezein badli hain:
#   1) STRICT UIA name match (exact naam + weight/header/button scoring,
#      fuzzy match HATA diya, call-log words block)
#   2) har click ke BAAD call screen VERIFY (OCR) - verify na ho to HONEST fail
#   3) fallback chain: UIA -> vision_click -> configured coords (default off)
# Video call ke liye args me video=true.

WA_CALL_STATE_WAIT_SEC = 2.5   # call screen check se pehle thoda wait

# STRICT name weights - key EXACT lowercase element name hai, fuzzy nahi.
# Weight 3 = pakka call button, 1 = generic "Call" (kabhi-kabhi list me bhi).
_WA_CALL_UI_NAME_WEIGHTS = {
    False: {"voice call": 3, "voice call button": 3, "audio call": 3,
            "audio call button": 3, "start voice call": 3, "call": 1},
    True:  {"video call": 3, "video call button": 3, "start video call": 3},
}

# Chat ke call-log message inhi words se bante hain ("Missed voice call",
# "Declined call", "No answer") - inhe kabhi click NAHI karna.
_WA_CALL_BAD_NAME_WORDS = ("missed", "declined", "ended", "incoming", "outgoing",
                           "no answer", "callback", "call back")

# Header region scoring: chat window ke top 22% height me aur left >= 25% width
# (yaani header ka right side) - asli call button wahin hota hai.
_WA_CALL_HEADER_TOP_RATIO = 0.22
_WA_CALL_HEADER_LEFT_RATIO = 0.25
_WA_CALL_HEADER_BONUS = 5
_WA_CALL_BUTTON_BONUS = 3
_WA_CALL_MAX_CLICK_TRIES = 3

# VLM (vision_click) ke liye English visual description - header ka right side.
# "it is NOT text inside chat messages" isliye: VLM chat ke 'Voice call'
# message pe click kar deta tha.
_WA_CALL_VISION_TARGETS = {
    False: ("phone handset icon button in the top header bar right side of the "
            "open WhatsApp chat window, next to the video camera and menu "
            "buttons. it is NOT text inside chat messages"),
    True:  ("video camera icon button in the top header bar right side of the "
            "open WhatsApp chat window, next to the phone handset and menu "
            "buttons. it is NOT text inside chat messages"),
}

# VERIFY: call screen pe ye text dikhta hai -> call really lag gayi.
# "call ended" / "no answer" JAAN-BOOJH ke hint NAHI hain - chat ke call-log
# message me bhi wahi text hota hai, isliye wo false positive dega.
_WA_CALL_SCREEN_HINTS = ("end call", "end video call", "calling", "ringing",
                         "reconnecting", "call connecting")

# vision_control.read_screen ka empty sentinel (OCR chala, text nahi mila).
_WA_OCR_EMPTY_MARK = "kuch text nahi mila"

# Call state values
WA_CALL_DETECTED = "detected"
WA_CALL_ABSENT = "absent"
WA_CALL_UNKNOWN = "unknown"
WA_CALL_NOCLICK = "noclick"


def _wa_call_wants_video(args):
    """args se video flag nikalo (bool / 'true' / 'haan' / 'video' sab chalega)."""
    v = (args or {}).get("video", (args or {}).get("video_call", False))
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in (
        "1", "true", "yes", "y", "haan", "ha", "video", "video call", "video_call")


def _wa_call_target(args):
    """Call ke liye contact/naam nikalo."""
    a = args or {}
    return (a.get("contact") or a.get("name") or a.get("to")
            or a.get("phone") or a.get("number") or "").strip()


def _wa_call_wants_probe(args):
    """probe=true -> sirf debug dump, koi click nahi."""
    p = (args or {}).get("probe", False)
    if isinstance(p, bool):
        return p
    return str(p).strip().lower() in ("1", "true", "yes", "y", "haan", "ha")


def _wa_call_name_weights(video=False):
    """Exact-name -> weight map. comms_config.json ka 'wa_call_names' (list ya
    str) extra naam weight 3 ke saath jodta hai - Windows pe tuning ke liye."""
    w = dict(_WA_CALL_UI_NAME_WEIGHTS[bool(video)])
    try:
        cfg = _load_json(CONFIG_PATH) or {}
        extra = cfg.get("wa_call_names") or []
        if isinstance(extra, str):
            extra = [extra]
        for n in extra:
            n = str(n or "").strip().lower()
            if n:
                w[n] = max(w.get(n, 0), 3)
    except Exception as e:
        print("[whatsapp_call] wa_call_names config skip: " + str(e)[:50])
    return w


_WA_OFFSCREEN_LIMIT = -20000
_WA_MIN_WINDOW_SIZE = 120
_WA_OCR_SELF_MARKERS = ("whatsapp_ca", "contact resolved", "esc] stop",
                        "arena.ai", "git pull", "origin/main", "mingw64",
                        "python comms_agent", "verify miss", "verify ok")


def _wa_win_score(title, rect):
    score = 100 if str(title).strip().lower() == "whatsapp" else 0
    if rect:
        l, t, r, b = rect
        w, h = max(0, r - l), max(0, b - t)
        if l > _WA_OFFSCREEN_LIMIT and t > _WA_OFFSCREEN_LIMIT:
            score += 60
        if w >= _WA_MIN_WINDOW_SIZE and h >= _WA_MIN_WINDOW_SIZE:
            score += 30
        score += min(20, w * h // 150000)
    return score


def _wa_diagnostic(operation, error):
    print("[whatsapp_call] %s: %s: %s" % (
        operation, type(error).__name__, str(error).replace("\n", " ")[:180]))


def _wa_on_windows():
    return sys.platform == "win32"


def _wa_dpi_api():
    # DPI_AWARENESS_CONTEXT is pointer-sized, including the negative pseudo
    # handles. ctypes' default c_int return would truncate a previous context
    # on 64-bit Windows and make restoration unreliable.
    import ctypes
    setter = ctypes.WinDLL("user32", use_last_error=True).SetThreadDpiAwarenessContext
    setter.argtypes = [ctypes.c_void_p]
    setter.restype = ctypes.c_void_p
    return setter


@contextmanager
def _wa_physical_pixels(operation):
    """Physical pixels for THIS thread only; nested scopes restore in finally.

    Do not set process-wide DPI awareness or preload pywinauto as a DPI fix.
    The thread override keeps GW rectangles and screenshot/click consumers in
    the same coordinate space regardless of a library's process DPI default.
    Non-Windows has no Windows DPI virtualization. On Windows, unsupported or
    failed setup is fail-closed (no legacy/global DPI fallback).
    """
    if not _wa_on_windows():
        yield True
        return
    setter, previous, ready = None, None, False
    try:
        setter = _wa_dpi_api()
        previous = setter(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        if not previous:
            import ctypes
            raise OSError("SetThreadDpiAwarenessContext failed (winerror=%s)" %
                          getattr(ctypes, "get_last_error", lambda: 0)())
        ready = True
    except Exception as e:
        _wa_diagnostic(operation + " DPI setup fail; unsafe screen operation skipped", e)
    try:
        yield ready
    finally:
        if previous:
            try:
                if not setter(previous):
                    raise OSError("previous thread DPI context restore returned NULL")
            except Exception as e:
                _wa_diagnostic(operation + " DPI restore fail", e)


def _wa_uia_window_candidates(dump=False, backend="uia"):
    out = []
    try:
        import ui_agent
        if not ui_agent.IS_WIN:
            return out
        if ui_agent._Desktop is None:
            ui_agent._get_pwa()
        if ui_agent._Desktop is None:
            raise RuntimeError("pywinauto Desktop unavailable")
        for w in ui_agent._Desktop(backend=backend).windows(visible_only=False):
            try:
                title = w.window_text()
                if "whatsapp" not in title.lower():
                    continue
                rect = _wa_el_rect(w, diagnostic=backend + " window rectangle fail")
                out.append((_wa_win_score(title, rect), title, rect, w))
            except Exception as e:
                _wa_diagnostic(backend + " window enumeration item fail", e)
    except Exception as e:
        _wa_diagnostic(backend + " window enumeration fail", e)
    out.sort(key=lambda c: -c[0])
    if dump:
        for score, title, rect, _ in out[:10]:
            print("window score=%d title=%r rect=%s" % (score, title, rect))
    return out


def _wa_uia_window():
    candidates = _wa_uia_window_candidates()
    if candidates:
        return candidates[0][3]
    # ui_agent._find_window silently catches backend errors. Enumerate this
    # fallback here instead, so missing windows and failed enumeration differ.
    with _wa_physical_pixels("win32 window fallback") as ready:
        candidates = _wa_uia_window_candidates(backend="win32") if ready else []
    return candidates[0][3] if candidates else None


def _wa_gw_rect(w):
    if w is None:
        return None
    with _wa_physical_pixels("GW bbox") as ready:
        if not ready:
            return None
        try:
            l, t, width, height = int(w.left), int(w.top), int(w.width), int(w.height)
            return l, t, l + width, t + height
        except Exception as e:
            _wa_diagnostic("GW window rectangle fail", e)
            return None


def _wa_gw_window():
    with _wa_physical_pixels("GW enumeration") as ready:
        if not ready:
            return None
        try:
            import pygetwindow as gw
            candidates = []
            for w in gw.getWindowsWithTitle("WhatsApp"):
                try:
                    title = str(w.title)
                    if "whatsapp" in title.lower():
                        candidates.append((_wa_win_score(title, _wa_gw_rect(w)), w))
                except Exception as e:
                    _wa_diagnostic("GW window enumeration item fail", e)
            return max(candidates, key=lambda item: item[0])[1] if candidates else None
        except Exception as e:
            _wa_diagnostic("GW window enumeration fail", e)
            return None


def _wa_window_handle(window):
    for obj, attr in ((window, "_hWnd"), (window, "handle"),
                      (getattr(window, "element_info", None), "handle")):
        try:
            value = getattr(obj, attr, None)
            if value:
                return int(value)
        except (AttributeError, TypeError, ValueError):
            continue
    return None


def _wa_window_title(window):
    if window is None:
        return ""
    try:
        title = getattr(window, "title", None)
        return str(title if title is not None else window.window_text()).strip()
    except Exception as e:
        _wa_diagnostic("window title read fail", e)
        return _wa_el_name(window)


def _wa_foreground_info():
    """HWND + title, not the return string from activate()/focus_window()."""
    if _wa_on_windows():
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetForegroundWindow.argtypes = []
            user32.GetForegroundWindow.restype = wintypes.HWND
            user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
            user32.GetWindowTextLengthW.restype = ctypes.c_int
            user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
            user32.GetWindowTextW.restype = ctypes.c_int
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None, ""
            buf = ctypes.create_unicode_buffer(user32.GetWindowTextLengthW(hwnd) + 1)
            user32.GetWindowTextW(hwnd, buf, len(buf))
            return int(hwnd), buf.value
        except Exception as e:
            _wa_diagnostic("native foreground read fail; GW fallback", e)
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active is not None:
            return _wa_window_handle(active), _wa_window_title(active)
        return None, str(gw.getActiveWindowTitle() or "")
    except Exception as e:
        _wa_diagnostic("GW foreground fallback fail", e)
        return None, ""


def _wa_screen_window(element=None):
    if element is not None:
        try:
            return element.top_level_parent()
        except AttributeError:
            pass  # a wrapper without a parent API: use the selected window
        except Exception as e:
            _wa_diagnostic("UIA top-level window fallback", e)
    w = _wa_gw_window()
    return w if w is not None else _wa_uia_window()


def _wa_foreground_status(window=None):
    try:
        w = window if window is not None else _wa_screen_window()
        expected = _wa_window_handle(w)
        active, title = _wa_foreground_info()
        if expected and active:
            ok = expected == active
            return ok, "HWND target=%s foreground=%s" % (expected, active)
        # Handles unavailable: exact title fallback, never a fuzzy substring
        # in an unrelated terminal title. A known HWND mismatch cannot get here.
        wanted = _wa_window_title(w) if w is not None else "WhatsApp"
        ok = ("whatsapp" in wanted.lower() and title.strip().lower() == wanted.lower())
        return ok, "title fallback target=%r foreground=%r" % (wanted, title)
    except Exception as e:
        _wa_diagnostic("foreground verification fail", e)
        return False, "foreground unavailable"


def _wa_screen_click_allowed(operation, window=None):
    ok, detail = _wa_foreground_status(window)
    if not ok:
        print("[whatsapp_call] %s BLOCKED: foreground unverified (%s)" % (operation, detail))
    return ok


def _wa_focus_call_window():
    notes = []
    w = _wa_gw_window()
    if w is not None:
        try:
            if getattr(w, "isMinimized", False):
                w.restore()
            w.activate()
            notes.append("activate returned")
        except Exception as e:
            _wa_diagnostic("activate fail; checking actual foreground", e)
            notes.append("activate exception: " + str(e)[:100])
    # Windows sometimes reports error 0 even though the activation worked.
    # Verify before trying any fallback that might steal focus again.
    ok, detail = _wa_foreground_status(w)
    if not ok:
        try:
            import app_control
            notes.append("fallback: " + str(app_control.focus_window("WhatsApp"))[:100])
        except Exception as e:
            _wa_diagnostic("focus fallback fail", e)
            notes.append("focus fallback exception")
        ok, detail = _wa_foreground_status(w)
    return "foreground %s (%s); %s" % (
        "verified" if ok else "UNVERIFIED", detail, "; ".join(notes))


def _wa_ocr_is_terminal(text):
    low = str(text).lower()
    return next((m for m in _WA_OCR_SELF_MARKERS if m in low), None)


def _wa_ocr_regions():
    with _wa_physical_pixels("OCR regions") as ready:
        if not ready:
            return []
        regions = []
        rect = _wa_gw_rect(_wa_gw_window())
        if rect is None:
            rect = _wa_el_rect(_wa_uia_window())
        if rect:
            l, t, r, b = rect
            if l >= 0 and t >= 0 and r - l >= 100 and b - t >= 100:
                regions.append(("whatsapp", (l, t, r - l, b - t)))
        return regions + [("active", None), ("full", None)]


def _wa_ocr_read(label, region):
    with _wa_physical_pixels("OCR capture") as ready:
        if not ready:
            raise RuntimeError("physical-pixel DPI context unavailable; OCR skipped")
        import vision_control
        if region is not None:
            return " ".join(str(item[0]) for item in
                            vision_control._ocr_screen(region_mode="custom", region=region))
        return vision_control.read_screen(region_mode=label)


def _wa_el_name(el):
    try:
        return str(getattr(el.element_info, "name", "") or "").strip()
    except Exception:
        return ""


def _wa_el_type(el):
    """UIA control_type (fallback class_name), lowercase."""
    try:
        ct = getattr(el.element_info, "control_type", None)
        if ct:
            return str(ct).strip().lower()
        return str(getattr(el.element_info, "class_name", "") or "").strip().lower()
    except Exception:
        return ""


def _wa_el_rect(el, diagnostic=None):
    if el is None:
        return None
    try:
        r = el.rectangle()
        return (int(r.left), int(r.top), int(r.right), int(r.bottom))
    except Exception as e:
        if diagnostic:
            _wa_diagnostic(diagnostic, e)
        return None


def _wa_control_key(el, name, ctype, rect):
    """Runtime ID is authoritative; geometry is ONLY the no-ID fallback.

    Different runtime IDs can legitimately share a name/type/rectangle. Do
    not merge them using a second geometry-only dedup pass.
    """
    try:
        rid = el.element_info.runtime_id
        rid = rid() if callable(rid) else rid
        if rid is not None:
            rid = tuple(rid)
            if rid:
                hash(rid)
                return "runtime", rid
    except Exception:
        pass  # missing/stale/unsupported RuntimeId: documented fallback
    return "name/type/rect", name.lower(), ctype, rect


_WA_PROBE_LIMIT = 10
_WA_NEAR_MISS_WORDS = ("call", "video", "voice", "audio", "phone", "handset", "camera",
                       "hang", "decline", "reject")


def _wa_scan_call_controls(window, video=False, end_call=False):
    """One descendants snapshot for strict raw/unique counts and compact probes."""
    weights = _WA_END_CALL_UI_NAME_WEIGHTS if end_call else _wa_call_name_weights(video)
    bad_words = _WA_END_CALL_BAD_NAME_WORDS if end_call else _WA_CALL_BAD_NAME_WORDS
    scan = dict(window=window, rect=_wa_el_rect(window), descendants=0, raw=0,
                candidates=[], near_misses=[], near_miss_count=0, error=None)
    if window is None:
        return scan
    try:
        descs = list(window.descendants())
        scan["descendants"] = len(descs)
    except Exception as e:
        _wa_diagnostic("%s descendants fail" % ("end-call" if end_call else "call"), e)
        scan["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
        return scan
    raw, near_seen = [], set()
    for el in descs:
        name = _wa_el_name(el)
        low = name.lower()
        strict = low in weights and not any(bad in low for bad in bad_words)
        if not strict and not any(word in low for word in _WA_NEAR_MISS_WORDS):
            continue
        ctype, rect = _wa_el_type(el), _wa_el_rect(el)
        if not strict:
            # Display-only dedup: long/repeated chat-history names must never
            # flood the probe, nor become click candidates.
            key = (name, ctype, rect)
            if key not in near_seen:
                near_seen.add(key)
                if len(scan["near_misses"]) < _WA_PROBE_LIMIT:
                    scan["near_misses"].append(key)
            continue
        score = weights[low] * 2
        if not end_call and rect and scan["rect"]:
            wl, wt, wr, wb = scan["rect"]
            if ((rect[1] - wt) <= max(1, wb - wt) * _WA_CALL_HEADER_TOP_RATIO
                    and (rect[0] - wl) >= max(1, wr - wl) * _WA_CALL_HEADER_LEFT_RATIO):
                score += _WA_CALL_HEADER_BONUS
        if ctype == "button":
            score += _WA_CALL_BUTTON_BONUS
        raw.append(((score, name, ctype, el), _wa_control_key(el, name, ctype, rect)))
    scan["raw"] = len(raw)
    scan["near_miss_count"] = len(near_seen)
    seen = set()
    for candidate, key in sorted(raw, key=lambda item: (-item[0][0], item[0][1].lower())):
        if key not in seen:
            seen.add(key)
            scan["candidates"].append(candidate)
    return scan


def _wa_scan_lines(scan):
    w, rect = scan["window"], scan["rect"]
    title = _wa_window_title(w)
    lines = ["whatsapp uia window: " + ("mila" if w is not None else "NAHI mila"),
             "window score=%d title=%r rect=%s" % (_wa_win_score(title, rect), title, rect),
             "descendants count: %d" % scan["descendants"],
             "STRICT candidates: raw=%d unique=%d (strict candidates)" %
             (scan["raw"], len(scan["candidates"]))]
    if scan["error"]:
        lines.append("candidate scan fail: " + scan["error"])
    for score, name, ctype, el in scan["candidates"][:_WA_PROBE_LIMIT]:
        lines.append("  score=%2d type=%s name=%r rect=%s" %
                     (score, ctype or "?", name[:140], _wa_el_rect(el)))
    lines.append("near-miss unique=%d (showing %d)" %
                 (scan["near_miss_count"], len(scan["near_misses"])))
    lines.extend("near-miss name=%r type=%s rect=%s" % (name[:140], ctype, rect)
                 for name, ctype, rect in scan["near_misses"])
    return lines


def _wa_uia_call_candidates(video=False, dump=False):
    """STRICT exact-name scoring unchanged; return unique controls, best first."""
    scan = _wa_scan_call_controls(_wa_uia_window(), video=video)
    if dump:
        print("\n".join(_wa_scan_lines(scan)))
    return scan["candidates"]


def _wa_point_in_rect(rect, x, y):
    return bool(rect and rect[0] > _WA_OFFSCREEN_LIMIT and rect[1] > _WA_OFFSCREEN_LIMIT
                and rect[0] <= x < rect[2] and rect[1] <= y < rect[3])


def _wa_screen_rect(window):
    return (_wa_gw_rect(window) if hasattr(window, "left")
            else _wa_el_rect(window, diagnostic="screen window rectangle fail"))


def _wa_uia_click(el):
    """Coordinate-free invoke survives focus/DPI failure. Screen clicks do not."""
    try:
        el.invoke()
        return True, "invoke"
    except Exception as e:
        _wa_diagnostic("invoke fail; guarded click_input fallback", e)
    with _wa_physical_pixels("UIA click_input") as ready:
        if not ready:
            return False, "click_input blocked: DPI unavailable"
        try:
            window = _wa_screen_window(el)
            rect = _wa_el_rect(el)
            if not rect or not _wa_point_in_rect(
                    _wa_screen_rect(window), (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2):
                return False, "click_input blocked: invalid/out-of-window bounds"
            if not _wa_screen_click_allowed("UIA click_input", window):
                return False, "click_input blocked: foreground unverified"
            el.click_input()
            return True, "click_input"
        except Exception as e:
            _wa_diagnostic("UIA click_input fail", e)
            return False, "click fail: " + str(e)[:100]


def _wa_click_call_button_ui(video=False):
    """Layer 1: up to three DISTINCT strict UIA controls, never fuzzy matches."""
    try:
        import ui_agent
    except Exception as e:
        _wa_diagnostic("ui_agent unavailable", e)
        return None
    if getattr(ui_agent, "IS_WIN", False) is not True:
        return None
    _wa_focus_call_window()
    time.sleep(0.3)
    cands = _wa_uia_call_candidates(video)
    if not cands:
        print("[whatsapp_call] UIA me strict call button nahi mila (fuzzy off)")
        return None
    for score, name, ctype, el in cands[:_WA_CALL_MAX_CLICK_TRIES]:
        ok, how = _wa_uia_click(el)
        if ok:
            note = "uia %s '%s' score=%d" % (how, name, score)
            print("[whatsapp_call] ui click OK: " + note)
            return note
        print("[whatsapp_call] ui click fail '%s': %s" % (name, how))
    return None


def _wa_guarded_vision_click(target):
    # A VLM request can take seconds: locate ONLY, then recheck the foreground
    # and window bounds before consuming its coordinates. OCR still verifies
    # call state in the caller; a dry-run/find result is never reported as a click.
    with _wa_physical_pixels("vision click") as ready:
        if not ready:
            return None
        try:
            window = _wa_screen_window()
            if not _wa_screen_click_allowed("vision_click", window):
                return None
            rect = _wa_screen_rect(window)
            if not rect:
                print("[whatsapp_call] vision_click BLOCKED: window bounds unavailable")
                return None
            import vision_agent
            res = vision_agent.vision_click(target, dry_run=True, use_active_window=True)
            if not isinstance(res, dict) or not res.get("ok"):
                print("[whatsapp_call] vision click miss: " + str(res)[:100])
                return None
            x, y = int(res["x"]), int(res["y"])
            import pyautogui
            if rect != _wa_screen_rect(window) or not _wa_point_in_rect(rect, x, y):
                print("[whatsapp_call] vision_click BLOCKED: moved window/out-of-window coords")
                return None
            if not _wa_screen_click_allowed("vision_click final click", window):
                return None
            pyautogui.click(x, y)
            return "vision_click (%d,%d)" % (x, y)
        except Exception as e:
            _wa_diagnostic("vision_click fail", e)
            return None


def _wa_click_call_button_vision(video=False):
    """Layer 2: verified-foreground, physical-pixel VLM locate + guarded click."""
    return _wa_guarded_vision_click(_WA_CALL_VISION_TARGETS[bool(video)])


def _wa_offset_click(off, end_call=False):
    with _wa_physical_pixels("configured coords") as ready:
        if not ready:
            return None
        try:
            import pyautogui
            w = _wa_gw_window()
            rect = _wa_gw_rect(w)
            if not rect:
                print("[whatsapp_call] coords BLOCKED: WhatsApp bounds unavailable")
                return None
            l, t, r, b = rect
            xoff, yoff = int(off[0]), int(off[1])
            x, y = (l + xoff, b - yoff) if end_call else (r - xoff, t + yoff)
            if (l < 0 or t < 0 or r - l < 100 or b - t < 100
                    or xoff < 0 or yoff < 0 or not _wa_point_in_rect(rect, x, y)):
                print("[whatsapp_call] coords BLOCKED: invalid offsets/window bounds")
                return None
            if not _wa_screen_click_allowed("configured coords", w):
                return None
            pyautogui.click(x, y)
            note = "coords click (%d,%d) offset=%dx%d" % (x, y, xoff, yoff)
            print("[whatsapp_call] " + note)
            return note
        except Exception as e:
            _wa_diagnostic("coords fallback fail", e)
            return None


def _wa_web_search_click(window, xy, pyautogui):
    """Shared chat-open path: never mix logical GW bounds with screen pixels."""
    with _wa_physical_pixels("web search coords") as ready:
        if not ready:
            return False
        try:
            rect = _wa_gw_rect(window)
            if not rect:
                return False
            if xy is not None:
                if not isinstance(xy, (tuple, list)) or len(xy) != 2:
                    return False
                x, y = int(xy[0]), int(xy[1])
            else:
                x, y = rect[0] + 150, rect[1] + 130
            if not _wa_point_in_rect(rect, x, y):
                print("[whatsapp_call] web search coords BLOCKED: out-of-window bounds")
                return False
            if not _wa_screen_click_allowed("web search coords", window):
                return False
            pyautogui.click(x, y)
            return True
        except Exception as e:
            _wa_diagnostic("web search coords fail; keyboard fallback", e)
            return False


def _wa_call_fallback_xy(video=False):
    """Layer 3: explicitly configured [x_from_right, y_from_top], default OFF."""
    try:
        cfg = _load_json(CONFIG_PATH) or {}
        key = "video" if video else "voice"
        off = (cfg.get("wa_call_button_offsets") or {}).get(key)
        if not isinstance(off, (list, tuple)) or len(off) != 2:
            print("[whatsapp_call] coords fallback DISABLED "
                  "(wa_call_button_offsets." + key + " missing/invalid)")
            return None
        return _wa_offset_click(off)
    except Exception as e:
        _wa_diagnostic("coords config fail", e)
        return None


def _wa_call_state_note(video=False, wait=None):
    """VERIFY (sabse zaroori): call screen sach me aaya?

    Returns (state, hint) jahan state in me se ek hai:
      "detected" - OCR me calling/ringing/end call jaisa text dikha -> call lagi
      "absent"   - OCR chala par call screen ka koi hint nahi -> call nahi lagi
      "unknown"  - OCR hi nahi chal paya -> confirm nahi kar sakte

    OCR pehle WhatsApp bbox, phir active window aur full screen. "call ended" / "no answer" hint
    NAHI hain - chat ke call-log message me bhi wahi text hota hai.
    """
    if wait is None:
        wait = WA_CALL_STATE_WAIT_SEC
    with _wa_physical_pixels("call-state OCR") as ready:
        if not ready:
            return WA_CALL_UNKNOWN, "DPI context unavailable; OCR skipped"
        try:
            if wait:
                time.sleep(wait)
            import vision_control
        except Exception as e:
            print("[whatsapp_call] verify skip (ocr unavailable): " + str(e)[:60])
            return WA_CALL_UNKNOWN, "ocr unavailable"
        text_seen = False
        for mode, region in _wa_ocr_regions():
            try:
                t = str(_wa_ocr_read(mode, region) or "")
            except Exception as e:
                print("[whatsapp_call] ocr '%s' fail: %s" % (mode, str(e)[:50]))
                continue
            if not t or _WA_OCR_EMPTY_MARK in t.lower():
                continue
            marker = _wa_ocr_is_terminal(t)
            if marker:
                print("[whatsapp_call] OCR DISCARD [%s]: terminal marker %r" % (mode, marker))
                continue
            text_seen = True
            low = t.lower()
            for hint in _WA_CALL_SCREEN_HINTS:
                if hint in low:
                    print("[whatsapp_call] verify OK: '%s' dikha (%s window)" % (hint, mode))
                    return WA_CALL_DETECTED, hint
            # Active window me hint nahi mila to full screen bhi dekho - WhatsApp
            # ki calling screen aksar ALAG window hoti hai, chat window me nahi.
        if not text_seen:
            print("[whatsapp_call] verify: ocr ne text nahi diya - confirm nahi kar sakte")
            return WA_CALL_UNKNOWN, "ocr ne text nahi diya"
        print("[whatsapp_call] verify MISS: call screen ka koi hint nahi")
        return WA_CALL_ABSENT, "no call-screen text"


def _wa_call_already_active(video=False):
    """Call pehle se chal rahi ho to double-dial mat karo (chat me button
    dobara dabane se call cut/switch ho sakti hai)."""
    state, hint = _wa_call_state_note(video, wait=0.6)
    if state == WA_CALL_DETECTED:
        print("[whatsapp_call] call already active ('%s') - dobara dial nahi kiya" % hint)
        return True
    return False


def _wa_call_probe(video=False, end_call=False):
    """Compact, no-click diagnostics. One descendants snapshot, no weight tuning."""
    focus = _wa_focus_call_window()
    kind = "end call" if end_call else ("video call" if video else "voice call")
    lines = ["=== whatsapp_call probe (%s) ===" % kind, "focus-result: " + focus]
    try:
        import ui_agent
        lines.append("ui_agent IS_WIN: %s" % getattr(ui_agent, "IS_WIN", None))
        windows = _wa_uia_window_candidates()
        lines.append("UIA windows: %d (showing at most %d)" % (len(windows), _WA_PROBE_LIMIT))
        for score, title, rect, _ in windows[:_WA_PROBE_LIMIT]:
            lines.append("window score=%d title=%r rect=%s" % (score, title, rect))
        w = windows[0][3] if windows else _wa_uia_window()
        lines.extend(_wa_scan_lines(_wa_scan_call_controls(w, video, end_call)))
    except Exception as e:
        _wa_diagnostic("probe candidate scan fail", e)
        lines.append("candidate scan fail: " + str(e)[:160])
    weights = _WA_END_CALL_UI_NAME_WEIGHTS if end_call else _wa_call_name_weights(video)
    bad_words = _WA_END_CALL_BAD_NAME_WORDS if end_call else _WA_CALL_BAD_NAME_WORDS
    lines.append("%s name weights: %s" % ("END-call" if end_call else "call", weights))
    lines.append("%s bad words: %s" % ("END-call" if end_call else "call", list(bad_words)))
    with _wa_physical_pixels("probe OCR") as ready:
        lines.append("screen DPI: " + ("physical-pixel context ready" if ready else "UNAVAILABLE; OCR skipped"))
        if ready:
            for mode, region in _wa_ocr_regions():
                try:
                    txt = " ".join(str(_wa_ocr_read(mode, region) or "").split())
                    marker = _wa_ocr_is_terminal(txt)
                    lines.append("ocr[%s]%s: %s" % (mode,
                        " DISCARD terminal=" + marker if marker else "", txt[:200] or "(khaali)"))
                except Exception as e:
                    lines.append("ocr[%s] unavailable: %s" % (mode, str(e)[:160]))
    state, hint = _wa_call_state_note(video, wait=0)
    lines.append("call state: %s (%s)" % (state, hint))
    cfg = _load_json(CONFIG_PATH) or {}
    lines.append("wa_call_button_offsets: %s" % str(cfg.get("wa_call_button_offsets")))
    lines.append("wa_end_call_button_offsets: %s" % str(cfg.get("wa_end_call_button_offsets")))
    lines.append("wa_call_names: %s" % str(cfg.get("wa_call_names")))
    out = "\n".join(lines)
    print(out)
    return out


_WA_END_CALL_UI_NAME_WEIGHTS = {
    "end call": 3, "end call button": 3, "end video call": 3,
    "end video call button": 3, "hang up": 3, "hangup": 3,
    "hang up button": 3, "decline": 2, "decline call": 2,
    "reject": 2, "reject call": 2,
}
_WA_END_CALL_BAD_NAME_WORDS = ("missed", "ended", "no answer", "callback",
                               "call back", "incoming", "outgoing")
_WA_END_CALL_VISION_TARGET = (
    "red round end call / hang up button on the WhatsApp calling screen. "
    "it is NOT text inside chat messages and NOT the phone handset icon "
    "in the chat header")


def _wa_near_miss_names(window=None):
    w = window if window is not None else _wa_uia_window()
    return _wa_scan_call_controls(w)["near_misses"]


def _wa_uia_end_call_candidates(dump=False):
    scan = _wa_scan_call_controls(_wa_uia_window(), end_call=True)
    if dump:
        print("\n".join(_wa_scan_lines(scan)))
    return scan["candidates"]


def _wa_click_end_call_button_ui():
    for score, name, ctype, el in _wa_uia_end_call_candidates()[:_WA_CALL_MAX_CLICK_TRIES]:
        ok, how = _wa_uia_click(el)
        if ok:
            return "uia %s %s" % (how, name)
        print("[whatsapp_call] end-call UIA click fail %r: %s" % (name, how))
    return None


def _wa_click_end_call_button_vision():
    return _wa_guarded_vision_click(_WA_END_CALL_VISION_TARGET)


def _wa_end_call_fallback_xy():
    """Explicit [x_from_left, y_from_bottom] offsets, default OFF."""
    try:
        cfg = _load_json(CONFIG_PATH) or {}
        off = cfg.get("wa_end_call_button_offsets")
        if not isinstance(off, (list, tuple)) or len(off) != 2:
            print("[whatsapp_call] end-call coords fallback DISABLED (missing/invalid offsets)")
            return None
        return _wa_offset_click(off, end_call=True)
    except Exception as e:
        _wa_diagnostic("end-call coords config fail", e)
        return None


def _wa_end_call_probe():
    return _wa_call_probe(end_call=True)


def whatsapp_call_end(args=None):
    """End current call without spoken confirmation; never infer success from unknown OCR."""
    if _wa_call_wants_probe(args):
        return _wa_end_call_probe()
    _wa_focus_call_window()
    state, hint = _wa_call_state_note(wait=0.6)
    if state == WA_CALL_ABSENT:
        return "Boss, abhi koi WhatsApp call chal hi nahi rahi, kaatne ko kuch nahi hai."
    attempts = []
    if state == WA_CALL_DETECTED:
        for clicker in (_wa_click_end_call_button_ui, _wa_click_end_call_button_vision,
                        _wa_end_call_fallback_xy):
            try:
                note = clicker()
            except Exception as e:
                attempts.append(str(e)[:100])
                continue
            if not note:
                attempts.append(clicker.__name__ + " unavailable")
                continue
            state, hint = _wa_call_state_note()
            attempts.append("%s verify=%s: %s" % (note, state, hint))
            if state == WA_CALL_ABSENT:
                return "WhatsApp call kaat di."
    else:
        attempts.append("active call verify unknown: " + hint)
    return ("Call kaat nahi paya, fail: " + " ; ".join(attempts)
            + ". Debug: python comms_agent.py --end-call-probe")


def _wa_unpack_result(res):
    """_wa_open_chat_and_run apna 2-tuple (ok, note) bhi de sakta hai aur
    after_open ka 3-tuple (ok, note, state) bhi. Dono handle karo.
    Returns (ok, note, state)."""
    if not isinstance(res, (tuple, list)):
        return False, str(res), WA_CALL_UNKNOWN
    try:
        n = len(res)
    except Exception:
        return False, str(res), WA_CALL_UNKNOWN
    if n >= 3:
        return bool(res[0]), str(res[1]), str(res[2] or WA_CALL_UNKNOWN)
    if n == 2:
        return bool(res[0]), str(res[1]), WA_CALL_UNKNOWN
    return False, str(res), WA_CALL_UNKNOWN


def whatsapp_call(args):
    """WhatsApp VOICE/VIDEO call lagao - contact naam se resolve karo, chat
    kholo, phir header ka call button STRICT UIA -> vision -> coords chain se
    click karo. Har click ke BAAD call screen OCR se VERIFY hota hai; verify
    na hone pe jhoothi success NAHI bolta.
    Args: {contact: str, video: bool, probe: bool}"""
    args = args or {}
    target = _wa_call_target(args)
    video = _wa_call_wants_video(args)
    kind = "video call" if video else "voice call"

    if _wa_call_wants_probe(args):
        return _wa_call_probe(video)

    if not target:
        return "Kisko call karna hai? Contact ka naam bolo."

    # Naam se contact resolve (contacts.json) - phone optional hai,
    # WhatsApp me naam se search hoke chat khul jati hai.
    phone, _email = _resolve_contact(target)
    if phone:
        print("[whatsapp_call] contact resolved: %s (+91%s)" % (target, phone[-10:]))

    def _do_call(_pg, _clipboard, mode):
        _wa_focus_call_window()
        time.sleep(0.5)

        # Double-dial guard
        if _wa_call_already_active(video):
            return True, "call pehle se active thi, dobara dial nahi kiya", WA_CALL_DETECTED

        attempts = []
        clicked = False
        state = WA_CALL_UNKNOWN
        for clicker in (_wa_click_call_button_ui,
                        _wa_click_call_button_vision,
                        _wa_call_fallback_xy):
            try:
                note = clicker(video)
            except Exception as e:
                note = None
                print("[whatsapp_call] %s crash: %s" % (clicker.__name__, str(e)[:60]))
            if not note:
                attempts.append(clicker.__name__ + ": miss")
                continue
            clicked = True
            attempts.append(clicker.__name__ + ": " + str(note))
            state, hint = _wa_call_state_note(video)
            if state == WA_CALL_DETECTED:
                # Spoken reply me parentheses nahi (bolo.py TTS strip karta hai)
                print("[whatsapp_call] method note: " + str(note)
                      + " | verify: " + str(hint) + " | " + mode + " mode")
                return True, str(note), state
            print("[whatsapp_call] verify %s after %s (%s) - next layer try"
                  % (state, clicker.__name__, hint))

        # Koi bhi layer confirm nahi kar paya - ek aakhri check
        state, hint = _wa_call_state_note(video)
        if state == WA_CALL_DETECTED:
            print("[whatsapp_call] method note: final check verified (" + hint + ")")
            return True, "final check", state
        print("[whatsapp_call] method note: " + " ; ".join(attempts)
              + " | verify: " + str(state) + " | " + mode + " mode")
        if not clicked:
            return False, " ; ".join(attempts) or "koi click layer chala hi nahi", WA_CALL_NOCLICK
        return False, " ; ".join(attempts), state

    res = _wa_open_chat_and_run(target, after_open=_do_call)
    # after_open chala (3-tuple) ya chat hi nahi khuli (2-tuple) - dono handle
    chat_phase_only = not (isinstance(res, tuple) and len(res) >= 3)
    ok, note, state = _wa_unpack_result(res)
    print("[whatsapp_call] result: ok=%s state=%s note=%s" % (ok, state, str(note)[:90]))

    if chat_phase_only:
        # Chat hi nahi khuli - WhatsApp/login/app ka masla
        return (target + " ko " + kind + " nahi laga paya - fail: " + note + ". "
                "WhatsApp login ya app check karo, ya number save karo: "
                "save contact " + target + " number 10 digit")

    if ok:
        return ("WhatsApp me " + target + " ko " + kind + " laga diya. "
                "Ringing ho raha hoga.")

    if state == WA_CALL_NOCLICK:
        return (target + " ko " + kind + " nahi laga paya, fail: call button click "
                "hi nahi hua, UIA aur vision dono me button nahi mila. "
                "Chat kholke khud try karo, ya debug chalao: "
                "python comms_agent.py --call-probe")

    if state == WA_CALL_ABSENT:
        return (target + " ko " + kind + " nahi laga paya, fail: call button click "
                "hua par calling screen nahi aayi. Chat kholke khud try karo, "
                "ya debug chalao: python comms_agent.py --call-probe")

    # OCR chala hi nahi - jhooth nahi bolenge, par hard fail bhi nahi
    return (target + " ke chat me " + kind + " button dabaya, par call confirm "
            "nahi kar paya. WhatsApp khud check kar lo.")


def whatsapp_reply(args):
    """Last chat me reply. Args: {message}"""
    message = (args.get("message") or args.get("text") or "").strip()
    if not message:
        return "Kya reply karna hai?"
    web_url = "https://web.whatsapp.com/"
    try:
        webbrowser.open(web_url)
    except Exception:
        return "WhatsApp Web khul hi nahi paaya."
    time.sleep(3)
    try:
        import pyautogui
        try:
            import pyperclip
            pyperclip.copy(message)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pyautogui.write(message, interval=0.02)
        time.sleep(0.3)
        pyautogui.press("enter")
        return f"Reply bhej diya (last chat): \"{message[:50]}\""
    except Exception as e:
        return f"WhatsApp Web khula, message type nahi paya ({str(e)[:60]}). Message khud paste kar do."


if __name__ == "__main__":
    # CALL DEBUG: python comms_agent.py [--video] --call-probe
    # WhatsApp ke open chat me strict UIA candidates + OCR dump karta hai,
    # kuch click NAHI karta. Output Boss bhejta hai -> weights tune hote hain.
    if "--end-call-probe" in sys.argv:
        _wa_end_call_probe()
        sys.exit(0)
    if "--call-probe" in sys.argv:
        _wa_call_probe("--video" in sys.argv)
        sys.exit(0)
    print("=== Phase 5 comms_agent TEST ===")
    print(calendar_add({"title": "Team standup", "when": "tomorrow 9 am"}))
    print(calendar_add({"title": "Pappu birthday", "when": "25 dec"}))
    print(calendar_list({"when": "week"}))
    print(save_contact({"name": "Ravi", "phone": "9876543210"}))
    print(_resolve_contact("Ravi"))
    print(calendar_delete({"title": "standup"}))
    print("Config path:", CONFIG_PATH)
