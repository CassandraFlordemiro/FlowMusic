# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Core Module.
Contains storage, logging, configuration, library scanning, and audio engine.
"""

from .config import (
    APPMUSIC_DIR,
    ASSETS_DIR,
    CACHE_DIR,
    CONFIG_PATH,
    COVERS_CACHE_DIR,
    DEFAULT_CONFIG,
    FAVORITES_PATH,
    HUD_ASSETS_DIR,
    LOGS_DIR,
    RPC_HOST,
    RPC_PORT,
    STATE_PATH,
)
from .logger import get_logger
from .storage import (
    atomic_write_json,
    is_favorite,
    load_config,
    load_favorites,
    load_state,
    safe_read_json,
    save_config,
    save_favorites,
    save_state,
    toggle_favorite,
)

__all__ = [
    "APPMUSIC_DIR",
    "CONFIG_PATH",
    "STATE_PATH",
    "FAVORITES_PATH",
    "CACHE_DIR",
    "COVERS_CACHE_DIR",
    "ASSETS_DIR",
    "HUD_ASSETS_DIR",
    "LOGS_DIR",
    "RPC_HOST",
    "RPC_PORT",
    "DEFAULT_CONFIG",
    "get_logger",
    "atomic_write_json",
    "safe_read_json",
    "load_config",
    "save_config",
    "load_state",
    "save_state",
    "load_favorites",
    "save_favorites",
    "is_favorite",
    "toggle_favorite",
]

