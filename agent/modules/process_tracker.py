# process_tracker.py — logs which apps are open and for how long

import threading, time, psutil
from datetime import datetime

_active: dict = {}   # pid -> {name, start_time}


def _snapshot() -> dict:
    """Return current running processes as {pid: name}."""
    result = {}
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            result[proc.info["pid"]] = proc.info["name"]
        except Exception:
            pass
    return result


def _diff(old: dict, new: dict) -> tuple:
    opened = {pid: name for pid, name in new.items() if pid not in old}
    closed = {pid: name for pid, name in old.items() if pid not in new}
    return opened, closed


def start(on_event_callback, interval: int = 10):
    """
    Poll process list every `interval` seconds.
    Calls on_event_callback(text) when apps open or close.
    """
    prev = _snapshot()

    def loop():
        nonlocal prev
        while True:
            time.sleep(interval)
            try:
                curr    = _snapshot()
                opened, closed = _diff(prev, curr)
                prev    = curr
                lines   = []
                ts      = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                for pid, name in opened.items():
                    lines.append(f"[{ts}] OPENED  {name} (PID {pid})")
                for pid, name in closed.items():
                    lines.append(f"[{ts}] CLOSED  {name} (PID {pid})")
                if lines:
                    on_event_callback("\n".join(lines))
            except Exception:
                pass

    t = threading.Thread(target=loop, daemon=True)
    t.start()
