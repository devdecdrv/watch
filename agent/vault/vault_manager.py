# vault_manager.py — encrypted local vault, no hiding, no ACL

import os, sqlite3, secrets
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

SALT_FILE = "salt.bin"
DB_FILE   = "activity.db"


# ── KEY DERIVATION ────────────────────────────────────────────────────────────

def _load_or_create_salt(vault_dir: Path) -> bytes:
    salt_path = vault_dir / SALT_FILE
    if salt_path.exists():
        return salt_path.read_bytes()
    salt = secrets.token_bytes(32)
    salt_path.write_bytes(salt)
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
    iv     = secrets.token_bytes(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc    = cipher.encryptor()
    ct     = enc.update(padded) + enc.finalize()
    return iv + ct

def decrypt_bytes(data: bytes, key: bytes) -> bytes:
    iv, ct   = data[:16], data[16:]
    cipher   = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec      = cipher.decryptor()
    padded   = dec.update(ct) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


# ── VAULT INIT ────────────────────────────────────────────────────────────────

def init_vault(vault_dir: Path, password: str) -> bytes:
    """Plain vault — no hiding, no ACL. Just creates folders and DB."""
    vault_dir.mkdir(parents=True, exist_ok=True)
    ss_dir = vault_dir / "ss"
    ss_dir.mkdir(parents=True, exist_ok=True)

    salt    = _load_or_create_salt(vault_dir)
    key     = derive_key(password, salt)

    db_path = vault_dir / DB_FILE
    conn    = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            category  TEXT    NOT NULL,
            payload   BLOB    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    return key


# ── VAULT WRITE ───────────────────────────────────────────────────────────────

def vault_write(vault_dir: Path, key: bytes, category: str, plaintext: str):
    db_path = vault_dir / DB_FILE
    ts      = datetime.utcnow().isoformat()
    blob    = encrypt_bytes(plaintext.encode("utf-8", errors="replace"), key)
    conn    = sqlite3.connect(str(db_path))
    conn.execute("INSERT INTO logs (ts, category, payload) VALUES (?, ?, ?)",
                 (ts, category, blob))
    conn.commit()
    conn.close()

def vault_write_screenshot(vault_dir: Path, key: bytes, png_bytes: bytes) -> str:
    ss_dir = vault_dir / "ss"
    ss_dir.mkdir(parents=True, exist_ok=True)
    ts     = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname  = ss_dir / f"{ts}.enc"
    blob   = encrypt_bytes(png_bytes, key)
    fname.write_bytes(blob)
    return str(fname)


# ── VAULT READ ────────────────────────────────────────────────────────────────

def vault_read_all(vault_dir: Path, key: bytes) -> list:
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
    return decrypt_bytes(Path(enc_path).read_bytes(), key)


# ── VAULT ERASE ───────────────────────────────────────────────────────────────

def vault_erase(vault_dir: Path):
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
