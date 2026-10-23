# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Centralized Configuration & Paths.
"""

import os

# Root directory of FlowMusic
APPMUSIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Data files
CONFIG_PATH = os.path.join(APPMUSIC_DIR, "config.json")
STATE_PATH = os.path.join(APPMUSIC_DIR, "state.json")
FAVORITES_PATH = os.path.join(APPMUSIC_DIR, "favorites.json")

# Resource & Cache directories
CACHE_DIR = os.path.join(APPMUSIC_DIR, "cache")
COVERS_CACHE_DIR = os.path.join(CACHE_DIR, "covers")
ASSETS_DIR = os.path.join(APPMUSIC_DIR, "assets")
HUD_ASSETS_DIR = os.path.join(ASSETS_DIR, "hud")
LOGS_DIR = os.path.join(APPMUSIC_DIR, "logs")

# Network / IPC RPC
RPC_HOST = "127.0.0.1"
RPC_PORT = 49360

# Default configuration settings
DEFAULT_CONFIG = {
    "music_dirs": [r"C:\Users\Administrator\Downloads\YouTube_Music"],
    "supported_extensions": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"],
    "volume": 100,
    "hud_position": "top_center",
    "hud_duration_seconds": 3.8,
    "hud_theme": "dark_acrylic",
    "fetch_covers": True,
    "auto_rescan_interval_s": 60,
    "enable_global_hotkeys": True,
    "autostart_with_windows": False,
}

# Ensure critical directories exist
for d in (CACHE_DIR, COVERS_CACHE_DIR, ASSETS_DIR, HUD_ASSETS_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)

