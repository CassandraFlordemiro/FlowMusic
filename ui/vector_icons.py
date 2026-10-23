# -*- coding: utf-8 -*-
"""
FlowMusic 360 - High-Resolution Vector Icon Renderer & Asset Loader.
Loads crisp Lucide / SF Symbols PNGs from assets/hud/ with fallback to pure vector geometry.
"""

import math
import os
from PIL import Image, ImageDraw

from core.config import HUD_ASSETS_DIR
from core.logger import get_logger

logger = get_logger("VectorIcons")

ICON_FILE_MAP = {
    "play": "play.png",
    "pause": "pause.png",
    "next": "next.png",
    "prev": "prev.png",
    "heart_filled": "heart_active.png",
    "heart_outline": "heart.png",
    "shuffle": "shuffle.png",
}


def load_png_asset(name: str, size: int, color: tuple = None) -> Image.Image:
    filename = ICON_FILE_MAP.get(name, f"{name}.png")
    path = os.path.join(HUD_ASSETS_DIR, filename)
    if os.path.isfile(path):
        try:
            im = Image.open(path).convert("RGBA")
            im = im.resize((size, size), Image.Resampling.LANCZOS)
            if color:
                r, g, b = color[:3]
                alpha = im.split()[3]
                tinted = Image.new("RGBA", (size, size), (r, g, b, 255))
                tinted.putalpha(alpha)
                return tinted
            return im
        except Exception as e:
            logger.debug(f"Failed loading PNG asset {filename}: {e}")
    return None


def render_play_icon(size: int = 18, color: tuple = (255, 255, 255, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [
        (6.5 * s / 24, 4.5 * s / 24),
        (19.5 * s / 24, 12 * s / 24),
        (6.5 * s / 24, 19.5 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_pause_icon(size: int = 18, color: tuple = (255, 255, 255, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = int(1.8 * scale)
    draw.rounded_rectangle([6 * s / 24, 4.5 * s / 24, 10 * s / 24, 19.5 * s / 24], radius=r, fill=color)
    draw.rounded_rectangle([14 * s / 24, 4.5 * s / 24, 18 * s / 24, 19.5 * s / 24], radius=r, fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_skip_forward_icon(size: int = 18, color: tuple = (160, 174, 192, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [
        (5 * s / 24, 5 * s / 24),
        (16 * s / 24, 12 * s / 24),
        (5 * s / 24, 19 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    r = int(1.2 * scale)
    draw.rounded_rectangle([18 * s / 24, 5 * s / 24, 20.5 * s / 24, 19 * s / 24], radius=r, fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_skip_back_icon(size: int = 18, color: tuple = (160, 174, 192, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [
        (19 * s / 24, 5 * s / 24),
        (8 * s / 24, 12 * s / 24),
        (19 * s / 24, 19 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    r = int(1.2 * scale)
    draw.rounded_rectangle([3.5 * s / 24, 5 * s / 24, 6 * s / 24, 19 * s / 24], radius=r, fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_heart_icon(size: int = 18, color: tuple = (244, 63, 94, 255), filled: bool = True) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = []
    for deg in range(0, 360, 4):
        t = math.radians(deg)
        x = 16 * (math.sin(t) ** 3)
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        px = s / 2 + x * (s / 39)
        py = s / 2 + (y + 1.2) * (s / 39)
        pts.append((px, py))
    if filled:
        draw.polygon(pts, fill=color)
    else:
        draw.polygon(pts, outline=color, width=int(1.8 * scale))
    return img.resize((size, size), Image.Resampling.LANCZOS)


_icon_cache: dict = {}


def get_icon(name: str, size: int = 18, color: tuple = (255, 255, 255, 255)) -> Image.Image:
    key = (name, size, color)
    if key in _icon_cache:
        return _icon_cache[key]

    img = load_png_asset(name, size, color)
    if img is None:
        if name == "play":
            img = render_play_icon(size, color)
        elif name == "pause":
            img = render_pause_icon(size, color)
        elif name == "next":
            img = render_skip_forward_icon(size, color)
        elif name == "prev":
            img = render_skip_back_icon(size, color)
        elif name == "heart_filled":
            img = render_heart_icon(size, color, filled=True)
        elif name == "heart_outline":
            img = render_heart_icon(size, color, filled=False)
        else:
            img = render_play_icon(size, color)

    _icon_cache[key] = img
    return img

