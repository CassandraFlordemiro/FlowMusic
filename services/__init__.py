# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Services Layer.
Contains the Windows Autostart Manager and Async YouTube Downloader.
"""

from .autostart import disable_autostart, enable_autostart, is_autostart_enabled, toggle_autostart
from .downloader import (
    download_state,
    extract_playlist_id_or_url,
    get_ffmpeg_path,
    is_valid_youtube_url,
    sanitize_folder_name,
    start_download_async,
)

__all__ = [
    "is_autostart_enabled",
    "enable_autostart",
    "disable_autostart",
    "toggle_autostart",
    "download_state",
    "get_ffmpeg_path",
    "is_valid_youtube_url",
    "extract_playlist_id_or_url",
    "sanitize_folder_name",
    "start_download_async",
]
