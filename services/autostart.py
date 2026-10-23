# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Windows Autostart Manager.
Allows silent, zero-console startup with Windows via shell:startup VBS launcher.
"""

import os
import sys

from core.config import APPMUSIC_DIR
from core.logger import get_logger

logger = get_logger("Autostart")

STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", ""),
    r"Microsoft\Windows\Start Menu\Programs\Startup",
)
VBS_NAME = "FlowMusic360_Startup.vbs"
VBS_PATH = os.path.join(STARTUP_FOLDER, VBS_NAME)


def is_autostart_enabled() -> bool:
    """Checks if the startup VBS launcher exists in the user's Startup folder."""
    return os.path.isfile(VBS_PATH)


def enable_autostart() -> bool:
    """
    Creates a zero-window VBS launcher in shell:startup.
    Executes daemon.py via pythonw.exe completely hidden.
    """
    try:
        os.makedirs(STARTUP_FOLDER, exist_ok=True)
        pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw_path):
            pythonw_path = "pythonw.exe"

        daemon_script = os.path.join(APPMUSIC_DIR, "daemon.py")

        vbs_content = (
            'Set WshShell = CreateObject("WScript.Shell")\r\n'
            f'WshShell.CurrentDirectory = "{APPMUSIC_DIR}"\r\n'
            f'WshShell.Run """{pythonw_path}"" ""{daemon_script}""", 0, False\r\n'
        )

        with open(VBS_PATH, "w", encoding="utf-8") as f:
            f.write(vbs_content)

        logger.info(f"Autostart enabled: created {VBS_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to enable autostart: {e}")
        return False


def disable_autostart() -> bool:
    """Removes the startup launcher from shell:startup."""
    try:
        if os.path.exists(VBS_PATH):
            os.remove(VBS_PATH)
            logger.info("Autostart disabled: removed startup script")
        return True
    except Exception as e:
        logger.error(f"Failed to disable autostart: {e}")
        return False


def toggle_autostart() -> bool:
    """Toggles autostart status and returns the new state."""
    if is_autostart_enabled():
        disable_autostart()
        return False
    else:
        enable_autostart()
        return True

