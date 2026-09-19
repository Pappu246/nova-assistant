"""
NOVA - Clean shutdown helper
"""
import os
import sys
import time
import signal
import psutil


def kill_nova():
    """Saare NOVA processes band karo."""
    me = os.getpid()
    targets = ["python.exe", "pythonw.exe", "chromium.exe"]
    killed = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == me:
                continue
            name = (proc.info.get('name') or '').lower()
            cmdline = ' '.join(proc.info.get('cmdline') or []).lower()

            if name in targets:
                if 'nova' in cmdline or 'server.py' in cmdline or 'main.py' in cmdline:
                    proc.kill()
                    killed.append(proc.pid)
        except Exception:
            pass

    print(f"Killed: {killed}")


if __name__ == "__main__":
    kill_nova()
