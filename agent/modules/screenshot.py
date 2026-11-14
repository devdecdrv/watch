# screenshot.py — periodic silent screenshots

import threading, time, io
import pyautogui
from PIL import Image


def _capture() -> bytes:
    """Capture full screen and return PNG bytes."""
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def start(on_capture_callback, interval: int = 60):
    """
    Take a screenshot every `interval` seconds.
    Calls on_capture_callback(png_bytes).
    """
    def loop():
        while True:
            try:
                png = _capture()
                on_capture_callback(png)
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
