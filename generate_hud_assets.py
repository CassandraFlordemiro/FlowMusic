# -*- coding: utf-8 -*-
"""
Generates ultra-crisp 64x64 and 128x128 RGBA transparent PNG icons (Lucide / SF Symbols style)
for the FlowMusic 360 Dynamic Island HUD and Flow Launcher.
Uses Pillow with 4x supersampled vector geometry for buttery smooth antialiasing.
"""

import math
import os
from PIL import Image, ImageDraw


def create_canvas(scale: int = 4, target_size: int = 64):
    s = target_size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s, scale


def finish(img: Image.Image, target_size: int = 64) -> Image.Image:
    return img.resize((target_size, target_size), Image.Resampling.LANCZOS)


def gen_play(target_size=64, color=(255, 255, 255, 255)):
    img, draw, s, scale = create_canvas(4, target_size)
    # Lucide play: sleek equilateral triangle with rounded look
    # Normalized coords on 24x24 grid:
    # (6.5, 4.5), (19.5, 12), (6.5, 19.5)
    pts = [
        (6.5 * s / 24, 4.5 * s / 24),
        (19.8 * s / 24, 12.0 * s / 24),
        (6.5 * s / 24, 19.5 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    return finish(img, target_size)


def gen_pause(target_size=64, color=(255, 255, 255, 255)):
    img, draw, s, scale = create_canvas(4, target_size)
    r = int(2.2 * scale)
    # Two rounded vertical pill bars
    draw.rounded_rectangle(
        [6.0 * s / 24, 4.5 * s / 24, 10.0 * s / 24, 19.5 * s / 24],
        radius=r,
        fill=color,
    )
    draw.rounded_rectangle(
        [14.0 * s / 24, 4.5 * s / 24, 18.0 * s / 24, 19.5 * s / 24],
        radius=r,
        fill=color,
    )
    return finish(img, target_size)


def gen_next(target_size=64, color=(255, 255, 255, 255)):
    img, draw, s, scale = create_canvas(4, target_size)
    # Triangle pointing right
    pts = [
        (5.0 * s / 24, 5.0 * s / 24),
        (16.0 * s / 24, 12.0 * s / 24),
        (5.0 * s / 24, 19.0 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    # End bar
    r = int(1.4 * scale)
    draw.rounded_rectangle(
        [18.0 * s / 24, 5.0 * s / 24, 20.5 * s / 24, 19.0 * s / 24],
        radius=r,
        fill=color,
    )
    return finish(img, target_size)


def gen_prev(target_size=64, color=(255, 255, 255, 255)):
    img, draw, s, scale = create_canvas(4, target_size)
    # Triangle pointing left
    pts = [
        (19.0 * s / 24, 5.0 * s / 24),
        (8.0 * s / 24, 12.0 * s / 24),
        (19.0 * s / 24, 19.0 * s / 24),
    ]
    draw.polygon(pts, fill=color)
    # Start bar
    r = int(1.4 * scale)
    draw.rounded_rectangle(
        [3.5 * s / 24, 5.0 * s / 24, 6.0 * s / 24, 19.0 * s / 24],
        radius=r,
        fill=color,
    )
    return finish(img, target_size)


def gen_heart(target_size=64, color=(255, 255, 255, 255), filled=False):
    img, draw, s, scale = create_canvas(4, target_size)
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
        draw.polygon(pts, outline=color, width=int(2.0 * scale))
    return finish(img, target_size)


def gen_shuffle(target_size=64, color=(255, 255, 255, 255)):
    img, draw, s, scale = create_canvas(4, target_size)
    w = int(2.0 * scale)
    # Arrow 1: top-left to bottom-right
    # Curve from (3, 6) to (21, 18)
    draw.line([(3 * s / 24, 6 * s / 24), (9 * s / 24, 6 * s / 24), (15 * s / 24, 18 * s / 24), (21 * s / 24, 18 * s / 24)], fill=color, width=w, joint="curve")
    # Arrow head at (21, 18)
    draw.polygon([(21 * s / 24, 15 * s / 24), (21 * s / 24, 21 * s / 24), (17 * s / 24, 21 * s / 24)], fill=color)

    # Arrow 2: bottom-left to top-right
    draw.line([(3 * s / 24, 18 * s / 24), (9 * s / 24, 18 * s / 24), (11 * s / 24, 14 * s / 24)], fill=color, width=w)
    draw.line([(13 * s / 24, 10 * s / 24), (15 * s / 24, 6 * s / 24), (21 * s / 24, 6 * s / 24)], fill=color, width=w)
    draw.polygon([(21 * s / 24, 9 * s / 24), (21 * s / 24, 3 * s / 24), (17 * s / 24, 3 * s / 24)], fill=color)
    return finish(img, target_size)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "assets", "hud")
    os.makedirs(out_dir, exist_ok=True)

    # Base colors:
    # 1. Neutral frosted silver for inactive/normal state
    c_silver = (200, 214, 229, 255)
    # 2. Pure bright white for active/hover state
    c_white = (255, 255, 255, 255)
    # 3. Vivid Apple Rose / Red for Favorite
    c_rose = (244, 63, 94, 255)

    icons = {
        "play.png": gen_play(64, c_white),
        "pause.png": gen_pause(64, c_white),
        "next.png": gen_next(64, c_silver),
        "prev.png": gen_prev(64, c_silver),
        "heart.png": gen_heart(64, c_silver, filled=False),
        "heart_active.png": gen_heart(64, c_rose, filled=True),
        "shuffle.png": gen_shuffle(64, c_silver),
    }

    for name, img in icons.items():
        path = os.path.join(out_dir, name)
        img.save(path, "PNG")
        print(f"Generated {path}")


if __name__ == "__main__":
    main()

