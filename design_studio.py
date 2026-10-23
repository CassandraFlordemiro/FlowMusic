# -*- coding: utf-8 -*-
"""
Design Studio V2 - Apple Sonoma & MyDockFinder Native Quality.
Features:
- Cached Dual-Stage Gaussian Shadow (0ms overhead)
- 3x Super-Sample Anti-Aliasing (SSAA) for subpixel-smooth squircle borders
- High-definition Apple SF Symbols media controls
- Authentic glassmorphism: specular top highlight line, smoked obsidian tint
- Elimination of all harsh neon outlines & low-res elements
"""

import math
import os
import time
from PIL import Image, ImageDraw, ImageFilter, ImageFont


class RetinaHUDDesigner:
    def __init__(self, width: int = 430, height: int = 86, scale: int = 3):
        self.w = width
        self.h = height
        self.scale = scale
        self.pad_x = 14
        self.pad_y = 10
        self.card_w = width - self.pad_x * 2
        self.card_h = height - self.pad_y * 2
        self.radius = 24

        # Precompute cached dual-stage shadow
        self._cached_shadow = self._build_shadow_layer()

    def _build_shadow_layer(self) -> Image.Image:
        w, h = self.w, self.h
        px, py = self.pad_x, self.pad_y
        cw, ch = self.card_w, self.card_h
        r = self.radius

        base = Image.new("RGBA", (w, h), (0, 0, 0, 0))

        # Ambient diffuse shadow
        s1 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d1 = ImageDraw.Draw(s1)
        d1.rounded_rectangle([px, py + 4, px + cw, py + ch + 4], radius=r, fill=(0, 0, 0, 115))
        s1 = s1.filter(ImageFilter.GaussianBlur(9))

        # Contact tight shadow
        s2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(s2)
        d2.rounded_rectangle([px, py + 2, px + cw, py + ch + 2], radius=r, fill=(0, 0, 0, 140))
        s2 = s2.filter(ImageFilter.GaussianBlur(3))

        base = Image.alpha_composite(base, s1)
        base = Image.alpha_composite(base, s2)
        return base

    def render(
        self,
        title: str = "41 - HEAVEN",
        artist: str = "The Best of Pro Evolution",
        status_text: str = "CONTINUANDO",
        time_str: str = "02:51 / 03:39",
        progress: float = 0.74,
        cover_image: Image.Image = None,
        is_paused: bool = False,
        is_fav: bool = False,
        is_hovered: bool = False,
    ) -> Image.Image:
        scale = self.scale
        W = self.w * scale
        H = self.h * scale

        # 3x Supersampled Hi-DPI Canvas
        hi_canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(hi_canvas)

        px = self.pad_x * scale
        py = self.pad_y * scale
        cw = self.card_w * scale
        ch = self.card_h * scale
        r = self.radius * scale

        # 1. Smoked Glass Card Body (Obsidian Dark with subtle blue-gray tint like MyDockFinder)
        # Unhovered: (14, 17, 24, 230), Hovered: (20, 24, 34, 242)
        bg_col = (14, 17, 24, 232) if not is_hovered else (20, 24, 34, 242)
        draw.rounded_rectangle(
            [px, py, px + cw, py + ch],
            radius=r,
            fill=bg_col,
        )

        # 2. Outer 1px frosted glass perimeter outline (Semi-transparent white)
        draw.rounded_rectangle(
            [px, py, px + cw, py + ch],
            radius=r,
            outline=(255, 255, 255, 42),
            width=scale,
        )

        # 3. Top specular light highlight (simulates macOS / MyDockFinder top edge bevel)
        draw.line(
            [px + r, py + int(1 * scale), px + cw - r, py + int(1 * scale)],
            fill=(255, 255, 255, 95),
            width=int(1.2 * scale),
        )

        # 4. Album Cover Art Tile (Continuous Squircle with inner glass bevel, zero harsh neon!)
        cov_x = px + int(11 * scale)
        cov_y = py + int(10 * scale)
        cov_size = int(46 * scale)
        cov_r = int(12 * scale)

        if cover_image:
            cv = cover_image.convert("RGBA").resize((cov_size, cov_size), Image.Resampling.LANCZOS)
            # Squircle mask
            mask = Image.new("L", (cov_size, cov_size), 0)
            md = ImageDraw.Draw(mask)
            md.rounded_rectangle([0, 0, cov_size - 1, cov_size - 1], radius=cov_r, fill=255)
            cv.putalpha(mask)

            # Delicate inner glass border
            inner_border = Image.new("RGBA", (cov_size, cov_size), (0, 0, 0, 0))
            ib_draw = ImageDraw.Draw(inner_border)
            ib_draw.rounded_rectangle(
                [0, 0, cov_size - 1, cov_size - 1],
                radius=cov_r,
                outline=(255, 255, 255, 50),
                width=scale,
            )
            cv_final = Image.alpha_composite(cv, inner_border)
            hi_canvas.paste(cv_final, (cov_x, cov_y), cv_final)
        else:
            draw.rounded_rectangle(
                [cov_x, cov_y, cov_x + cov_size, cov_y + cov_size],
                radius=cov_r,
                fill=(28, 33, 46, 255),
                outline=(255, 255, 255, 40),
                width=scale,
            )

        # 5. Typography (Windows 11 Segoe UI Variable / Segoe UI Bold)
        text_x = cov_x + cov_size + int(13 * scale)

        try:
            font_status = ImageFont.truetype(r"C:\Windows\Fonts\SegUIVar.ttf", int(9.5 * scale))
            font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", int(14 * scale))
            font_time = ImageFont.truetype(r"C:\Windows\Fonts\SegUIVar.ttf", int(10.5 * scale))
        except Exception:
            font_status = font_title = font_time = ImageFont.load_default()

        # Header status dot + text
        dot_r = int(3 * scale)
        dot_y = cov_y + int(5 * scale)
        dot_col = (251, 191, 36) if is_paused else (48, 209, 88)  # Amber when paused, Apple Green when playing

        # Sub-glow halo around status dot
        draw.ellipse(
            [text_x - scale, dot_y - scale, text_x + dot_r * 2 + scale, dot_y + dot_r * 2 + scale],
            fill=dot_col + (75,),
        )
        draw.ellipse(
            [text_x, dot_y, text_x + dot_r * 2, dot_y + dot_r * 2],
            fill=dot_col + (255,),
        )

        header_str = f"{status_text} • {artist}".upper()
        if len(header_str) > 36:
            header_str = header_str[:34] + "…"
        draw.text(
            (text_x + dot_r * 2 + int(6 * scale), cov_y + int(2 * scale)),
            header_str,
            fill=(155, 172, 195, 255),
            font=font_status,
        )

        right_x = px + cw - int(14 * scale)

        # 6. Right Side: Controls Capsule on Hover OR Time Display
        if is_hovered:
            pill_w = int(124 * scale)
            pill_h = int(27 * scale)
            pill_x = right_x - pill_w
            pill_y = cov_y - int(1 * scale)

            # Frosted glass capsule background
            draw.rounded_rectangle(
                [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                radius=pill_h // 2,
                fill=(255, 255, 255, 18),
                outline=(255, 255, 255, 45),
                width=scale,
            )

            # Apple SF Symbols Style Vector Buttons
            cy = pill_y + pill_h // 2
            icon_col = (215, 226, 238, 255)

            # Prev button
            bx = pill_x + int(18 * scale)
            draw.polygon([(bx + int(6*scale), cy - int(6*scale)), (bx - int(2*scale), cy), (bx + int(6*scale), cy + int(6*scale))], fill=icon_col)
            draw.line([(bx - int(4*scale), cy - int(6*scale)), (bx - int(4*scale), cy + int(6*scale))], fill=icon_col, width=int(1.8*scale))

            # Play / Pause button
            bx += int(28 * scale)
            if is_paused:
                draw.polygon([(bx - int(3*scale), cy - int(7*scale)), (bx + int(7*scale), cy), (bx - int(3*scale), cy + int(7*scale))], fill=(255, 255, 255, 255))
            else:
                bar_hw = int(1.6 * scale)
                draw.rounded_rectangle([bx - int(4*scale), cy - int(6*scale), bx - int(4*scale) + bar_hw * 2, cy + int(6*scale)], radius=scale, fill=(255, 255, 255, 255))
                draw.rounded_rectangle([bx + int(2*scale), cy - int(6*scale), bx + int(2*scale) + bar_hw * 2, cy + int(6*scale)], radius=scale, fill=(255, 255, 255, 255))

            # Next button
            bx += int(28 * scale)
            draw.polygon([(bx - int(6*scale), cy - int(6*scale)), (bx + int(2*scale), cy), (bx - int(6*scale), cy + int(6*scale))], fill=icon_col)
            draw.line([(bx + int(4*scale), cy - int(6*scale)), (bx + int(4*scale), cy + int(6*scale))], fill=icon_col, width=int(1.8*scale))

            # Heart button
            bx += int(27 * scale)
            heart_col = (255, 59, 92, 255) if is_fav else (175, 190, 208, 220)
            # Draw vector heart
            h_pts = []
            s_heart = int(13 * scale)
            for deg in range(0, 360, 6):
                t = math.radians(deg)
                hx = 16 * (math.sin(t) ** 3)
                hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                px_h = bx + hx * (s_heart / 40)
                py_h = cy + (hy + 1.2) * (s_heart / 40)
                h_pts.append((px_h, py_h))
            if is_fav:
                draw.polygon(h_pts, fill=heart_col)
            else:
                draw.polygon(h_pts, outline=heart_col, width=int(1.5 * scale))

        else:
            # Time string
            draw.text(
                (right_x, cov_y + int(3 * scale)),
                time_str,
                fill=(135, 150, 170, 230),
                font=font_time,
                anchor="ra",
            )

        # Track Title
        disp_title = title
        if len(disp_title) > 34:
            disp_title = disp_title[:32] + "…"
        draw.text(
            (text_x, cov_y + int(19 * scale)),
            disp_title,
            fill=(255, 255, 255, 255),
            font=font_title,
        )

        # 7. Progress Bar: Apple Delicate 3.5px Glass Pill
        bar_y = cov_y + cov_size - int(4 * scale)
        bar_x1 = text_x
        bar_x2 = right_x
        bar_h = int(3.5 * scale)

        # Track background
        draw.rounded_rectangle(
            [bar_x1, bar_y, bar_x2, bar_y + bar_h],
            radius=bar_h // 2,
            fill=(255, 255, 255, 24),
        )

        # Active Fill (Apple White/Pearl with subtle glow)
        prog = max(0.0, min(1.0, progress))
        if prog > 0.005:
            fill_w = max(bar_h, int((bar_x2 - bar_x1) * prog))
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=bar_h // 2,
                fill=(255, 255, 255, 230),
            )

            # Apple Scrubber Knob
            thumb_x = bar_x1 + fill_w
            thumb_r = int(3.5 * scale)
            draw.ellipse(
                [thumb_x - thumb_r, bar_y + bar_h // 2 - thumb_r, thumb_x + thumb_r, bar_y + bar_h // 2 + thumb_r],
                fill=(255, 255, 255, 255),
                outline=(0, 0, 0, 60),
                width=scale,
            )

        # Downsample 3x with Lanczos for subpixel anti-aliasing
        rendered_card = hi_canvas.resize((self.w, self.h), Image.Resampling.LANCZOS)

        # Final composite: Cached drop shadow + 3x Lanczos card
        final_img = Image.alpha_composite(self._cached_shadow, rendered_card)
        return final_img


if __name__ == "__main__":
    designer = RetinaHUDDesigner()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Find cover from cache
    cov_path = os.path.join(base_dir, "cache", "covers", "00a442ea8f14ffd9_128.png")
    cov_img = Image.open(cov_path) if os.path.exists(cov_path) else None

    # Benchmark & Generate
    t0 = time.time()
    normal_img = designer.render(cover_image=cov_img, is_hovered=False)
    t1 = time.time()
    print(f"Normal render time: {(t1-t0)*1000:.2f}ms")

    hover_img = designer.render(cover_image=cov_img, is_hovered=True, is_fav=True)
    normal_img.save(os.path.join(base_dir, "test_v2_normal.png"))
    hover_img.save(os.path.join(base_dir, "test_v2_hover.png"))
    print("Saved test_v2_normal.png and test_v2_hover.png")

