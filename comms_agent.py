"""
NOVA Comms Agent - Phase 5: Email, Calendar, WhatsApp.
Sab kuch local config se (Gmail App Password), credentials kabhi code me nahi.
"""
import os
import json
import re
import time
import datetime
import threading
import webbrowser
import urllib.parse

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
    except Exception:
        try:
            w.minimize()
            time.sleep(0.3)
            w.maximize()
        except Exception:
            pass


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
    try:
        if desktop:
            os.system("start whatsapp://")
            mode = "desktop"
        else:
            webbrowser.open("https://web.whatsapp.com/")
            mode = "web"
    except Exception:
        pass
    # Window ka wait karo
    wins = []
    deadline = time.time() + wait_load
    while time.time() < deadline:
        time.sleep(1)
        try:
            wins = [w for w in gw.getWindowsWithTitle("WhatsApp") if w.visible]
        except Exception:
            wins = []
        if wins:
            break
    if not wins:
        return False, "WhatsApp window khula nahi (app install / QR login check karo)"
    # Desktop app ko prefer karo exact title se
    exact = [w for w in wins if (w.title or "").strip() == "WhatsApp"]
    w = exact[0] if exact else wins[0]
    _wa_activate(w)
    time.sleep(1.2)
    old_pause, old_failsafe = pyautogui.PAUSE, pyautogui.FAILSAFE
    pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = False
    try:
        pyautogui.hotkey("esc")
        time.sleep(0.4)
        if mode == "desktop":
            pyautogui.hotkey("ctrl", "f")   # Desktop: search chats
        else:
            # Web: search box click (configurable coords) fallback keyboard combo
            cfg = _load_json(CONFIG_PATH)
            xy = cfg.get("wa_web_search_xy")
            clicked = False
            if xy and len(xy) == 2:
                try:
                    pyautogui.click(int(xy[0]), int(xy[1]))
                    clicked = True
                except Exception:
                    clicked = False
            if not clicked:
                try:
                    pyautogui.click(w.left + 150, w.top + 130)
                except Exception:
                    pyautogui.hotkey("ctrl", "alt", "/")
        time.sleep(0.8)
        # Naam paste (unicode safe) -> pehla result khulta hai
        pyperclip.copy(str(name))
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(1.2)
        if callable(after_open):
            return after_open(pyautogui, pyperclip, mode)
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
# Flow: contact naam se resolve -> chat kholo (search -> type naam -> enter,
# wahi _wa_open_chat_and_run jo whatsapp_send use karta hai) -> chat header ke
# upar-right wale call button pe click:
#   1) pywinauto/ui_agent se precise try (element name match)
#   2) fallback: vision_click (VLM, active window = WhatsApp)
# Video call ke liye args me video=true.

WA_CALL_STATE_WAIT_SEC = 2.5   # call screen check se pehle thoda wait

# pywinauto/UIA element names (WhatsApp Desktop approx. inhi naam se expose karta hai)
_WA_CALL_UI_NAMES = {
    False: ["Voice call", "Audio call", "voice_call", "Voice call button",
            "Call", "voice call"],
    True: ["Video call", "Video Call", "video_call", "Video call button",
           "video call"],
}

# VLM (vision_click) ke liye English visual description - header ke upar-right
_WA_CALL_VISION_TARGETS = {
    False: ("voice call button: telephone handset icon in the top-right header of "
            "the open WhatsApp chat, LEFT of the video camera and menu buttons"),
    True: ("video call button: video camera icon in the top-right header of the "
           "open WhatsApp chat, next to the voice call button"),
}

# Call screen pe ye text dikhta hai (best-effort confirmation)
_WA_CALL_SCREEN_HINTS = ("calling", "ringing", "end call", "end video call",
                         "call ended", "no answer", "audio call", "video call")


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


def _wa_focus_call_window():
    """CALL FIX (NOVA): click se pehle WhatsApp window front pe lao,
    warna active-window vision click galat window pe chala jata hai."""
    try:
        import app_control
        r = app_control.focus_window("WhatsApp")
        print("[whatsapp_call] focus: " + str(r)[:60])
        return str(r)
    except Exception as e:
        print("[whatsapp_call] focus skip: " + str(e)[:50])
        return ""


def _wa_click_call_button_ui(video=False):
    """Layer 1: pywinauto/ui_agent se precise call button click.
    Returns note (str) on success, warna None."""
    try:
        import ui_agent
    except Exception as e:
        print("[whatsapp_call] ui_agent unavailable: " + str(e)[:60])
        return None
    if getattr(ui_agent, "IS_WIN", True) is False:
        return None
    for name in _WA_CALL_UI_NAMES[bool(video)]:
        try:
            r = str(ui_agent.click_element({"window": "WhatsApp", "element": name}))
        except Exception as e:
            print(f"[whatsapp_call] ui click '{name}' fail: {str(e)[:60]}")
            continue
        low = r.lower()
        if "clicked" in low or "click kiya" in low or "vision click" in low:
            print(f"[whatsapp_call] ui_agent click OK ('{name}'): {r[:70]}")
            return r[:80]
    return None


def _wa_click_call_button_vision(video=False):
    """Layer 2 (fallback): VLM vision_click se call button pe click.
    Returns note (str) on success, warna None."""
    try:
        import vision_agent
    except Exception as e:
        print("[whatsapp_call] vision_agent unavailable: " + str(e)[:60])
        return None
    target = _WA_CALL_VISION_TARGETS[bool(video)]
    try:
        res = vision_agent.vision_click(target, dry_run=False, use_active_window=True)
    except Exception as e:
        print("[whatsapp_call] vision_click fail: " + str(e)[:70])
        return None
    if isinstance(res, dict) and res.get("ok"):
        note = f"vision_click ({res.get('x')},{res.get('y')})"
        if res.get("verified"):
            note += " screen change verify hua"
        print("[whatsapp_call] vision click OK: " + note)
        return note
    print("[whatsapp_call] vision click miss: " + str(res)[:80])
    return None


def _wa_call_state_note(video=False):
    """Best-effort: call screen aaya? Active window OCR me 'Calling/Ringing/
    End call' jaisa text dhundo. Koi text na mile to khaali string."""
    try:
        time.sleep(WA_CALL_STATE_WAIT_SEC)
        import vision_control
        text = str(vision_control.read_screen(region_mode="active") or "")
    except Exception as e:
        print("[whatsapp_call] state check skip: " + str(e)[:60])
        return ""
    low = text.lower()
    for hint in _WA_CALL_SCREEN_HINTS:
        if hint in low:
            return f"Call screen confirm: '{hint}' dikha."
    return ""


def whatsapp_call(args):
    """WhatsApp VOICE/VIDEO call lagao - contact ko naam se resolve karo,
    chat kholo (search -> naam -> enter), phir header ke call button pe click
    (pehle pywinauto/ui_agent precise try, phir vision_click fallback).
    Args: {contact: str, video: bool} - video=true se video call."""
    args = args or {}
    target = _wa_call_target(args)
    video = _wa_call_wants_video(args)
    kind = "video call" if video else "voice call"
    if not target:
        return "Kisko call karna hai? Contact ka naam bolo."
    # Naam se contact resolve (contacts.json) - phone optional hai,
    # WhatsApp me naam se search hoke chat khul jati hai.
    phone, _email = _resolve_contact(target)
    if phone:
        print(f"[whatsapp_call] contact resolved: {target} (+91{phone[-10:]})")

    def _do_call(_pg, _clipboard, mode):
        _wa_focus_call_window()
        time.sleep(0.5)
        ui_note = _wa_click_call_button_ui(video)
        if ui_note:
            return True, f"pywinauto se {kind} button, {ui_note} [{mode} mode]"
        print("[whatsapp_call] pywinauto se button nahi mila - vision_click fallback")
        vis_note = _wa_click_call_button_vision(video)
        if vis_note:
            return True, f"{vis_note} [{mode} mode]"
        return False, (f"chat khul gaya par {kind} button click nahi hua "
                       f"(pywinauto aur vision dono fail) [{mode} mode]")

    ok, note = _wa_open_chat_and_run(target, after_open=_do_call)
    if not ok:
        return (f"'{target}' ko {kind} nahi laga paya - fail ({note}). "
                f"WhatsApp login/app check karo, ya number save karo: "
                f"save contact {target} number <10 digit>")
    state_note = _wa_call_state_note(video)
    tail = (" " + state_note) if state_note else " Call screen khud check kar lo."
    return (f"WhatsApp me '{target}' ko {kind} laga diya ({note}). "
            f"Ringing ho raha hoga.{tail}")


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
    print("=== Phase 5 comms_agent TEST ===")
    print(calendar_add({"title": "Team standup", "when": "tomorrow 9 am"}))
    print(calendar_add({"title": "Pappu birthday", "when": "25 dec"}))
    print(calendar_list({"when": "week"}))
    print(save_contact({"name": "Ravi", "phone": "9876543210"}))
    print(_resolve_contact("Ravi"))
    print(calendar_delete({"title": "standup"}))
    print("Config path:", CONFIG_PATH)
