# -*- coding: utf-8 -*-
"""
Music Library Scanner, Metadata Parser, and Favorites Manager for FlowMusic 360.
"""

import json
import os
import re
import struct
import unicodedata
from typing import Dict, List, Optional, Set

APPMUSIC_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APPMUSIC_DIR, "config.json")
STATE_PATH = os.path.join(APPMUSIC_DIR, "state.json")
FAVORITES_PATH = os.path.join(APPMUSIC_DIR, "favorites.json")

DEFAULT_CONFIG = {
    "music_dirs": [
        os.path.join(os.path.expanduser("~"), "Downloads", "YouTube_Music"),
        os.path.join(os.path.expanduser("~"), "Music"),
    ],
    "volume": 80,
    "shuffle": False,
    "repeat": "all",  # "all", "one", "off"
    "hud_position": "top_center",  # "top_center" (Dynamic Island), "top_right", "bottom_right"
    "hud_duration_ms": 5000,
    "hotkeys_enabled": True,
    "theme": "opal",
}

SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac", ".aac", ".wma", ".webm", ".ogg"}
TRACK_PREFIX_RE = re.compile(r"^\s*(\d{1,3})\s*[-_.]+\s*(.+)$")


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                if isinstance(user_cfg, dict):
                    cfg.update(user_cfg)
        except Exception:
            pass
    if "music_dirs" in cfg and isinstance(cfg["music_dirs"], list):
        cfg["music_dirs"] = [os.path.expanduser(os.path.expandvars(p)) for p in cfg["music_dirs"]]
    return cfg


def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_favorites() -> Set[str]:
    if not os.path.exists(FAVORITES_PATH):
        return set()
    try:
        with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(os.path.normcase(p) for p in data)
    except Exception:
        pass
    return set()


def save_favorites(favs: Set[str]) -> None:
    try:
        with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(favs)), f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def is_favorite(filepath: str, favs: Optional[Set[str]] = None) -> bool:
    if favs is None:
        favs = load_favorites()
    return os.path.normcase(os.path.abspath(filepath)) in favs


def toggle_favorite(filepath: str) -> bool:
    favs = load_favorites()
    norm = os.path.normcase(os.path.abspath(filepath))
    if norm in favs:
        favs.remove(norm)
        added = False
    else:
        favs.add(norm)
        added = True
    save_favorites(favs)
    return added


def normalize_text(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_str.lower().strip()


def natural_sort_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def read_id3v2_tags(filepath: str) -> dict:
    """Fast, zero-dependency ID3v2 title and artist reader in pure Python."""
    tags = {"artist": "", "title": ""}
    try:
        with open(filepath, "rb") as f:
            header = f.read(10)
            if len(header) < 10 or header[:3] != b"ID3":
                return tags
            version_major = header[3]
            # synchsafe integer size
            tag_size = (
                (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]
            )
            raw = f.read(min(tag_size, 32768))

            idx = 0
            while idx + 10 < len(raw):
                frame_id = raw[idx : idx + 4].decode("latin1", errors="ignore")
                if not frame_id or frame_id[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    break
                if version_major == 4:
                    frame_len = (
                        (raw[idx + 4] << 21)
                        | (raw[idx + 5] << 14)
                        | (raw[idx + 6] << 7)
                        | raw[idx + 7]
                    )
                else:
                    frame_len = struct.unpack(">I", raw[idx + 4 : idx + 8])[0]
                idx += 10
                if frame_len <= 0 or idx + frame_len > len(raw):
                    break
                data = raw[idx : idx + frame_len]
                idx += frame_len

                if frame_id in ("TIT2", "TPE1", "TALB"):
                    encoding = data[0] if len(data) > 0 else 0
                    text_bytes = data[1:]
                    val = ""
                    try:
                        if encoding == 0:
                            val = text_bytes.decode("latin1", errors="ignore")
                        elif encoding in (1, 2):
                            val = text_bytes.decode("utf-16", errors="ignore")
                        elif encoding == 3:
                            val = text_bytes.decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                    val = val.strip().strip("\x00")
                    if frame_id == "TIT2" and not tags["title"]:
                        tags["title"] = val
                    elif frame_id == "TPE1" and not tags["artist"]:
                        tags["artist"] = val
    except Exception:
        pass
    return tags


def parse_track_filename(filepath: str, root_dir: str, favs: Optional[Set[str]] = None) -> dict:
    filename = os.path.basename(filepath)
    stem, ext = os.path.splitext(filename)
    parent_dir = os.path.dirname(filepath)

    if os.path.normcase(os.path.abspath(parent_dir)) == os.path.normcase(os.path.abspath(root_dir)):
        playlist = "YouTube Music (Geral)"
    else:
        playlist = os.path.basename(parent_dir)

    match = TRACK_PREFIX_RE.match(stem)
    if match:
        track_num = match.group(1).zfill(2)
        clean_title = match.group(2).strip()
    else:
        track_num = ""
        clean_title = stem.strip()

    id3 = read_id3v2_tags(filepath) if ext.lower() == ".mp3" else {}
    artist = id3.get("artist") or ""

    # If title looks like "Artist - Title"
    if " - " in clean_title and not artist:
        parts = clean_title.split(" - ", 1)
        artist = parts[0].strip()
        clean_title = parts[1].strip()

    display_title = f"{track_num} - {clean_title}" if track_num else clean_title
    is_fav = is_favorite(filepath, favs)

    search_blob = normalize_text(f"{display_title} {clean_title} {artist} {playlist} {stem}")

    return {
        "path": os.path.abspath(filepath),
        "filename": filename,
        "stem": stem,
        "title": clean_title,
        "display_title": display_title,
        "artist": artist,
        "track_num": track_num,
        "playlist": playlist,
        "ext": ext.lower(),
        "is_favorite": is_fav,
        "search_blob": search_blob,
    }


def scan_library(music_dirs: Optional[List[str]] = None) -> List[dict]:
    if music_dirs is None:
        music_dirs = load_config().get("music_dirs", DEFAULT_CONFIG["music_dirs"])

    favs = load_favorites()
    tracks: List[dict] = []
    seen_paths = set()

    for root_dir in music_dirs:
        if not root_dir or not os.path.isdir(root_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames.sort(key=natural_sort_key)
            filenames.sort(key=natural_sort_key)
            for fn in filenames:
                if fn.endswith(".part") or fn.endswith(".ytdl") or fn.startswith("."):
                    continue
                _, ext = os.path.splitext(fn)
                if ext.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                full_path = os.path.abspath(os.path.join(dirpath, fn))
                norm_path = os.path.normcase(full_path)
                if norm_path in seen_paths:
                    continue
                seen_paths.add(norm_path)
                tracks.append(parse_track_filename(full_path, root_dir, favs))

    return tracks


def get_playlists(tracks: Optional[List[dict]] = None) -> Dict[str, List[dict]]:
    if tracks is None:
        tracks = scan_library()
    playlists: Dict[str, List[dict]] = {}

    # Check for favorited tracks to build the special virtual playlist
    fav_tracks = [t for t in tracks if t.get("is_favorite")]
    if fav_tracks:
        playlists["❤️ Favoritas"] = fav_tracks

    for t in tracks:
        pl = t["playlist"]
        playlists.setdefault(pl, []).append(t)
    return playlists


def search_tracks(query: str, tracks: Optional[List[dict]] = None, limit: int = 35) -> List[dict]:
    if tracks is None:
        tracks = scan_library()
    q_norm = normalize_text(query)
    if not q_norm:
        return tracks[:limit]

    tokens = [tok for tok in q_norm.split() if tok]
    scored = []
    for t in tracks:
        blob = t["search_blob"]
        title_norm = normalize_text(t["title"])
        disp_norm = normalize_text(t["display_title"])
        art_norm = normalize_text(t.get("artist", ""))

        # All tokens must match somewhere in search_blob
        if not all(tok in blob for tok in tokens):
            continue

        score = 50
        if title_norm == q_norm or disp_norm == q_norm:
            score += 100
        elif title_norm.startswith(q_norm) or disp_norm.startswith(q_norm):
            score += 65
        elif q_norm in title_norm or (art_norm and q_norm in art_norm):
            score += 45
        elif t["track_num"] and t["track_num"].lstrip("0") == q_norm.lstrip("0"):
            score += 85

        if t.get("is_favorite"):
            score += 15

        scored.append((score, t))

    scored.sort(key=lambda item: (-item[0], natural_sort_key(item[1]["display_title"])))
    return [item[1] for item in scored[:limit]]
