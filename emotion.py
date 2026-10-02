"""
NOVA Phase 6 - Emotion & Personality
- Text se emotion detect (Hinglish + English rules)
- Mood log (memory + history) - NOVA ko pata hai Boss ka mood
- Reply ka tone adjust (empathy ack sirf jab zarurat)
- edge-tts voice params (rate/pitch) emotion ke hisaab se
"""
import os
import json
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOOD_PATH = os.path.join(BASE_DIR, "mood_history.json")

# emotion -> (edge-tts rate, pitch)
_VOICE = {
    "neutral":  ("+5%",  "+0Hz"),
    "happy":    ("+8%",  "+20Hz"),
    "excited":  ("+15%", "+30Hz"),
    "sad":      ("-12%", "-30Hz"),
    "angry":    ("+8%",  "+10Hz"),
    "stressed": ("+3%",  "+0Hz"),
    "tired":    ("-10%", "-20Hz"),
    "worried":  ("+0%",  "-10Hz"),
    "affectionate": ("+5%", "+10Hz"),
}

# keyword rules - order matters (specific pehle)
_RULES = [
    ("excited",  ["excited", "utsuk", "can't wait", "cant wait", "let's go", "letss go",
                  "yay", "party", "maza aane wala", "boom"]),
    ("angry",    ["gussa", "angry", "pagal kar", "irritat", "chidh", "nafrat",
                  "bakwas", "frustrat", "annoy", "chu*iyapa", "galat kar"]),
    ("worried",  ["worry", "worried", "ghabra", "darr", "scared", "dar lag",
                  "fikar", "chinta"]),
    ("stressed", ["tension", "stress", "pressure", "deadline", "pareshan",
                  "overwhelm", "tang aa", "pareshaani", "headache"]),
    ("sad",      ["udaas", "sad", "dukhi", "dil tuta", "rona", "roti", "akela",
                  "miss kar", "khali khali", "depress", "heartbreak", "bura lag"]),
    ("tired",    ["thak", "tired", "neend", "sleepy", "burnout", "exhaust",
                  "bhaari", "aatish", "lag gaye"]),
    ("affectionate", ["love you", "pyar", "dost", "yaar", "care kar", "dil se"]),
    ("happy",    ["khush", "happy", "maza", "mast", "badhiya", "shukriya", "thanks",
                  "kamaal", "great", "sahi hai", "perfect", "shandar", "zabardast"]),
]

_INTENSIFIERS = ["bahut", "bohot", "bhot", "bilkul", "so much", "too much",
                 "extremely", "very", "kitna", "bahot"]

# In emotions pe hi empathy ack lagta hai (intensity ke saath)
_ACK_EMOTIONS = {"sad", "angry", "stressed", "tired", "worried"}

_ACKS = {
    "sad":      ["Samajh sakta hoon Boss.", "Mood off hai shayad, main hoon na."],
    "angry":    ["Pareshaan mat ho Boss, sambhalte hain.", "Gussa thik hai, ab solution pe chalte hain."],
    "stressed": ["Tension mat lo Boss, aaram se karte hain.", "Halke me lete hain, main help karunga."],
    "tired":    ["Thak gaye ho shayad Boss, halke me lenge.", "Aaram kar lo, kaam baad me bhi ho jayega."],
    "worried":  ["Ghabrao mat Boss, sab theek hoga.", "Fikar chhodo, ek-ek karke dekhte hain."],
}


def detect_emotion(text):
    """Text -> {emotion, intensity, cues}. Rule-based (fast, offline)."""
    low = (text or "").lower()
    best = ("neutral", 0.0, [])
    for emotion, words in _RULES:
        cues = [w for w in words if w in low]
        if cues:
            intensity = 0.5 + min(len(cues) * 0.15, 0.3)
            if any(x in low for x in _INTENSIFIERS):
                intensity = min(intensity + 0.3, 1.0)
            if intensity > best[1]:
                best = (emotion, round(intensity, 2), cues)
    return {"emotion": best[0], "intensity": best[1], "cues": best[2]}


def voice_params(d):
    """Emotion -> (rate, pitch) for edge-tts."""
    if isinstance(d, str):
        d = {"emotion": d}
    return _VOICE.get((d or {}).get("emotion", "neutral"), _VOICE["neutral"])


def apply_voice(d):
    """bolo ke EDGE_RATE/EDGE_PITCH update (next speak pe apply)."""
    try:
        import bolo
        rate, pitch = voice_params(d)
        bolo.EDGE_RATE = rate
        bolo.EDGE_PITCH = pitch
        return True
    except Exception:
        return False


def apply_ack(d, reply):
    """Chat reply ke aage short empathy prefix - sirf notable emotions pe."""
    try:
        if not d or d.get("emotion") not in _ACK_EMOTIONS:
            return reply
        if d.get("intensity", 0) < 0.6:
            return reply
        acks = _ACKS.get(d["emotion"])
        if not acks:
            return reply
        ack = acks[0] if d.get("intensity", 0) < 0.85 else acks[-1]
        return ack + " " + str(reply)
    except Exception:
        return reply


def log_mood(d, source="chat"):
    """Mood ko memory + history me save."""
    try:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        entry = {"emotion": (d or {}).get("emotion", "neutral"),
                 "intensity": (d or {}).get("intensity", 0.0),
                 "at": now, "source": source}
        hist = []
        if os.path.exists(MOOD_PATH):
            try:
                with open(MOOD_PATH, "r", encoding="utf-8") as f:
                    hist = json.load(f)
            except Exception:
                hist = []
        hist.append(entry)
        hist = hist[-30:]
        with open(MOOD_PATH, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=1, ensure_ascii=False)
        try:
            import memory
            memory.save_fact("last_mood", f"{entry['emotion']} ({now[11:16]})", "mood")
        except Exception:
            pass
        return entry
    except Exception as e:
        print(f"[emotion] log fail: {e}")
        return None


def mood_context(threshold=0.55):
    """LLM prompt ke liye chhota mood line (sirf notable mood pe)."""
    try:
        if not os.path.exists(MOOD_PATH):
            return ""
        with open(MOOD_PATH, "r", encoding="utf-8") as f:
            hist = json.load(f)
        if not hist:
            return ""
        last = hist[-1]
        if last["emotion"] == "neutral" or last.get("intensity", 0) < threshold:
            return ""
        return (f"\n[Boss mood alert]: abhi '{last['emotion']}' feel kar raha hai "
                f"({last['at'][11:16]}) - jawaaz ka style usi hisaab se rakho.")
    except Exception:
        return ""


def mood_history_tool(args=None):
    """Tool: recent mood report."""
    try:
        if not os.path.exists(MOOD_PATH):
            return "Abhi tak koi mood record nahi hua."
        with open(MOOD_PATH, "r", encoding="utf-8") as f:
            hist = json.load(f)
        if not hist:
            return "Abhi tak koi mood record nahi hua."
        recent = hist[-7:][::-1]
        lines = ["Boss ka recent mood:"]
        for h in recent:
            lines.append(f"  {h['at'][11:16]} - {h['emotion']} (intensity {h.get('intensity', 0)})")
        return "\n".join(lines)
    except Exception as e:
        return f"Mood history fail: {str(e)[:60]}"


def tool_mood(args):
    return mood_history_tool(args)


if __name__ == "__main__":
    print("=== Phase 6 emotion TEST ===")
    for s in ["yaar bahut udaas hoon aaj",
              "bilkul gussa aa raha hai tumse",
              "chal yaar maza aane wala hai party!",
              "deadline ki tension ho rahi hai bahut",
              "thak gaya hoon yaar aaj",
              "time kya hai"]:
        d = detect_emotion(s)
        print(f"  {d['emotion']:>13} ({d['intensity']}) <- {s[:40]!r}")
    d = detect_emotion("bahut udaas hoon")
    print("voice:", voice_params(d), "| ack:", apply_ack(d, "Theek ho jayega."))
    log_mood(d)
    print(mood_context())
    print(mood_history_tool())
