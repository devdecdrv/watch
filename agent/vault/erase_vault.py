# erase_vault.py — securely wipe all stored data from vault
# Run only when you want to clear all logs and screenshots
# Overwrites files with zeros before deleting — no forensic trace

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vault.vault_manager import vault_erase
import config


def main():
    print("=" * 60)
    print("  PARENTWATCH — SECURE VAULT ERASER")
    print("=" * 60)
    print("\n[!] This will permanently destroy ALL stored logs and screenshots.")
    confirm = input("\nType YES to confirm: ").strip()
    if confirm != "YES":
        print("Cancelled.")
        return

    vault_erase(config.VAULT_DIR)
    print("\n[+] Vault wiped. All data destroyed.")
    input("Press Enter to exit.")


if __name__ == "__main__":
    main()
