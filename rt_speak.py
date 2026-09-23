"""
NOVA Real-Time TTS - streaming sentence-by-sentence.
LLM ke tokens buffer karta, sentence complete hone pe turant bolta.
Parallel queue - bolna chalta rahe jab tak naye tokens aa rahe.
"""
import os
import re
import tempfile
import time
import threading
import queue

import numpy as np

try:
    import edge_tts
    _EDGE = True
except Exception:
    _EDGE = False

try:
    from playsound3 import playsound
    _PLAY = True
except Exception:
    _PLAY = False

try:
    import pygame
    _PYGAME = True
except Exception:
    _PYGAME = False


VOICE = "hi-IN-MadhurNeural"
RATE = "+5%"
PITCH = "+0Hz"

# Stop flag for barge-in
_stop_flag = threading.Event()
_speaking_flag = threading.Event()


def stop_speaking():
    """Barge-in: TTS turant rok do."""
    _stop_flag.set()
    try:
        if _PYGAME and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
    except Exception:
        pass


def is_speaking():
    return _speaking_flag.is_set()


def _clean_for_speech(text):
    """Emoji, markdown cleanup for TTS."""
    if not text:
        return ""
    t = text
    # Remove markdown
    t = re.sub(r"```[\s\S]*?```", " code block ", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\|", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"https?://\S+", " link ", t)
    # Remove emoji
    try:
        emoji = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002700-\U000027BF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FAFF"
            "\U00002600-\U000026FF"
            "]+",
            flags=re.UNICODE,
        )
        t = emoji.sub("", t)
    except Exception:
        pass
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _edge_tts_to_file(text, path):
    """Generate MP3 file with edge-tts."""
    try:
        import asyncio

        async def _gen():
            c = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
            await c.save(path)

        asyncio.run(_gen())
        return os.path.exists(path) and os.path.getsize(path) > 500
    except Exception as e:
        print("[rt_speak] edge-tts fail: " + str(e)[:60])
        return False


def _play_and_wait(path):
    """Play MP3 and wait. Respects stop flag for barge-in."""
    if _PLAY:
        try:
            playsound(path, block=True)
            return True
        except Exception as e:
            print("[rt_speak] playsound fail: " + str(e)[:60])

    if _PYGAME:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.7)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if _stop_flag.is_set():
                    pygame.mixer.music.stop()
                    return True
                pygame.time.wait(60)
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            return True
        except Exception as e:
            print("[rt_speak] pygame fail: " + str(e)[:60])
    return False


# ============ SPEAK WORKER (QUEUE) ============

_speak_queue = queue.Queue()
_worker_started = False


def _speak_worker():
    """Background worker: pull sentences, speak them."""
    while True:
        item = None
        try:
            item = _speak_queue.get()
            if item is None:
                _speak_queue.task_done()
                break

            text, done_callback = item
            print("[rt_speak] speaking: " + text[:60])

            if _stop_flag.is_set():
                if done_callback:
                    done_callback()
                _speak_queue.task_done()
                continue

            text = _clean_for_speech(text)
            if not text:
                if done_callback:
                    done_callback()
                _speak_queue.task_done()
                continue

            _speaking_flag.set()

            path = os.path.join(
                tempfile.gettempdir(),
                "nova_rt_" + str(int(time.time() * 1000)) + ".mp3",
            )

            if _edge_tts_to_file(text, path):
                print("[rt_speak] playing: " + path)
                _play_and_wait(path)
                try:
                    os.remove(path)
                except Exception:
                    pass
            else:
                print("[rt_speak] TTS gen failed")

            _speaking_flag.clear()
            if done_callback:
                done_callback()

        except Exception as e:
            print("[rt_speak] worker error: " + str(e)[:80])
            _speaking_flag.clear()
        finally:
            # CRITICAL: always mark done
            try:
                _speak_queue.task_done()
            except Exception:
                pass


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    t = threading.Thread(target=_speak_worker, daemon=True)
    t.start()


def enqueue(text, done_callback=None):
    """Add text to speak queue."""
    _ensure_worker()
    _speak_queue.put((text, done_callback))


def speak_streaming(token_iterator):
    """
    Consume a token iterator, speak sentence-by-sentence.

    Args:
        token_iterator: yields (type, data) tuples - same as rt_brain.stream_reply
                       ('token', 'chunk'), ('done', 'full'), ('error', 'msg')

    Returns: full text (str)
    """
    _ensure_worker()
    _stop_flag.clear()

    sentence_buffer = ""
    full_text = ""
    SENTENCE_MIN = 15       # min chars before considering flush
    SENTENCE_END = re.compile(r"[.!?।]\s*$")

    for event in token_iterator:
        etype = event[0]

        if etype == "token":
            chunk = event[1]
            sentence_buffer += chunk
            full_text += chunk

            # Flush at sentence boundary OR when buffer grows too long
            stripped = sentence_buffer.strip()
            if stripped and (
                SENTENCE_END.search(stripped)
                or len(stripped) >= 80
            ):
                enqueue(stripped)
                sentence_buffer = ""

        elif etype == "done":
            # Flush remaining
            if sentence_buffer.strip():
                enqueue(sentence_buffer.strip())
                sentence_buffer = ""

            # Wait for queue to drain
            _speak_queue.join()
            return full_text

        elif etype == "error":
            print("[rt_speak] error: " + event[1])

    if sentence_buffer.strip():
        enqueue(sentence_buffer.strip())
    _speak_queue.join()
    return full_text


# ============ TEST ============

if __name__ == "__main__":
    print("=" * 55)
    print("  rt_speak.py TEST")
    print("=" * 55)
    print()

    # Test 1: Direct speak
    print("Test 1: Direct speak")
    _ensure_worker()
    enqueue("Namaste Boss, main NOVA hoon.")
    enqueue("Aaj mausam bahut accha hai.")
    _speak_queue.join()
    print("  Done")
    print()

    # Test 2: Streaming (simulated)
    print("Test 2: Streaming tokens (sentence-by-sentence)")
    def fake_tokens():
        chunks = [
            "Chrome kholne ", "ke liye ", "confirm ", "karna ",
            "hai Boss. ", "Haan ", "ya ", "nahi ", "bolo.",
            " Aap bhi ", "theek hain ", "na?",
        ]
        import time as t
        for c in chunks:
            yield ("token", c)
            t.sleep(0.08)
        yield ("done", "")

    t0 = time.time()
    full = speak_streaming(fake_tokens())
    print("  Full text: " + full)
    print("  Time: " + str(round(time.time() - t0, 2)) + "s")
    print()
    print("=" * 55)
