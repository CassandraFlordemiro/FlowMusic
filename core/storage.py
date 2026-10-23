# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Resilient Storage & Atomic File I/O.
Prevents file corruption from sudden power cuts, system crashes, or concurrent writes
by writing to a temporary file before performing an atomic os.replace().
"""

import json
import os
import shutil
import time

from .config import CONFIG_PATH, DEFAULT_CONFIG, FAVORITES_PATH, STATE_PATH
from .logger import get_logger

logger = get_logger("Storage")


def atomic_write_json(filepath: str, data: dict | list, indent: int = 2) -> bool:
    """
    Atomically writes a Python dict or list to a JSON file.
    Writes to a temporary file on the same volume and uses os.replace() for atomic swapping.
    """
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)
    tmp_path = f"{filepath}.{os.getpid()}.{time.time_ns()}.tmp"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replacement on Windows / NTFS
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        logger.error(f"Failed atomic write to {filepath}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False


def safe_read_json(filepath: str, default=None):
    """
    Safely reads a JSON file with error resilience.
    If corrupted or missing, returns default and creates a .bak backup of the corrupted file.
    """
    if not os.path.exists(filepath):
        return default

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as jde:
        logger.warning(f"JSONDecodeError reading {filepath}: {jde}. Preserving corrupted file to .bak")
        try:
            bak_path = f"{filepath}.corrupt_{int(time.time())}.bak"
            shutil.copy2(filepath, bak_path)
        except Exception:
            pass
        return default
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return default


# --- High-level Config Helpers ---


def load_config() -> dict:
    config = safe_read_json(CONFIG_PATH, default=None)
    if not config:
        config = dict(DEFAULT_CONFIG)
        save_config(config)
    else:
        # Merge any missing defaults
        updated = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in config:
                config[k] = v
                updated = True
        if updated:
            save_config(config)
    return config


def save_config(config: dict) -> bool:
    return atomic_write_json(CONFIG_PATH, config)


# --- High-level State Helpers ---


def load_state() -> dict:
    return safe_read_json(STATE_PATH, default={})


def save_state(state: dict) -> bool:
    return atomic_write_json(STATE_PATH, state)


# --- High-level Favorites Helpers ---


def load_favorites() -> list[str]:
    favs = safe_read_json(FAVORITES_PATH, default=[])
    if isinstance(favs, list):
        return favs
    return []


def save_favorites(favorites: list[str]) -> bool:
    unique_favs = sorted(list(set(favorites)))
    return atomic_write_json(FAVORITES_PATH, unique_favs)


def is_favorite(track_path: str, favorites_cache: set[str] | None = None) -> bool:
    norm = os.path.normcase(os.path.abspath(track_path))
    if favorites_cache is not None:
        return norm in favorites_cache
    favs = set(os.path.normcase(os.path.abspath(f)) for f in load_favorites())
    return norm in favs


def toggle_favorite(track_path: str) -> tuple[bool, list[str]]:
    """Toggles track favorite status and returns (now_is_favorite, updated_list)."""
    norm = os.path.normcase(os.path.abspath(track_path))
    favs = load_favorites()
    fav_set = set(os.path.normcase(os.path.abspath(f)) for f in favs)

    if norm in fav_set:
        new_favs = [f for f in favs if os.path.normcase(os.path.abspath(f)) != norm]
        save_favorites(new_favs)
        logger.info(f"Removed from favorites: {track_path}")
        return False, new_favs
    else:
        new_favs = favs + [track_path]
        save_favorites(new_favs)
        logger.info(f"Added to favorites: {track_path}")
        return True, new_favs

