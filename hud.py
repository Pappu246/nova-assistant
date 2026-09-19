"""
NOVA HUD v3 - Compact circular floating orb.
"""
import tkinter as tk
import threading
import queue
import datetime
import math


class NovaHUD:
    def __init__(self):
        self.q = queue.Queue()
        self.root = None
        self.running = False
        self.state = "Ready"
        self.angle = 0
        self.wave_phase = 0
        self.pulse = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def update(self, key, value):
        self.q.put((key, str(value)))

    def _run(self):
        try:
            self.root = tk.Tk()
        except Exception as e:
            print(f"[hud] fail: {e}")
            return

        self.root.title("NOVA")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg="#000000")

        W, H = 260, 260
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{sw-W-30}+{sh-H-80}")

        self.canvas = tk.Canvas(self.root, width=W, height=H,
                                 bg="#050810", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        cx, cy = W // 2, H // 2

        # Outer rotating rings
        self.rings = []
        for r in [115, 100, 85]:
            ring = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                            outline="#00d4ff", width=1,
                                            dash=(3, 8))
            self.rings.append(ring)

        # Glow layers
        self.glow3 = self.canvas.create_oval(cx-70, cy-70, cx+70, cy+70,
                                              fill="#001a3a", outline="")
        self.glow2 = self.canvas.create_oval(cx-58, cy-58, cx+58, cy+58,
                                              fill="#003366", outline="")
        self.glow1 = self.canvas.create_oval(cx-45, cy-45, cx+45, cy+45,
                                              fill="#0066aa", outline="")

        # Core orb
        self.core = self.canvas.create_oval(cx-32, cy-32, cx+32, cy+32,
                                              fill="#00d4ff", outline="#66e0ff",
                                              width=2)

        # NOVA text center
        self.orb_text = self.canvas.create_text(cx, cy, text="NOVA",
                                                   fill="#ffffff",
                                                   font=("Consolas", 13, "bold"))

        # Status text below orb
        self.status_text = self.canvas.create_text(cx, cy + 85, text="Ready",
                                                     fill="#00ff88",
                                                     font=("Consolas", 10, "bold"))

        # Time top
        self.time_text = self.canvas.create_text(cx, 20, text="--:--",
                                                    fill="#00d4ff",
                                                    font=("Consolas", 11, "bold"))

        # Drag
        self._drag = {"x": 0, "y": 0}
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<Button-3>", lambda e: self.root.destroy())

        self._animate()
        self._tick()
        self.root.after(100, self._process_q)
        self.root.mainloop()

    def _drag_start(self, e):
        self._drag["x"] = e.x_root - self.root.winfo_x()
        self._drag["y"] = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self._drag["x"]
        y = e.y_root - self._drag["y"]
        self.root.geometry(f"+{x}+{y}")

    def _animate(self):
        try:
            W, H = 260, 260
            cx, cy = W // 2, H // 2

            self.angle += 2
            self.wave_phase += 0.15
            self.pulse += 0.08

            # Rotate rings
            for i, ring in enumerate(self.rings):
                phase = self.angle + i * 40
                r = [115, 100, 85][i] + math.sin(math.radians(phase)) * 3
                self.canvas.coords(ring, cx-r, cy-r, cx+r, cy+r)

            # State colors
            colors = {
                "Ready":     ("#00ff88", "#00d4ff", "#003366", "#001a3a"),
                "Listening": ("#ff3366", "#ff3366", "#4d001a", "#1a0008"),
                "Thinking":  ("#ffaa00", "#ffaa00", "#4d3300", "#1a0f00"),
                "Speaking":  ("#00d4ff", "#a855f7", "#330066", "#0a0033"),
                "Stopped":   ("#7a8ba8", "#4a5975", "#1a2038", "#0a0e1a"),
            }
            dot_color, orb_color, glow_med, glow_dark = colors.get(
                self.state, colors["Ready"])

            self.canvas.itemconfig(self.status_text, fill=dot_color, text=self.state)
            for ring in self.rings:
                self.canvas.itemconfig(ring, outline=orb_color)
            self.canvas.itemconfig(self.core, fill=orb_color, outline=orb_color)
            self.canvas.itemconfig(self.glow1, fill=glow_med)
            self.canvas.itemconfig(self.glow2, fill=glow_med)
            self.canvas.itemconfig(self.glow3, fill=glow_dark)

            # Pulse effect
            scale = 1.0
            if self.state == "Listening":
                scale = 1.0 + 0.15 * abs(math.sin(self.wave_phase * 0.6))
            elif self.state == "Speaking":
                scale = 1.0 + 0.18 * abs(math.sin(self.wave_phase * 0.5))
            elif self.state == "Thinking":
                scale = 1.0 + 0.08 * abs(math.sin(self.wave_phase * 0.4))
            else:
                scale = 1.0 + 0.04 * abs(math.sin(self.pulse * 0.5))

            # Scale glows
            for r, item in [(70, self.glow3), (58, self.glow2), (45, self.glow1), (32, self.core)]:
                rr = int(r * scale)
                self.canvas.coords(item, cx-rr, cy-rr, cx+rr, cy+rr)

            self.root.after(50, self._animate)
        except Exception:
            pass

    def _tick(self):
        try:
            now = datetime.datetime.now().strftime("%I:%M %p")
            self.canvas.itemconfig(self.time_text, text=now)
            self.root.after(1000, self._tick)
        except Exception:
            pass

    def _process_q(self):
        try:
            while not self.q.empty():
                key, value = self.q.get_nowait()
                if key == "status":
                    self.state = value
            self.root.after(100, self._process_q)
        except Exception:
            pass


_hud = None


def get_hud():
    global _hud
    if _hud is None:
        _hud = NovaHUD()
    return _hud


def start():
    get_hud().start()


def update(key, value):
    try:
        get_hud().update(key, value)
    except Exception:
        pass
