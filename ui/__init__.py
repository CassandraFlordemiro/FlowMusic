# -*- coding: utf-8 -*-
"""
FlowMusic 360 - UI Layer.
Contains the Acrylic HUD Dynamic Island window, vector icon engine, and album art cover provider.
"""

from .covers import get_cover_icon_path, get_hud_cover_file, prefetch_covers_for_library
from .hud_acrylic import AcrylicHUDWindow
from .vector_icons import get_icon

__all__ = [
    "AcrylicHUDWindow",
    "get_icon",
    "get_cover_icon_path",
    "get_hud_cover_file",
    "prefetch_covers_for_library",
]

