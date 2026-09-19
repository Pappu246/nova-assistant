"""
NOVA Web Dashboard - FastAPI backend
"""
import os
import sys
import json
import time
import asyncio
import datetime
import threading
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

try:
    import psutil
    _PSUTIL = True
except Exception:
    _PSUTIL = False

BASE = Path(__file__).parent
WEB = BASE / "web"
WEB.mkdir(exist_ok=True)

app = FastAPI(title="NOVA")
app.mount("/static", StaticFiles(directory=str(WEB)), name="static")

# ---- Global state ----
STATE = {
    "status": "Ready",
    "user_text": "",
    "nova_text": "",
    "history": [],
    "tasks": [],
    "start_time": time.time(),
    "voice_active": False,
    "wake_detected": False,
}

# Lazy import brain to avoid circular imports
_brain = None
def _get_brain():
    global _brain
    if _brain is None:
        try:
            from brain import ask_nova
            _brain = ask_nova
        except Exception as e:
            print(f"[server] brain load fail: {e}")
            def _stub(m, h=None):
                return f"Brain load nahi hua: {e}"
            _brain = _stub
    return _brain


# ---------- API ROUTES ----------

@app.get("/")
def index():
    return FileResponse(str(WEB / "index.html"))


@app.get("/api/state")
def get_state():
    return STATE


@app.get("/api/status")
def get_status():
    data = {
        "uptime": int(time.time() - STATE["start_time"]),
        "status": STATE["status"],
    }
    if _PSUTIL:
        try:
            data["cpu"] = int(psutil.cpu_percent(interval=0.1))
            data["ram"] = int(psutil.virtual_memory().percent)
            data["storage"] = int(psutil.disk_usage("C:\\").percent)
            net = psutil.net_io_counters()
            data["network"] = int((net.bytes_sent + net.bytes_recv) / (1024 * 1024))
        except Exception:
            pass
    return data


@app.get("/api/weather")
def get_weather(city: str = "Jaipur"):
    try:
        import urllib.request, urllib.parse
        geo = "https://geocoding-api.open-meteo.com/v1/search?name=" + urllib.parse.quote(city) + "&count=1"
        with urllib.request.urlopen(geo, timeout=5) as r:
            g = json.loads(r.read())
        if not g.get("results"):
            return {"error": "location not found"}
        lat = g["results"][0]["latitude"]
        lon = g["results"][0]["longitude"]
        w = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        with urllib.request.urlopen(w, timeout=5) as r:
            d = json.loads(r.read())
        return {
            "city": city,
            "temp": d["current"]["temperature_2m"],
            "code": d["current"]["weather_code"],
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/chat")
async def chat(payload: dict):
    msg = (payload.get("message") or "").strip()
    if not msg:
        return {"reply": "Kuch bola nahi"}

    STATE["user_text"] = msg
    STATE["status"] = "Soch raha hoon..."
    ask = _get_brain()
    try:
        reply = await asyncio.get_event_loop().run_in_executor(None, ask, msg, None)
    except Exception as e:
        reply = f"Error: {e}"

    STATE["nova_text"] = reply
    STATE["status"] = "Ready"
    STATE["history"].insert(0, {
        "user": msg,
        "nova": reply,
        "time": datetime.datetime.now().strftime("%I:%M %p"),
    })
    STATE["history"] = STATE["history"][:20]
    return {"reply": reply}


@app.post("/api/speak")
async def speak_endpoint(payload: dict):
    text = (payload.get("text") or "").strip()
    if not text:
        return {"ok": False}
    try:
        from bolo import speak, stop_speaking
        import threading as _t

        def _speak_thread():
            try:
                from suno import listen_for_stop
                stop_event = _t.Event()

                def _listener():
                    try:
                        listen_for_stop(stop_event, timeout_sec=60)
                    except Exception as e:
                        print(f"[stop listener] {e}")

                def _watch():
                    while not stop_event.is_set():
                        stop_event.wait(0.15)
                        if stop_event.is_set():
                            stop_speaking()
                            break

                _t.Thread(target=_listener, daemon=True).start()
                _t.Thread(target=_watch, daemon=True).start()

                speak(text)
                stop_event.set()
            except Exception as e:
                print(f"[speak thread] {e}")

        threading.Thread(target=_speak_thread, daemon=True).start()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice/start")
async def voice_start():
    def _run():
        try:
            import main as nova_main
            nova_main.voice_mode()
        except Exception as e:
            print(f"[voice] fail: {e}")
    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True}


@app.get("/api/history")
def get_history():
    return STATE["history"]


@app.get("/api/tasks")
def get_tasks():
    return STATE["tasks"]


@app.post("/api/tasks")
async def add_task(payload: dict):
    t = (payload.get("title") or "").strip()
    if t:
        STATE["tasks"].append({"title": t, "done": False})
    return STATE["tasks"]


@app.post("/api/tasks/{idx}/toggle")
async def toggle_task(idx: int):
    if 0 <= idx < len(STATE["tasks"]):
        STATE["tasks"][idx]["done"] = not STATE["tasks"][idx]["done"]
    return STATE["tasks"]




@app.post("/api/voice/activate")
async def voice_activate():
    """Orb click - ek baar sunno."""
    STATE["voice_active"] = True
    STATE["status"] = "Listening..."

    def _run_once():
        try:
            from suno import listen
            from brain import ask_nova
            from bolo import speak

            STATE["status"] = "Sun raha hoon..."
            user_input = listen()
            STATE["voice_active"] = False
            if not user_input:
                STATE["status"] = "Kuch suna nahi"
                return

            STATE["user_text"] = user_input
            STATE["status"] = "Soch raha hoon..."
            reply = ask_nova(user_input, None)
            STATE["nova_text"] = reply
            STATE["status"] = "Bol raha hoon..."
            STATE["history"].insert(0, {
                "user": user_input,
                "nova": reply,
                "time": datetime.datetime.now().strftime("%I:%M %p"),
            })
            STATE["history"] = STATE["history"][:20]
            speak(reply)
            STATE["status"] = "Ready"
        except Exception as e:
            STATE["voice_active"] = False
            STATE["status"] = f"Error: {str(e)[:60]}"
            print(f"[voice activate] {e}")

    threading.Thread(target=_run_once, daemon=True).start()
    return {"ok": True}


@app.get("/api/voice/state")
def voice_state():
    return {
        "voice_active": STATE.get("voice_active", False),
        "wake_detected": STATE.get("wake_detected", False),
        "status": STATE["status"],
    }


@app.post("/api/wake/ping")
async def wake_ping():
    """Wake word detect hua - dashboard ko batao."""
    STATE["wake_detected"] = True
    STATE["status"] = "Wake word suna!"
    import time as _t
    def _reset():
        _t.sleep(2)
        STATE["wake_detected"] = False
    threading.Thread(target=_reset, daemon=True).start()
    return {"ok": True}


# ---------- WEBSOCKET (live updates) ----------

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = {
                "status": STATE["status"],
                "user": STATE["user_text"],
                "nova": STATE["nova_text"],
                "voice_active": STATE.get("voice_active", False),
                "wake_detected": STATE.get("wake_detected", False),
            }
            if _PSUTIL:
                try:
                    data["cpu"] = int(psutil.cpu_percent(interval=None))
                    data["ram"] = int(psutil.virtual_memory().percent)
                    data["storage"] = int(psutil.disk_usage("C:\\").percent)
                except Exception:
                    pass
            await ws.send_json(data)
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ---------- RUN ----------

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  NOVA Web Dashboard")
    print("  http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
