# -*- coding: utf-8 -*-
"""
FlowMusic 360 - Background Audio Daemon.
Uses the True 32-Bit Per-Pixel Alpha Acrylic HUD Window (MyDockFinder style)
with real album art covers, clickable seek bar, and global in-game hotkeys.
"""

import ctypes
from ctypes import wintypes
import json
import math
import os
import queue
import random
import socket
import sys
import threading
import time
import tkinter as tk
from PIL import Image

from core.storage import atomic_write_json
from covers import get_cover_icon_path, prefetch_covers_for_library
from hud_acrylic import AcrylicHUDWindow
from library import (
    DEFAULT_CONFIG,
    STATE_PATH,
    get_playlists,
    is_favorite,
    load_config,
    save_config,
    scan_library,
    toggle_favorite,
)

RPC_HOST = "127.0.0.1"
RPC_PORT = 49360

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

VK_SPACE = 0x20
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_F = 0x46
VK_H = 0x48
VK_M = 0x4D
VK_S = 0x53


def format_ms(ms: int) -> str:
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

    def _send(self, cmd: str) -> tuple[int, str]:
        buf = ctypes.create_unicode_buffer(512)
        err = self.winmm.mciSendStringW(cmd, buf, 512, 0)
        return err, buf.value

    def close(self):
        if self.is_open:
            self._send(f"stop {self.alias}")
            self._send(f"close {self.alias}")
            self.is_open = False

    def load_and_play(self, filepath: str, volume: int = 80, start_pos_ms: int = 0) -> bool:
        self.close()
        err, _ = self._send(f'open "{filepath}" type mpegvideo alias {self.alias}')
        if err != 0:
            err, _ = self._send(f'open "{filepath}" alias {self.alias}')
            if err != 0:
                return False

        self.is_open = True
        self.current_path = filepath
        self._send(f"set {self.alias} time format milliseconds")

        _, len_str = self._send(f"status {self.alias} length")
        self.duration_ms = int(len_str) if len_str.isdigit() else 0

        self.set_volume(volume)
        if start_pos_ms > 0:
            self.seek(start_pos_ms, playing=True)
        else:
            self._send(f"play {self.alias}")
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


class FlowMusicDaemon:
    def __init__(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.config = load_config()
        self.audio = MCIAudioEngine()
        self.cmd_queue: queue.Queue = queue.Queue()

        self.tracks = scan_library(self.config.get("music_dirs"))
        self.active_playlist: str = "Todas as Músicas"
        self.play_queue: list[dict] = list(self.tracks)
        self.current_index: int = -1
        self.current_track: dict | None = None
        self.state: str = "stopped"
        self.volume: int = int(self.config.get("volume", 80))
        self.shuffle: bool = bool(self.config.get("shuffle", False))
        self.repeat: str = str(self.config.get("repeat", "all"))
        self.position_ms: int = 0
        self.duration_ms: int = 0
        self.last_rescan_time: float = time.time()

        self._restore_session_state()

        # Prefetch album covers in background
        prefetch_covers_for_library(self.tracks)

        # True 32-bit Win32 Layered Window Acrylic HUD
        theme = self.config.get("theme", "opal")
        self.hud = AcrylicHUDWindow(on_action_cb=self._on_hud_user_action, theme=theme)
        pos = self.config.get("hud_position", "top_center")
        self.hud._position_hud(pos)
        self._init_global_hotkeys()

        # Tkinter dummy root for timer event loop & single thread sync
        self.root = tk.Tk()
        self.root.withdraw()

        self.save_state_snapshot()

    def _init_global_hotkeys(self):
        if not self.config.get("hotkeys_enabled", True):
            return
        MOD_CONTROL = 0x0002
        MOD_ALT = 0x0001
        mods = MOD_CONTROL | MOD_ALT
        self.hotkey_map = {
            1: ("toggle", {}),
            2: ("next", {}),
            3: ("prev", {}),
            4: ("vol_delta", {"delta": 10}),
            5: ("vol_delta", {"delta": -10}),
            6: ("hud", {}),
            7: ("hud", {}),
            8: ("shuffle", {}),
            9: ("toggle_fav", {}),
            10: ("toggle", {}),
            11: ("next", {}),
            12: ("prev", {}),
        }
        hk_defs = {
            1: (mods, VK_SPACE),
            2: (mods, VK_RIGHT),
            3: (mods, VK_LEFT),
            4: (mods, VK_UP),
            5: (mods, VK_DOWN),
            6: (mods, VK_M),
            7: (mods, VK_H),
            8: (mods, VK_S),
            9: (mods, VK_F),
            10: (0, 0xB3),  # VK_MEDIA_PLAY_PAUSE
            11: (0, 0xB0),  # VK_MEDIA_NEXT_TRACK
            12: (0, 0xB1),  # VK_MEDIA_PREV_TRACK
        }
        self.hud.register_hotkeys(hk_defs)

    def _dispatch_action(self, cmd: str, req: dict | None = None):
        req = req or {}
        if cmd == "hud":
            if self.hud.alpha > 20 and self.hud.target_alpha > 0:
                self.hud.target_alpha = 0
            else:
                self.trigger_track_hud(prefix="🎵 Tocando agora" if self.state == "playing" else "⏸ Status atual")
        elif cmd == "toggle":
            self.toggle_play_pause()
        elif cmd == "next":
            self.next_track(auto_advanced=False)
        elif cmd == "prev":
            self.prev_track()
        elif cmd == "seek":
            new_pos = int(req.get("pos", 0))
            self.audio.seek(new_pos, playing=(self.state == "playing"))
            self.position_ms = new_pos
            self.trigger_track_hud(prefix="⏩ Posição alterada")
        elif cmd == "toggle_fav":
            self.toggle_favorite_current()
        elif cmd == "vol_delta":
            self.set_volume(self.volume + int(req.get("delta", 10)))
        elif cmd == "shuffle":
            self.toggle_shuffle()
        elif cmd == "toggle_theme":
            self.toggle_theme()

    def _on_hud_user_action(self, action: str, val=None):
        if action == "hotkey":
            hk_id = val
            if hasattr(self, "hotkey_map") and hk_id in self.hotkey_map:
                cmd, extra = self.hotkey_map[hk_id]
                self._dispatch_action(cmd, extra)
            return

        if action == "seek_fraction":
            if self.duration_ms > 0:
                new_pos = int(val * self.duration_ms)
                self._dispatch_action("seek", {"pos": new_pos})
        elif action == "seek_delta":
            if self.duration_ms > 0:
                new_pos = max(0, min(self.duration_ms, self.position_ms + int(val)))
                self._dispatch_action("seek", {"pos": new_pos})
        elif action == "vol_delta":
            self._dispatch_action("vol_delta", {"delta": int(val)})
        elif action in ("toggle", "next", "prev", "toggle_fav", "shuffle", "toggle_theme"):
            self._dispatch_action(action, {})

    def _restore_session_state(self):
        if os.path.exists(STATE_PATH):
            try:
                with open(STATE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        saved_track = data.get("current_track")
                        if saved_track and os.path.exists(saved_track.get("path", "")):
                            self.current_track = saved_track
                            self.active_playlist = data.get("active_playlist", "Todas as Músicas")
                            self.position_ms = int(data.get("position_ms", 0))
                            self.duration_ms = int(data.get("duration_ms", 0))
                            norm = os.path.normcase(saved_track["path"])
                            for i, t in enumerate(self.tracks):
                                if os.path.normcase(t["path"]) == norm:
                                    self.current_index = i
                                    break
            except Exception:
                pass

    def trigger_track_hud(self, prefix: str = "🎵 Tocando agora"):
        if not self.current_track:
            self.hud.show(
                header="FLOWMUSIC 360",
                title="Nenhuma música em reprodução",
                artist="Digite 'm' no Flow Launcher",
                cur_time="00:00",
                total_time="00:00",
                progress=0.0,
                cover_image=None,
                accent_rgb=(56, 189, 248),
                is_paused=True,
                is_fav=False,
                is_shuffle=self.shuffle,
            )
            return

        prog = (self.position_ms / self.duration_ms) if self.duration_ms > 0 else 0.0
        cur_s = format_ms(self.position_ms)
        tot_s = format_ms(self.duration_ms) if self.duration_ms > 0 else "00:00"
        pl = self.current_track.get("playlist", "Playlist")
        is_fav = is_favorite(self.current_track["path"])
        accent = (244, 63, 94) if is_fav else ((16, 225, 125) if self.state == "playing" else (251, 191, 36))

        # Load real cover image
        cov_path = get_cover_icon_path(self.current_track)
        cov_img = None
        if os.path.exists(cov_path):
            try:
                cov_img = Image.open(cov_path)
            except Exception:
                pass

        self.hud.show(
            header=f"{prefix} • {pl}",
            title=self.current_track.get("display_title", self.current_track.get("title", "")),
            artist=self.current_track.get("artist", ""),
            cur_time=cur_s,
            total_time=tot_s,
            progress=prog,
            cover_image=cov_img,
            accent_rgb=accent,
            is_paused=(self.state != "playing"),
            is_fav=is_fav,
            is_shuffle=self.shuffle,
            duration_s=self.config.get("hud_duration_ms", 5000) / 1000.0,
        )

    def toggle_favorite_current(self):
        if not self.current_track:
            return
        path = self.current_track["path"]
        added = toggle_favorite(path)
        self.current_track["is_favorite"] = added
        self.refresh_library_if_needed(force=True)
        self.save_state_snapshot()

        cov_path = get_cover_icon_path(self.current_track)
        cov_img = Image.open(cov_path) if os.path.exists(cov_path) else None

        if added:
            self.hud.show(
                header="❤️ ADICIONADA ÀS FAVORITAS!",
                title=self.current_track["display_title"],
                artist=self.current_track.get("artist", ""),
                time_str="Playlist ❤️ Favoritas",
                progress=1.0,
                cover_image=cov_img,
                accent_rgb=(244, 63, 94),
                is_paused=(self.state != "playing"),
                is_fav=True,
                duration_s=3.2,
            )
        else:
            self.hud.show(
                header="💔 REMOVIDA DAS FAVORITAS",
                title=self.current_track["display_title"],
                artist=self.current_track.get("artist", ""),
                time_str="Favoritas",
                progress=0.0,
                cover_image=cov_img,
                accent_rgb=(148, 163, 184),
                is_paused=(self.state != "playing"),
                is_fav=False,
                duration_s=3.2,
            )

    def refresh_library_if_needed(self, force: bool = False):
        now = time.time()
        if force or (now - self.last_rescan_time > 8.0):
            self.tracks = scan_library(self.config.get("music_dirs"))
            self.last_rescan_time = now
            if not self.play_queue and self.tracks:
                self.play_queue = list(self.tracks)

    def _build_queue_for_track(self, target_track: dict, playlist_filter: str | None = None):
        self.refresh_library_if_needed(force=True)
        pl_name = playlist_filter or target_track.get("playlist")
        if pl_name == "❤️ Favoritas":
            fav_tracks = [t for t in self.tracks if t.get("is_favorite")]
            self.active_playlist = "❤️ Favoritas"
            self.play_queue = fav_tracks if fav_tracks else list(self.tracks)
        elif pl_name and pl_name != "Todas as Músicas":
            pl_tracks = [t for t in self.tracks if t["playlist"] == pl_name]
            if pl_tracks:
                self.active_playlist = pl_name
                self.play_queue = list(pl_tracks)
            else:
                self.active_playlist = "Todas as Músicas"
                self.play_queue = list(self.tracks)
        else:
            self.active_playlist = "Todas as Músicas"
            self.play_queue = list(self.tracks)

        target_norm = os.path.normcase(target_track["path"])
        if self.shuffle:
            others = [t for t in self.play_queue if os.path.normcase(t["path"]) != target_norm]
            random.shuffle(others)
            self.play_queue = [target_track] + others
            self.current_index = 0
        else:
            self.current_index = 0
            for i, t in enumerate(self.play_queue):
                if os.path.normcase(t["path"]) == target_norm:
                    self.current_index = i
                    break

    def play_track_by_path(self, filepath: str, playlist_filter: str | None = None) -> bool:
        self.refresh_library_if_needed(force=True)
        norm_target = os.path.normcase(os.path.abspath(filepath))
        found = next((t for t in self.tracks if os.path.normcase(t["path"]) == norm_target), None)
        if not found:
            if not os.path.exists(filepath):
                return False
            from library import parse_track_filename
            found = parse_track_filename(filepath, os.path.dirname(filepath))

        self._build_queue_for_track(found, playlist_filter)
        return self._play_current_index(hud_prefix="▶ Tocando agora")

    def play_playlist(self, playlist_name: str) -> bool:
        self.refresh_library_if_needed(force=True)
        if playlist_name == "❤️ Favoritas":
            candidates = [t for t in self.tracks if t.get("is_favorite")]
        elif playlist_name == "Todas as Músicas":
            candidates = list(self.tracks)
        else:
            candidates = [t for t in self.tracks if t["playlist"].lower() == playlist_name.lower()]
        if not candidates:
            return False

        self.active_playlist = playlist_name
        self.play_queue = list(candidates)
        if self.shuffle:
            random.shuffle(self.play_queue)
        self.current_index = 0
        return self._play_current_index(hud_prefix=f"📂 Playlist • {playlist_name}")

    def enqueue_next(self, filepath: str) -> bool:
        self.refresh_library_if_needed()
        norm_target = os.path.normcase(os.path.abspath(filepath))
        found = next((t for t in self.tracks if os.path.normcase(t["path"]) == norm_target), None)
        if not found:
            return False

        insert_pos = max(0, self.current_index + 1)
        self.play_queue.insert(insert_pos, found)
        self.save_state_snapshot()

        cov_path = get_cover_icon_path(found)
        cov_img = Image.open(cov_path) if os.path.exists(cov_path) else None

        self.hud.show(
            header="🎵 ADICIONADA A SEGUIR",
            title=found["display_title"],
            artist=found.get("artist", ""),
            time_str=f"Posição #{insert_pos + 1}",
            progress=1.0,
            cover_image=cov_img,
            accent_rgb=(56, 189, 248),
            duration_s=3.0,
        )
        return True

    def _play_current_index(self, hud_prefix: str = "🎵 Tocando agora", start_pos_ms: int = 0) -> bool:
        if not self.play_queue or self.current_index < 0 or self.current_index >= len(self.play_queue):
            return False

        track = self.play_queue[self.current_index]
        ok = self.audio.load_and_play(track["path"], self.volume, start_pos_ms=start_pos_ms)
        if ok:
            self.current_track = track
            self.state = "playing"
            self.position_ms = start_pos_ms
            self.duration_ms = self.audio.duration_ms
            self.save_state_snapshot()
            self.trigger_track_hud(prefix=hud_prefix)
        return ok

    def toggle_play_pause(self):
        if self.state == "playing":
            self.audio.pause()
            self.state = "paused"
            self.save_state_snapshot()
            self.trigger_track_hud(prefix="⏸ Pausado")
        elif self.state == "paused":
            self.audio.resume()
            self.state = "playing"
            self.save_state_snapshot()
            self.trigger_track_hud(prefix="▶ Continuando")
        else:
            self.refresh_library_if_needed(force=True)
            if self.current_track and os.path.exists(self.current_track["path"]):
                self._play_current_index(hud_prefix="▶ Retomando reprodução", start_pos_ms=self.position_ms)
            else:
                if not self.play_queue and self.tracks:
                    self.play_queue = list(self.tracks)
                    if self.shuffle:
                        random.shuffle(self.play_queue)
                if self.play_queue:
                    self.current_index = 0
                    self._play_current_index(hud_prefix="▶ Tocando agora")

    def next_track(self, auto_advanced: bool = False):
        self.refresh_library_if_needed()
        if not self.play_queue and self.tracks:
            self.play_queue = list(self.tracks)
        if not self.play_queue:
            return

        if auto_advanced and self.repeat == "one" and self.current_index >= 0:
            self._play_current_index(hud_prefix="🔂 Repetindo faixa")
            return

        next_idx = self.current_index + 1
        if next_idx >= len(self.play_queue):
            if auto_advanced and self.repeat == "off":
                self.audio.stop()
                self.state = "stopped"
                self.save_state_snapshot()
                return
            next_idx = 0
            if self.shuffle and len(self.play_queue) > 1:
                random.shuffle(self.play_queue)

        self.current_index = next_idx
        prefix = "🎵 Tocando a seguir" if auto_advanced else "⏭ Próxima faixa"
        self._play_current_index(hud_prefix=prefix)

    def prev_track(self):
        if not self.play_queue:
            return
        if self.position_ms > 4000:
            self.audio.seek(0, playing=(self.state == "playing"))
            self.position_ms = 0
            self.trigger_track_hud(prefix="⏮ Início da faixa")
            return

        prev_idx = self.current_index - 1
        if prev_idx < 0:
            prev_idx = len(self.play_queue) - 1
        self.current_index = prev_idx
        self._play_current_index(hud_prefix="⏮ Faixa anterior")

    def set_volume(self, new_vol: int):
        self.volume = max(0, min(100, int(new_vol)))
        self.audio.set_volume(self.volume)
        self.config["volume"] = self.volume
        save_config(self.config)
        self.save_state_snapshot()

        sub_title = self.current_track["display_title"] if self.current_track else "Volume do Reprodutor"
        cov_path = get_cover_icon_path(self.current_track) if self.current_track else ""
        cov_img = Image.open(cov_path) if cov_path and os.path.exists(cov_path) else None

        self.hud.show(
            header=f"🔊 VOLUME AJUSTADO • {self.volume}%",
            title=sub_title,
            artist=self.current_track.get("artist", "") if self.current_track else "",
            time_str=f"{self.volume}%",
            progress=self.volume / 100.0,
            cover_image=cov_img,
            accent_rgb=(56, 189, 248),
            duration_s=2.8,
        )

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.config["shuffle"] = self.shuffle
        save_config(self.config)

        if self.play_queue:
            if self.current_track:
                curr_norm = os.path.normcase(self.current_track["path"])
                if self.shuffle:
                    others = [t for t in self.play_queue if os.path.normcase(t["path"]) != curr_norm]
                    random.shuffle(others)
                    self.play_queue = [self.current_track] + others
                    self.current_index = 0
                else:
                    if self.active_playlist and self.active_playlist != "Todas as Músicas":
                        self.play_queue = [t for t in self.tracks if t["playlist"] == self.active_playlist]
                    else:
                        self.play_queue = list(self.tracks)
                    for i, t in enumerate(self.play_queue):
                        if os.path.normcase(t["path"]) == curr_norm:
                            self.current_index = i
                            break
            elif self.shuffle:
                random.shuffle(self.play_queue)

        self.save_state_snapshot()
        state_lbl = "ATIVADO (ON)" if self.shuffle else "DESATIVADO (OFF)"
        cov_path = get_cover_icon_path(self.current_track) if self.current_track else ""
        cov_img = Image.open(cov_path) if cov_path and os.path.exists(cov_path) else None

        self.hud.show(
            header=f"🔀 MODO ALEATÓRIO {state_lbl}",
            title=self.current_track["display_title"] if self.current_track else f"Fila: {len(self.play_queue)} músicas",
            artist="Shuffle " + ("ON" if self.shuffle else "OFF"),
            time_str="Shuffle",
            progress=1.0 if self.shuffle else 0.0,
            cover_image=cov_img,
            accent_rgb=(45, 212, 191),
            duration_s=2.8,
        )

    def cycle_repeat(self):
        order = ["all", "one", "off"]
        idx = order.index(self.repeat) if self.repeat in order else 0
        self.repeat = order[(idx + 1) % len(order)]
        self.config["repeat"] = self.repeat
        save_config(self.config)
        self.save_state_snapshot()
        labels = {"all": "REPETIR PLAYLIST", "one": "REPETIR 1 MÚSICA", "off": "REPETIÇÃO DESATIVADA"}
        cov_path = get_cover_icon_path(self.current_track) if self.current_track else ""
        cov_img = Image.open(cov_path) if cov_path and os.path.exists(cov_path) else None

        self.hud.show(
            header=f"🔁 {labels[self.repeat]}",
            title=self.current_track["display_title"] if self.current_track else "Configuração de Repetição",
            artist=self.repeat.upper(),
            time_str=self.repeat.upper(),
            progress=1.0 if self.repeat != "off" else 0.0,
            cover_image=cov_img,
            accent_rgb=(168, 85, 247),
            duration_s=2.8,
        )

    def cycle_hud_position(self):
        positions = ["top_center", "top_right", "bottom_right"]
        curr = self.config.get("hud_position", "top_center")
        idx = positions.index(curr) if curr in positions else 0
        new_pos = positions[(idx + 1) % len(positions)]
        self.config["hud_position"] = new_pos
        save_config(self.config)
        self.hud._position_hud(new_pos)

        names = {
            "top_center": "Topo Central (Dynamic Island)",
            "top_right": "Canto Superior Direito",
            "bottom_right": "Canto Inferior Direito",
        }
        self.hud.show(
            header="✨ POSIÇÃO DO HUD ALTERADA",
            title=names[new_pos],
            artist="Estilo MyDockFinder / macOS",
            time_str="Posição",
            progress=1.0,
            accent_rgb=(236, 72, 153),
            duration_s=2.8,
        )

    def toggle_theme(self):
        curr = self.config.get("theme", "opal")
        new_theme = "dark" if curr == "opal" else "opal"
        self.config["theme"] = new_theme
        save_config(self.config)
        self.hud.theme = new_theme
        self.hud._cached_shadow = self.hud._build_shadow_layer()
        self.hud.update_content()

        theme_name = "Obsidian (Escuro)" if new_theme == "dark" else "Opal Glass (Claro)"
        self.hud.show(
            header="🎨 TEMA VISUAL ALTERADO",
            title=f"Tema Ativo: {theme_name}",
            artist="Clique no sol/lua para alternar",
            cur_time=self.hud.cur_time,
            total_time=self.hud.total_time,
            progress=self.hud.progress,
            cover_image=self.hud.cover_img,
            is_paused=(self.state != "playing"),
            is_fav=self.hud.is_fav,
            is_shuffle=self.shuffle,
            duration_s=4.0,
        )
        return new_theme

    def trigger_download_async(self, url: str, folder_name: str | None = None):
        import downloader

        self.hud.show(
            header="📥 INICIANDO DOWNLOAD DO YOUTUBE",
            title=folder_name or "Playlist YouTube Music",
            artist="Conectando...",
            time_str="Download",
            progress=0.1,
            accent_rgb=(56, 189, 248),
            duration_s=4.0,
        )

        def on_prog(pl_name, fn, pct):
            dummy_q = queue.Queue()
            self.cmd_queue.put(("download_progress", {"pl": pl_name, "fn": fn, "pct": pct}, dummy_q))

        def on_done(pl_name, count, err):
            dummy_q = queue.Queue()
            self.cmd_queue.put(("download_done", {"pl": pl_name, "count": count, "err": err}, dummy_q))

        downloader.start_download_async(
            url=url,
            folder_name=folder_name,
            on_progress=on_prog,
            on_finish=on_done,
        )

    def get_next_track_preview(self) -> dict | None:
        if not self.play_queue:
            return None
        nxt = (self.current_index + 1) % len(self.play_queue)
        return self.play_queue[nxt]

    def get_status_dict(self) -> dict:
        import downloader
        nxt = self.get_next_track_preview()
        return {
            "running": True,
            "state": self.state,
            "current_track": self.current_track,
            "next_track": nxt,
            "active_playlist": self.active_playlist,
            "volume": self.volume,
            "shuffle": self.shuffle,
            "repeat": self.repeat,
            "position_ms": self.position_ms,
            "duration_ms": self.duration_ms,
            "position_str": format_ms(self.position_ms),
            "duration_str": format_ms(self.duration_ms),
            "queue_length": len(self.play_queue),
            "total_tracks": len(self.tracks),
            "hud_position": self.config.get("hud_position", "top_center"),
            "download_state": dict(downloader.download_state),
            "updated_at": time.time(),
        }

    def save_state_snapshot(self):
        try:
            atomic_write_json(STATE_PATH, self.get_status_dict())
        except Exception:
            pass

    def handle_command(self, req: dict) -> dict:
        cmd = req.get("cmd", "status")
        if cmd == "status":
            return self.get_status_dict()

        reply_q: queue.Queue = queue.Queue()
        self.cmd_queue.put((cmd, req, reply_q))
        try:
            return reply_q.get(timeout=2.0)
        except queue.Empty:
            return self.get_status_dict()

    def _process_queued_commands(self):
        while not self.cmd_queue.empty():
            try:
                cmd, req, reply_q = self.cmd_queue.get_nowait()
            except queue.Empty:
                break

            try:
                if cmd == "play_track":
                    self.play_track_by_path(req.get("path", ""), req.get("playlist"))
                elif cmd == "play_playlist":
                    self.play_playlist(req.get("playlist", "Todas as Músicas"))
                elif cmd == "enqueue_next":
                    self.enqueue_next(req.get("path", ""))
                elif cmd == "toggle":
                    self.toggle_play_pause()
                elif cmd == "next":
                    self.next_track(auto_advanced=False)
                elif cmd == "prev":
                    self.prev_track()
                elif cmd == "seek":
                    new_pos = int(req.get("pos", 0))
                    self.audio.seek(new_pos, playing=(self.state == "playing"))
                    self.position_ms = new_pos
                    self.trigger_track_hud(prefix="⏩ Posição alterada")
                elif cmd == "toggle_fav":
                    self.toggle_favorite_current()
                elif cmd == "volume":
                    self.set_volume(int(req.get("value", 80)))
                elif cmd == "vol_delta":
                    self.set_volume(self.volume + int(req.get("delta", 10)))
                elif cmd == "shuffle":
                    self.toggle_shuffle()
                elif cmd == "repeat":
                    self.cycle_repeat()
                elif cmd == "hud":
                    if self.hud.alpha > 40 and self.hud.target_alpha > 0:
                        self.hud.target_alpha = 0
                    else:
                        self.trigger_track_hud(prefix="🎵 Tocando agora" if self.state == "playing" else "⏸ Status atual")
                elif cmd == "hud_pos":
                    self.cycle_hud_position()
                elif cmd == "toggle_theme":
                    self.toggle_theme()
                elif cmd == "rescan":
                    self.refresh_library_if_needed(force=True)
                    self.hud.show(
                        header="🔄 BIBLIOTECA ATUALIZADA",
                        title=f"{len(self.tracks)} músicas encontradas",
                        artist="Pronto para tocar",
                        progress=1.0,
                        accent_rgb=(16, 225, 125),
                        duration_s=2.8,
                    )
                elif cmd == "download_playlist":
                    self.trigger_download_async(req.get("url", ""), req.get("name"))
                elif cmd == "download_progress":
                    pl = req.get("pl", "Playlist")
                    fn = req.get("fn", "")
                    pct = req.get("pct", 0.0)
                    self.hud.show(
                        header=f"📥 BAIXANDO: {pl}",
                        title=fn,
                        artist=f"{pct:.0f}% concluído",
                        time_str=f"{pct:.0f}%",
                        progress=pct / 100.0,
                        accent_rgb=(56, 189, 248),
                        duration_s=2.5,
                    )
                elif cmd == "download_done":
                    pl = req.get("pl", "Playlist")
                    cnt = req.get("count", 0)
                    err = req.get("err")
                    self.refresh_library_if_needed(force=True)
                    if err:
                        self.hud.show(
                            header="⚠️ ERRO NO DOWNLOAD",
                            title=pl,
                            artist="Verifique URL",
                            progress=1.0,
                            accent_rgb=(239, 68, 68),
                            duration_s=4.0,
                        )
                    else:
                        self.hud.show(
                            header="🎉 DOWNLOAD CONCLUÍDO!",
                            title=f"{cnt} músicas adicionadas",
                            artist=f"Playlist '{pl}'",
                            progress=1.0,
                            accent_rgb=(16, 225, 125),
                            duration_s=4.0,
                        )
                elif cmd == "autostart":
                    from services.autostart import is_autostart_enabled, toggle_autostart
                    action = req.get("action", "toggle")
                    if action == "status":
                        enabled = is_autostart_enabled()
                    else:
                        enabled = toggle_autostart()
                    self.hud.show(
                        header="INICIALIZAÇÃO DO WINDOWS",
                        title="Iniciar com o Windows: " + ("ATIVADO" if enabled else "DESATIVADO"),
                        artist="Configuração salva com sucesso",
                        progress=1.0,
                        accent_rgb=(16, 225, 125) if enabled else (239, 68, 68),
                        duration_s=3.2,
                    )
                elif cmd == "stop_daemon":
                    self.audio.close()
                    self.state = "stopped"
                    self.save_state_snapshot()
                    reply_q.put({"running": False, "state": "stopped"})
                    self.root.after(100, self.root.destroy)
                    return
            except Exception:
                pass

            reply_q.put(self.get_status_dict())

    def _tick(self):
        try:
            self._process_queued_commands()

            now = time.time()
            self.hud.check_hover_and_animate()

            if self.state == "playing" and self.audio.is_open:
                self.position_ms = self.audio.get_position_ms()
                mode = self.audio.get_mode()
                if (self.duration_ms > 0 and self.position_ms >= self.duration_ms - 250) or mode == "stopped":
                    self.next_track(auto_advanced=True)
                elif int(now * 2) % 4 == 0:
                    self.save_state_snapshot()

                if self.hud.alpha > 20 and self.duration_ms > 0:
                    cur_sec = int(self.position_ms / 1000)
                    if cur_sec != getattr(self, "_last_hud_sec", -1) and not self.hud.is_hovered:
                        self._last_hud_sec = cur_sec
                        self.hud.progress = self.position_ms / float(self.duration_ms)
                        self.hud.cur_time = format_ms(self.position_ms)
                        self.hud.total_time = format_ms(self.duration_ms)
                        self.hud.update_content()
        except Exception:
            pass
        finally:
            self.root.after(35, self._tick)

    def _rpc_server_loop(self, srv: socket.socket):
        while True:
            try:
                conn, _ = srv.accept()
                with conn:
                    conn.settimeout(1.5)
                    data = conn.recv(65536)
                    if not data:
                        continue
                    req = json.loads(data.decode("utf-8"))
                    resp = self.handle_command(req)
                    conn.sendall(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            except Exception:
                pass

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        bound = False
        for _ in range(12):
            try:
                srv.bind((RPC_HOST, RPC_PORT))
                srv.listen(10)
                bound = True
                break
            except OSError:
                time.sleep(0.5)

        if not bound:
            sys.exit(0)

        t_rpc = threading.Thread(target=self._rpc_server_loop, args=(srv,), daemon=True)
        t_rpc.start()

        self.root.after(40, self._tick)
        self.root.mainloop()


if __name__ == "__main__":
    daemon = FlowMusicDaemon()
    daemon.run()
