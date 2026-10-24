"""'Start with Windows' via the current user's Run registry key (no admin needed)."""

from __future__ import annotations

import logging
import sys
import winreg
from pathlib import Path

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "PCDash"


def launch_command() -> str:
    """Command that starts PCDash without a console window."""
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if pythonw.exists():
        exe = pythonw
    script = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{exe}" "{script}"'


def is_enabled(name: str = VALUE_NAME) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, name)
            return True
    except OSError:
        return False


def set_enabled(enabled: bool, name: str = VALUE_NAME) -> bool:
    """Add or remove the Run entry. Returns False if the registry write failed."""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        log.warning("Could not change autostart: %s", exc)
        return False
