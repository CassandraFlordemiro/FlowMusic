# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Plugin Synchronizer.
Instantly syncs the core plugin script and assets to Flow Launcher's roaming plugins directory.
"""

import os
import shutil

APPMUSIC_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    r"FlowLauncher\Plugins\FlowMusic-1.0.0",
)


def sync():
    if not os.path.isdir(PLUGIN_DIR):
        print(f"Flow Launcher plugin directory not found at: {PLUGIN_DIR}")
        return False

    src_main = os.path.join(APPMUSIC_DIR, "flow_plugin_main.py")
    dst_main = os.path.join(PLUGIN_DIR, "main.py")

    shutil.copy2(src_main, dst_main)
    print(f"Synced {src_main} -> {dst_main}")

    # Sync assets
    src_assets = os.path.join(APPMUSIC_DIR, "assets")
    dst_assets = os.path.join(PLUGIN_DIR, "assets")
    if os.path.isdir(src_assets):
        shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)
        print(f"Synced assets -> {dst_assets}")

    print("Flow Launcher plugin is 100% up-to-date!")
    return True


if __name__ == "__main__":
    sync()

