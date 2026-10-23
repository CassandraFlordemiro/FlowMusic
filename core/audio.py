# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Native WinMM / MCI Audio Engine.
Provides low-latency, zero-dependency background audio playback on Windows.
"""

import ctypes
import os
from typing import Tuple

from .logger import get_logger

logger = get_logger("AudioEngine")


def format_ms(ms: int) -> str:
    """Formats milliseconds into MM:SS string."""
    if ms <= 0:
        return "00:00"
    total_sec = int(ms // 1000)
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}"


class MCIAudioEngine:
    def __init__(self):
        self.winmm = ctypes.windll.winmm
        self.alias = "flowmusic_media"
        self.is_open = False
        self.current_path = ""
        self.duration_ms = 0

    def _send(self, cmd: str) -> Tuple[int, str]:
        buf = ctypes.create_unicode_buffer(512)
        err = self.winmm.mciSendStringW(cmd, buf, 512, 0)
        return err, buf.value

    def close(self):
        if self.is_open:
            try:
                self._send(f"stop {self.alias}")
                self._send(f"close {self.alias}")
            except Exception as e:
                logger.error(f"Error closing MCI device: {e}")
            finally:
                self.is_open = False
                self.current_path = ""
                self.duration_ms = 0

    def load_and_play(self, filepath: str, volume: int = 80, start_pos_ms: int = 0) -> bool:
        if not os.path.isfile(filepath):
            logger.error(f"Cannot play track: File does not exist -> {filepath}")
            return False

        self.close()
        # Escape quotes in file path
        clean_path = filepath.replace('"', "")

        # Try open as mpegvideo first, fallback to default MCI
        err, _ = self._send(f'open "{clean_path}" type mpegvideo alias {self.alias}')
        if err != 0:
            err, _ = self._send(f'open "{clean_path}" alias {self.alias}')
            if err != 0:
                logger.error(f"MCI open failed with error code {err} for {clean_path}")
                return False

        self.is_open = True
        self.current_path = clean_path
        self._send(f"set {self.alias} time format milliseconds")

        _, len_str = self._send(f"status {self.alias} length")
        self.duration_ms = int(len_str) if len_str.isdigit() else 0

        self.set_volume(volume)
        if start_pos_ms > 0:
            self.seek(start_pos_ms, playing=True)
        else:
            self._send(f"play {self.alias}")

        logger.info(f"Playback started: {os.path.basename(clean_path)} ({format_ms(self.duration_ms)})")
        return True

    def pause(self):
        if self.is_open:
            self._send(f"pause {self.alias}")

    def resume(self):
        if self.is_open:
            self._send(f"resume {self.alias}")

    def stop(self):
        if self.is_open:
            self._send(f"stop {self.alias}")

    def seek(self, pos_ms: int, playing: bool = True):
        if self.is_open:
            pos_ms = max(0, min(self.duration_ms, int(pos_ms)))
            if playing:
                self._send(f"play {self.alias} from {pos_ms}")
            else:
                self._send(f"seek {self.alias} to {pos_ms}")

    def set_volume(self, volume_0_100: int):
        if self.is_open:
            mci_vol = max(0, min(1000, int(volume_0_100 * 10)))
            self._send(f"setaudio {self.alias} volume to {mci_vol}")

    def get_position_ms(self) -> int:
        if not self.is_open:
            return 0
        _, pos_str = self._send(f"status {self.alias} position")
        return int(pos_str) if pos_str.isdigit() else 0

    def get_mode(self) -> str:
        if not self.is_open:
            return "stopped"
        _, mode_str = self._send(f"status {self.alias} mode")
        return mode_str.strip().lower() or "stopped"

