# -*- coding: utf-8 -*-
"""
High-Resolution Album Cover Art Provider & Squircle Cache for FlowMusic 360.
Zero-dependency on Flow Launcher side: uses only stdlib (hashlib, os, re, json, urllib).
Pillow is imported lazily only when generating/processing new images.
"""

import hashlib
import json
import os
import re
import struct
import threading
import urllib.parse
import urllib.request

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

APPMUSIC_DIR = os.path.dirname(os.path.abspath(__file__))
COVERS_CACHE_DIR = os.path.join(APPMUSIC_DIR, "cache", "covers")
os.makedirs(COVERS_CACHE_DIR, exist_ok=True)

DEFAULT_TRACK_ICON = os.path.join(APPMUSIC_DIR, "assets", "track.png")
DEFAULT_HEART_ICON = os.path.join(APPMUSIC_DIR, "assets", "heart.png")

_fetch_queue: set[str] = set()
_lock = threading.Lock()


def get_track_cache_key(track_path: str) -> str:
    norm = os.path.normcase(os.path.abspath(track_path))
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:16]


def extract_embedded_apic(filepath: str) -> bytes | None:
    """Extract embedded ID3 APIC picture bytes if present."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(10)
            if len(header) < 10 or header[:3] != b"ID3":
                return None
            version = header[3]
            tag_size = (
                (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]
            )
            raw = f.read(min(tag_size, 1024 * 1024 * 8))

            idx = 0
            while idx + 10 < len(raw):
                fid = raw[idx : idx + 4].decode("latin1", errors="ignore")
                if not fid or fid[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    break
                if version == 4:
                    flen = (
                        (raw[idx + 4] << 21)
                        | (raw[idx + 5] << 14)
                        | (raw[idx + 6] << 7)
                        | raw[idx + 7]
                    )
                else:
                    flen = struct.unpack(">I", raw[idx + 4 : idx + 8])[0]
                idx += 10
                if flen <= 0 or idx + flen > len(raw):
                    break
                data = raw[idx : idx + flen]
                idx += flen

                if fid == "APIC" and len(data) > 10:
                    mime_end = data.find(b"\x00", 1)
                    if mime_end != -1:
                        pic_data_start = mime_end + 2
                        if data[0] in (1, 2):  # UTF-16
                            desc_end = data.find(b"\x00\x00", pic_data_start)
                            if desc_end != -1:
                                pic_data_start = desc_end + 2
                        else:
                            desc_end = data.find(b"\x00", pic_data_start)
                            if desc_end != -1:
                                pic_data_start = desc_end + 1
                        if pic_data_start < len(data):
                            return data[pic_data_start:]
    except Exception:
        pass
    return None


def fetch_itunes_cover_url(query: str) -> tuple[str | None, str | None]:
    """Queries iTunes Search API for official high-resolution album cover and artist."""
    cleaned = re.sub(r"^\d{1,3}\s*[-_.]+\s*", "", query)
    cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()

    try:
        url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
            {"term": cleaned, "entity": "song", "limit": 1}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("results"):
                res = data["results"][0]
                art_url = res.get("artworkUrl100", "")
                if art_url:
                    art_url = art_url.replace("100x100bb", "600x600bb")
                artist = res.get("artistName", "")
                return art_url, artist
    except Exception:
        pass
    return None, None


def make_squircle_image(raw_image, size: int = 128, radius: int = 24):
    if not HAS_PIL:
        return None
    img = raw_image.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    scale = 4
    mask = Image.new("L", (size * scale, size * scale), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [0, 0, size * scale - 1, size * scale - 1],
        radius=radius * scale,
        fill=255,
    )
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    img.putalpha(mask)

    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rounded_rectangle(
        [0, 0, size - 1, size - 1],
        radius=radius,
        outline=(255, 255, 255, 45),
        width=1,
    )
    return Image.alpha_composite(img, overlay)


def make_circular_image(raw_image, size: int = 48):
    if not HAS_PIL:
        return None
    img = raw_image.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    scale = 4
    mask = Image.new("L", (size * scale, size * scale), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, size * scale - 1, size * scale - 1], fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    img.putalpha(mask)

    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.ellipse([0, 0, size - 1, size - 1], outline=(255, 255, 255, 55), width=1)
    return Image.alpha_composite(img, overlay)


def process_and_cache_cover(img_data: bytes, cache_key: str) -> None:
    if not HAS_PIL:
        return
    import io
    try:
        raw = Image.open(io.BytesIO(img_data))
        sq_128 = make_squircle_image(raw, size=128, radius=26)
        if sq_128:
            sq_128.save(os.path.join(COVERS_CACHE_DIR, f"{cache_key}_128.png"), format="PNG")
        circ_48 = make_circular_image(raw, size=48)
        if circ_48:
            circ_48.save(os.path.join(COVERS_CACHE_DIR, f"{cache_key}_48.png"), format="PNG")
    except Exception:
        pass


def get_cover_icon_path(track_info: dict, allow_fetch_sync: bool = False) -> str:
    path = track_info.get("path", "")
    if not path:
        return DEFAULT_TRACK_ICON

    cache_key = get_track_cache_key(path)
    out_file = os.path.join(COVERS_CACHE_DIR, f"{cache_key}_128.png")

    # Fast path: already on disk (works in Flow Launcher's embedded Python with ZERO dependencies!)
    if os.path.exists(out_file):
        return out_file

    if HAS_PIL and allow_fetch_sync:
        _fetch_and_create_cover(track_info, cache_key)
        if os.path.exists(out_file):
            return out_file

    if HAS_PIL:
        with _lock:
            if cache_key not in _fetch_queue:
                _fetch_queue.add(cache_key)
                threading.Thread(
                    target=_fetch_and_create_cover,
                    args=(track_info, cache_key),
                    daemon=True,
                ).start()

    return DEFAULT_HEART_ICON if track_info.get("is_favorite") else DEFAULT_TRACK_ICON


def get_hud_cover_file(track_path: str) -> str | None:
    if not track_path:
        return None
    cache_key = get_track_cache_key(track_path)
    hud_file = os.path.join(COVERS_CACHE_DIR, f"{cache_key}_48.png")
    if os.path.exists(hud_file):
        return hud_file
    return None


def _fetch_and_create_cover(track_info: dict, cache_key: str):
    if not HAS_PIL:
        return
    path = track_info.get("path", "")
    out_file = os.path.join(COVERS_CACHE_DIR, f"{cache_key}_128.png")
    if os.path.exists(out_file):
        return

    apic_bytes = extract_embedded_apic(path)
    if apic_bytes:
        process_and_cache_cover(apic_bytes, cache_key)
        return

    parent_dir = os.path.dirname(path)
    for cand in ("cover.jpg", "cover.png", "folder.jpg", "folder.png"):
        cand_path = os.path.join(parent_dir, cand)
        if os.path.exists(cand_path):
            try:
                with open(cand_path, "rb") as f:
                    process_and_cache_cover(f.read(), cache_key)
                    return
            except Exception:
                pass

    title = track_info.get("title", "")
    artist = track_info.get("artist", "")
    query = f"{artist} {title}" if artist else title
    art_url, _ = fetch_itunes_cover_url(query)

    if art_url:
        try:
            req = urllib.request.Request(art_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                process_and_cache_cover(data, cache_key)
        except Exception:
            pass


def prefetch_covers_for_library(tracks: list[dict]):
    def worker():
        for t in tracks:
            cache_key = get_track_cache_key(t["path"])
            out_file = os.path.join(COVERS_CACHE_DIR, f"{cache_key}_128.png")
            if not os.path.exists(out_file):
                _fetch_and_create_cover(t, cache_key)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
