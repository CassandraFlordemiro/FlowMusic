# -*- coding: utf-8 -*-
"""
Generates sleek, minimalist macOS Sonoma / Xbox 360 style 128x128 RGBA PNG icons
using pure Python standard library (struct + zlib) with supersampled anti-aliasing.
"""

import math
import os
import struct
import zlib


def write_png(filepath: str, width: int, height: int, rgba_bytes: bytes):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    raw_rows = bytearray()
    stride = width * 4
    for y in range(height):
        raw_rows.append(0)  # Filter type 0 (None)
        raw_rows.extend(rgba_bytes[y * stride : (y + 1) * stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw_rows), 9)

    with open(filepath, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", compressed))
        f.write(chunk(b"IEND", b""))


def sd_rounded_box(px: float, py: float, cx: float, cy: float, hw: float, hh: float, r: float) -> float:
    dx = abs(px - cx) - hw + r
    dy = abs(py - cy) - hh + r
    return math.hypot(max(dx, 0.0), max(dy, 0.0)) + min(max(dx, dy), 0.0) - r


def sd_circle(px: float, py: float, cx: float, cy: float, r: float) -> float:
    return math.hypot(px - cx, py - cy) - r


def sd_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    pax, pay = px - ax, py - ay
    bax, bay = bx - ax, by - ay
    denom = bax * bax + bay * bay
    h = max(0.0, min(1.0, (pax * bax + pay * bay) / denom)) if denom > 0 else 0.0
    return math.hypot(pax - bax * h, pay - bay * h)


def sd_triangle(px: float, py: float, p0, p1, p2) -> float:
    e0 = (p1[0] - p0[0], p1[1] - p0[1])
    e1 = (p2[0] - p1[0], p2[1] - p1[1])
    e2 = (p0[0] - p2[0], p0[1] - p2[1])
    v0 = (px - p0[0], py - p0[1])
    v1 = (px - p1[0], py - p1[1])
    v2 = (px - p2[0], py - p2[1])

    def clamp01(v):
        return max(0.0, min(1.0, v))

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1]

    pq0 = (v0[0] - e0[0] * clamp01(dot(v0, e0) / dot(e0, e0)), v0[1] - e0[1] * clamp01(dot(v0, e0) / dot(e0, e0)))
    pq1 = (v1[0] - e1[0] * clamp01(dot(v1, e1) / dot(e1, e1)), v1[1] - e1[1] * clamp01(dot(v1, e1) / dot(e1, e1)))
    pq2 = (v2[0] - e2[0] * clamp01(dot(v2, e2) / dot(e2, e2)), v2[1] - e2[1] * clamp01(dot(v2, e2) / dot(e2, e2)))

    s = 1.0 if (e0[0] * e2[1] - e0[1] * e2[0]) >= 0 else -1.0
    d0 = (dot(pq0, pq0), s * (v0[0] * e0[1] - v0[1] * e0[0]))
    d1 = (dot(pq1, pq1), s * (v1[0] * e1[1] - v1[1] * e1[0]))
    d2 = (dot(pq2, pq2), s * (v2[0] * e2[1] - v2[1] * e2[0]))

    min_d = min(d0[0], d1[0], d2[0])
    min_s = min(d0[1], d1[1], d2[1])
    return -math.sqrt(min_d) * (1.0 if min_s > 0 else -1.0)


def sd_heart(px: float, py: float) -> float:
    # Centered heart shape
    x = (px - 64.0) / 36.0
    y = -(py - 60.0) / 36.0
    # Equation (x^2 + y^2 - 1)^3 - x^2 * y^3
    f = (x * x + y * y - 0.7) ** 3 - x * x * (y ** 3)
    return f * 12.0


def sd_download(px: float, py: float) -> float:
    # Arrow pointing down + base tray
    stem = sd_rounded_box(px, py, 64, 52, 4.0, 14, 2.5)
    tip = sd_triangle(px, py, (44, 62), (84, 62), (64, 82)) - 2.0
    tray_bottom = sd_rounded_box(px, py, 64, 88, 22, 3.5, 2.5)
    tray_l = sd_rounded_box(px, py, 43, 80, 3.5, 9, 2.0)
    tray_r = sd_rounded_box(px, py, 85, 80, 3.5, 9, 2.0)
    return min(stem, tip, tray_bottom, tray_l, tray_r)


def render_icon(filepath: str, accent_top, accent_bot, symbol_fn, size: int = 128):
    buf = bytearray(size * size * 4)
    for y in range(size):
        t = y / max(1, size - 1)
        for x in range(size):
            d_bg = sd_rounded_box(x + 0.5, y + 0.5, 64.0, 64.0, 56.0, 56.0, 26.0)
            if d_bg > 1.0:
                continue

            alpha_bg = max(0.0, min(1.0, 0.5 - d_bg))
            r_bg = int(20 * (1 - t) + 12 * t + accent_top[0] * 0.12 * (1 - t) + accent_bot[0] * 0.08 * t)
            g_bg = int(22 * (1 - t) + 14 * t + accent_top[1] * 0.12 * (1 - t) + accent_bot[1] * 0.08 * t)
            b_bg = int(28 * (1 - t) + 18 * t + accent_top[2] * 0.12 * (1 - t) + accent_bot[2] * 0.08 * t)

            border_dist = abs(d_bg + 1.5) - 1.2
            if border_dist < 1.0:
                b_cov = max(0.0, min(1.0, 0.5 - border_dist)) * 0.55
                ar = accent_top[0] * (1 - t) + accent_bot[0] * t
                ag = accent_top[1] * (1 - t) + accent_bot[1] * t
                ab = accent_top[2] * (1 - t) + accent_bot[2] * t
                r_bg = int(r_bg * (1 - b_cov) + ar * b_cov)
                g_bg = int(g_bg * (1 - b_cov) + ag * b_cov)
                b_bg = int(b_bg * (1 - b_cov) + ab * b_cov)

            d_sym = symbol_fn(x + 0.5, y + 0.5)
            sym_cov = max(0.0, min(1.0, 0.5 - d_sym))
            glow_cov = math.exp(-max(0.0, d_sym) * 0.18) * 0.28 if d_sym > 0 else 0.0

            sr = accent_top[0] * (1 - t) + accent_bot[0] * t
            sg = accent_top[1] * (1 - t) + accent_bot[1] * t
            sb = accent_top[2] * (1 - t) + accent_bot[2] * t

            r = r_bg * (1 - glow_cov) + sr * glow_cov
            g = g_bg * (1 - glow_cov) + sg * glow_cov
            b = b_bg * (1 - glow_cov) + sb * glow_cov

            fg_r = min(255, sr * 0.35 + 255 * 0.65)
            fg_g = min(255, sg * 0.35 + 255 * 0.65)
            fg_b = min(255, sb * 0.35 + 255 * 0.65)

            r = int(max(0, min(255, r * (1 - sym_cov) + fg_r * sym_cov)))
            g = int(max(0, min(255, g * (1 - sym_cov) + fg_g * sym_cov)))
            b = int(max(0, min(255, b * (1 - sym_cov) + fg_b * sym_cov)))
            a = int(max(0, min(255, alpha_bg * 255)))

            idx = (y * size + x) * 4
            buf[idx] = r
            buf[idx + 1] = g
            buf[idx + 2] = b
            buf[idx + 3] = a

    write_png(filepath, size, size, bytes(buf))


def sym_app(x, y):
    ring = abs(sd_circle(x, y, 64, 64, 38)) - 3.2
    b1 = sd_rounded_box(x, y, 48, 66, 3.8, 12, 3.5)
    b2 = sd_rounded_box(x, y, 59, 64, 3.8, 21, 3.5)
    b3 = sd_rounded_box(x, y, 70, 62, 3.8, 16, 3.5)
    b4 = sd_rounded_box(x, y, 81, 67, 3.8, 10, 3.5)
    return min(ring, b1, b2, b3, b4)


def sym_play(x, y):
    return sd_triangle(x, y, (48, 40), (48, 88), (88, 64)) - 3.0


def sym_pause(x, y):
    b1 = sd_rounded_box(x, y, 51, 64, 6.5, 22, 4.0)
    b2 = sd_rounded_box(x, y, 77, 64, 6.5, 22, 4.0)
    return min(b1, b2)


def sym_next(x, y):
    t1 = sd_triangle(x, y, (40, 42), (40, 86), (74, 64)) - 2.5
    bar = sd_rounded_box(x, y, 84, 64, 4.5, 22, 3.5)
    return min(t1, bar)


def sym_prev(x, y):
    t1 = sd_triangle(x, y, (88, 42), (88, 86), (54, 64)) - 2.5
    bar = sd_rounded_box(x, y, 44, 64, 4.5, 22, 3.5)
    return min(t1, bar)


def sym_shuffle(x, y):
    s1 = sd_segment(x, y, 40, 48, 86, 80) - 3.5
    s2 = sd_segment(x, y, 40, 80, 86, 48) - 3.5
    a1 = sd_triangle(x, y, (80, 40), (92, 48), (80, 56)) - 1.5
    a2 = sd_triangle(x, y, (80, 72), (92, 80), (80, 88)) - 1.5
    return min(s1, s2, a1, a2)


def sym_playlist(x, y):
    l1 = sd_rounded_box(x, y, 64, 46, 24, 3.8, 3.5)
    l2 = sd_rounded_box(x, y, 64, 64, 24, 3.8, 3.5)
    l3 = sd_rounded_box(x, y, 56, 82, 16, 3.8, 3.5)
    c = sd_circle(x, y, 84, 80, 6.5)
    return min(l1, l2, l3, c)


def sym_track(x, y):
    c1 = sd_circle(x, y, 52, 78, 9.5)
    stem = sd_rounded_box(x, y, 59.5, 58, 3.2, 20, 2.5)
    flag = sd_rounded_box(x, y, 69, 43, 11, 4.5, 3.0)
    return min(c1, stem, flag)


def sym_volume(x, y):
    box = sd_rounded_box(x, y, 45, 64, 7, 9, 2.5)
    cone = sd_triangle(x, y, (44, 64), (66, 44), (66, 84)) - 2.0
    arc1 = max(abs(sd_circle(x, y, 64, 64, 16)) - 2.8, 66 - x)
    arc2 = max(abs(sd_circle(x, y, 64, 64, 26)) - 2.8, 68 - x)
    return min(box, cone, arc1, arc2)


def generate_all(output_dirs):
    icons = {
        "app.png": ((16, 225, 125), (10, 165, 255), sym_app),
        "playing.png": ((34, 235, 130), (16, 185, 129), sym_app),
        "play.png": ((56, 189, 248), (99, 102, 241), sym_play),
        "pause.png": ((251, 191, 36), (245, 158, 11), sym_pause),
        "next.png": ((168, 85, 247), (236, 72, 153), sym_next),
        "prev.png": ((168, 85, 247), (99, 102, 241), sym_prev),
        "shuffle.png": ((45, 212, 191), (14, 165, 233), sym_shuffle),
        "playlist.png": ((244, 114, 182), (168, 85, 247), sym_playlist),
        "track.png": ((129, 140, 248), (192, 132, 252), sym_track),
        "volume.png": ((52, 211, 153), (59, 130, 246), sym_volume),
        "heart.png": ((244, 63, 94), (225, 29, 72), sd_heart),         # Vibrant Rose / Red
        "download.png": ((56, 189, 248), (14, 165, 233), sd_download), # Sky Blue
    }
    for out_dir in output_dirs:
        os.makedirs(out_dir, exist_ok=True)
        for filename, (c1, c2, fn) in icons.items():
            render_icon(os.path.join(out_dir, filename), c1, c2, fn)


if __name__ == "__main__":
    appdata = os.environ.get("APPDATA", "")
    dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"),
        os.path.join(appdata, r"FlowLauncher\Plugins\FlowMusic-1.0.0\assets"),
    ]
    generate_all(dirs)
    print("Generated all icons successfully!")
