# -*- coding: utf-8 -*-
"""
High-Resolution Vector Icon Renderer (Apple SF Symbols / Lucide style)
for FlowMusic 360 Dynamic Island HUD.
Eliminates all missing font glyphs / 'tofu' squares by rendering clean,
crisp anti-aliased RGBA vector bitmaps at any resolution.
"""

import math
import os
from PIL import Image, ImageDraw

HUD_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "hud")

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
                # Multiply target color with image's alpha mask
                alpha = im.split()[3]
                tinted = Image.new("RGBA", (size, size), (r, g, b, 255))
                tinted.putalpha(alpha)
                return tinted
            return im
        except Exception:
            pass
    return None



def render_play_icon(size: int = 18, color: tuple = (255, 255, 255, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Lucide play: sleek equilateral triangle with rounded appearance
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
    # Two rounded vertical pill bars
    draw.rounded_rectangle(
        [6 * s / 24, 4.5 * s / 24, 10 * s / 24, 19.5 * s / 24],
        radius=r,
        fill=color,
    )
    draw.rounded_rectangle(
        [14 * s / 24, 4.5 * s / 24, 18 * s / 24, 19.5 * s / 24],
        radius=r,
        fill=color,
    )
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_skip_forward_icon(size: int = 18, color: tuple = (160, 174, 192, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Triangle pointing right
    pts = [
        (5 * s / 24, 5 * s / 24),
        (16 * s / 24, 12 * s / 24),
        (5 * s / 24, 19 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    # End bar
    r = int(1.2 * scale)
    draw.rounded_rectangle(
        [18 * s / 24, 5 * s / 24, 20.5 * s / 24, 19 * s / 24],
        radius=r,
        fill=color,
    )
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_skip_back_icon(size: int = 18, color: tuple = (160, 174, 192, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Triangle pointing left
    pts = [
        (19 * s / 24, 5 * s / 24),
        (8 * s / 24, 12 * s / 24),
        (19 * s / 24, 19 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    # Start bar
    r = int(1.2 * scale)
    draw.rounded_rectangle(
        [3.5 * s / 24, 5 * s / 24, 6 * s / 24, 19 * s / 24],
        radius=r,
        fill=color,
    )
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render_heart_icon(
    size: int = 18,
    color: tuple = (244, 63, 94, 255),
    filled: bool = True,
) -> Image.Image:
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


# Cache of rendered icons for microsecond-fast HUD frames
_icon_cache: dict = {}


def get_icon(name: str, size: int = 18, color: tuple = (255, 255, 255, 255)) -> Image.Image:
    key = (name, size, color)
    if key in _icon_cache:
        return _icon_cache[key]

    # 1. Try loading from assets/hud PNG first
    img = load_png_asset(name, size, color)

    # 2. Vector fallback if asset not present
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
