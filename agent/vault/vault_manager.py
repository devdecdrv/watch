def init_vault(vault_dir: Path, password: str) -> bytes:
    """
    Create vault, write salt, derive key — THEN hide and lock.
    Order matters: write first, restrict after.
    """
    # Step 1 — create folder normally first (no hiding yet)
    vault_dir.mkdir(parents=True, exist_ok=True)

    ss_dir = vault_dir / "ss"
    ss_dir.mkdir(parents=True, exist_ok=True)

    # Step 2 — write salt (folder is plain and writable right now)
    salt = _load_or_create_salt(vault_dir)

    # Step 3 — derive key
    key = derive_key(password, salt)

    # Step 4 — init DB
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

    # Step 5 — NOW hide and lock everything
    try:
        _hide_folder(vault_dir)
        _hide_folder(ss_dir)
        _hide_file(db_path)
        _hide_file(vault_dir / SALT_FILE)
        _lock_folder_acl(vault_dir)
    except Exception:
        pass  # hiding failed — vault still works, just not hidden

    return key
