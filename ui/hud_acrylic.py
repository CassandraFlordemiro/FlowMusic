# -*- coding: utf-8 -*-
"""
FlowMusic 360 - True 32-Bit Per-Pixel Alpha Acrylic HUD Window (V2.5 Accessible).
Features:
- Expanded High-Readability Layout (540x172)
- Dedicated Bottom Media Controls Deck (Shuffle, Prev, -10s, Play/Pause, +10s, Next, Fav)
- Interactive Hover Highlights & Quick Close Button (✕)
- 3x Super-Sample Anti-Aliasing (SSAA) for Subpixel Smoothness
- Dual-Stage Glassmorphic Drop Shadow
"""

import ctypes
from ctypes import wintypes
import math
import os
import re
import sys
import time
from PIL import Image, ImageDraw, ImageFilter, ImageFont

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000

WS_POPUP = 0x80000000
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
GWL_EXSTYLE = -20

WM_LBUTTONDOWN = 0x0201
WM_MOUSEMOVE = 0x0200
WM_MOUSEWHEEL = 0x020A
WM_DESTROY = 0x0002
WM_HOTKEY = 0x0312


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HICON),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]

user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND,
    wintypes.HDC,
    ctypes.POINTER(POINT),
    ctypes.POINTER(SIZE),
    wintypes.HDC,
    ctypes.POINTER(POINT),
    wintypes.COLORREF,
    ctypes.POINTER(BLENDFUNCTION),
    wintypes.DWORD,
]

user32.GetWindowLongW.restype = wintypes.LONG
user32.SetWindowLongW.restype = wintypes.LONG

user32.DefWindowProcW.restype = ctypes.c_longlong
user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    ctypes.c_uint,
    wintypes.WPARAM,
    wintypes.LPARAM,
]


def pil_to_premultiplied_bgra(pil_img: Image.Image) -> bytes:
    """
    Ultra-fast C-level premultiplied BGRA conversion using Pillow's native raw BGRa encoder.
    ~10x faster than pure Python loops with zero CPU overhead.
    """
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    return pil_img.tobytes("raw", "BGRa")


def clean_header_text(header: str) -> str:
    header = header.replace("•", " · ").replace("  ", " ")
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", header)
    cleaned = re.sub(r"[\u2190-\u21ff\u2300-\u23ff\u25a0-\u25ff\u2600-\u27ff]", "", cleaned)
    cleaned = "".join(c for c in cleaned if c.isprintable())
    return cleaned.strip()


class AcrylicHUDWindow:
    def __init__(self, on_action_cb=None, theme: str = "opal"):
        self.on_action = on_action_cb
        self.theme = theme
        self.w = 540
        self.h = 172
        self.scale = 2  # 2x Super-Sample Anti-Aliasing (SSAA) for Retina clarity with low CPU
        self.x = 0
        self.y = 36
        self.alpha = 0
        self.target_alpha = 0
        self.hide_at = 0.0
        self.is_hovered = False
        self.hover_btn = ""
        self.click_through = True

        self.pad_x = 16
        self.pad_y = 14
        self.card_w = self.w - self.pad_x * 2
        self.card_h = self.h - self.pad_y * 2
        self.radius = 26

        # Load and pre-cache custom icons for instant 0ms blitting
        self.icons = {}
        self._load_custom_icons()

        # Cached dual-stage shadow
        self._cached_shadow = self._build_shadow_layer()

        # Pre-cache system typography to avoid disk reads on render
        try:
            self.font_status = ImageFont.truetype(r"C:\Windows\Fonts\SegUIVar.ttf", int(10.5 * self.scale))
            self.font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", int(16 * self.scale))
            self.font_sub = ImageFont.truetype(r"C:\Windows\Fonts\SegUIVar.ttf", int(12 * self.scale))
            self.font_time = ImageFont.truetype(r"C:\Windows\Fonts\SegUIVar.ttf", int(10.5 * self.scale))
        except Exception:
            self.font_status = self.font_title = self.font_sub = self.font_time = ImageFont.load_default()

        self.cover_img = None
        self._last_raw_cover = None
        self._prepared_cover = None
        self.header_text = "FLOWMUSIC 360"
        self.title_text = "Pronto para tocar"
        self.artist_text = ""
        self.cur_time = "00:00"
        self.total_time = "00:00"
        self.progress = 0.0
        self.accent_rgb = (16, 225, 125)
        self.is_paused = False
        self.is_fav = False
        self.is_shuffle = False

        self._create_win32_window()
        self._init_gdi_surface()

    def _load_custom_icons(self):
        scale = self.scale
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_dir = os.path.join(base_dir, "assets", "novos_icones")
        if not os.path.isdir(icon_dir):
            icon_dir = os.path.join(base_dir, "..", "assets", "novos_icones")
        if not os.path.isdir(icon_dir):
            return

        # Target visual sizes (calibrated in pts * scale)
        icon_targets = {
            "close": ("close.png", int(13 * scale)),
            "music": ("music.png", int(40 * scale)),
            "shuffle": ("shuffle.png", int(22 * scale)),
            "prev": ("previous.png", int(22 * scale)),
            "rewind": ("ten_seconds_return.png", int(22 * scale)),
            "play": ("play.png", int(28 * scale)),
            "stop": ("stop.png", int(28 * scale)),
            "forward": ("ten_seconds.png", int(22 * scale)),
            "next": ("next.png", int(22 * scale)),
            "fav": ("love_song.png", int(22 * scale)),
        }

        for key, (filename, target_sz) in icon_targets.items():
            p = os.path.join(icon_dir, filename)
            if os.path.exists(p):
                try:
                    with Image.open(p) as img:
                        rgba = img.convert("RGBA")
                        # Crop to visible bbox to remove uneven transparent padding
                        bbox = rgba.getbbox()
                        if bbox:
                            rgba = rgba.crop(bbox)
                        iw, ih = rgba.size
                        ratio = min(target_sz / iw, target_sz / ih)
                        nw, nh = max(1, int(iw * ratio)), max(1, int(ih * ratio))
                        self.icons[key] = rgba.resize((nw, nh), Image.Resampling.LANCZOS)
                except Exception:
                    pass

    def _build_shadow_layer(self) -> Image.Image:
        w, h = self.w, self.h
        px, py = self.pad_x, self.pad_y
        cw, ch = self.card_w, self.card_h
        r = self.radius

        base = Image.new("RGBA", (w, h), (0, 0, 0, 0))

        if self.theme == "opal":
            s_alpha = 32
            s_blur = 14
        else:
            s_alpha = 75
            s_blur = 16

        # Wide, soft, airy ambient drop shadow with zero dark contact lines
        s1 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d1 = ImageDraw.Draw(s1)
        d1.rounded_rectangle([px, py + 4, px + cw, py + ch + 4], radius=r, fill=(0, 0, 0, s_alpha))
        s1 = s1.filter(ImageFilter.GaussianBlur(s_blur))
        base = Image.alpha_composite(base, s1)
        return base

    def toggle_theme(self) -> str:
        self.theme = "dark" if self.theme == "opal" else "opal"
        self._cached_shadow = self._build_shadow_layer()
        self.update_content()
        return self.theme

    def _create_win32_window(self):
        self.class_name = f"FlowMusicAcrylic_{id(self)}"
        self._wnd_proc_ref = WNDPROC(self._wnd_proc)
        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wnd_proc_ref
        wc.lpszClassName = self.class_name
        wc.hInstance = hinst
        wc.hCursor = user32.LoadCursorW(None, 32512)
        user32.RegisterClassExW(ctypes.byref(wc))

        ex_style = (
            WS_EX_LAYERED
            | WS_EX_TOOLWINDOW
            | WS_EX_TOPMOST
            | WS_EX_NOACTIVATE
            | WS_EX_TRANSPARENT
        )
        self.hwnd = user32.CreateWindowExW(
            ex_style,
            self.class_name,
            "FlowMusicHUD",
            WS_POPUP,
            0,
            0,
            self.w,
            self.h,
            None,
            None,
            hinst,
            None,
        )

        self._position_hud()

    def _init_gdi_surface(self):
        """Allocate persistent Win32 GDI resources to eliminate per-frame allocations."""
        self.hdc_screen = user32.GetDC(None)
        self.hdc_mem = gdi32.CreateCompatibleDC(self.hdc_screen)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.w
        bmi.bmiHeader.biHeight = -self.h  # top-down DIB
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        self.p_bits = ctypes.c_void_p()
        self.hbmp = gdi32.CreateDIBSection(
            self.hdc_screen,
            ctypes.byref(bmi),
            0,
            ctypes.byref(self.p_bits),
            None,
            0,
        )
        self.hbmp_old = gdi32.SelectObject(self.hdc_mem, self.hbmp)

        self.pt_src = POINT(0, 0)
        self.pt_dst = POINT(self.x, self.y)
        self.sz = SIZE(self.w, self.h)

    def __del__(self):
        try:
            self.unregister_hotkeys()
            if hasattr(self, "hdc_mem") and self.hdc_mem:
                if hasattr(self, "hbmp_old") and self.hbmp_old:
                    gdi32.SelectObject(self.hdc_mem, self.hbmp_old)
                if hasattr(self, "hbmp") and self.hbmp:
                    gdi32.DeleteObject(self.hbmp)
                gdi32.DeleteDC(self.hdc_mem)
            if hasattr(self, "hdc_screen") and self.hdc_screen:
                user32.ReleaseDC(None, self.hdc_screen)
        except Exception:
            pass

    def register_hotkeys(self, hotkeys: dict):
        """
        Registers system-wide hotkeys directly on this window handle.
        Windows guarantees instant routing to _wnd_proc on the main thread with 0 latency.
        hotkeys: {hk_id: (mods, vk)}
        """
        self._registered_hotkeys = {}
        for hk_id, (mods, vk) in hotkeys.items():
            try:
                user32.UnregisterHotKey(self.hwnd, hk_id)
            except Exception:
                pass
            # Try with MOD_NOREPEAT first (0x4000)
            res = user32.RegisterHotKey(self.hwnd, hk_id, mods | 0x4000, vk)
            if not res:
                # Fallback without MOD_NOREPEAT
                res = user32.RegisterHotKey(self.hwnd, hk_id, mods, vk)
            if res:
                self._registered_hotkeys[hk_id] = (mods, vk)

    def unregister_hotkeys(self):
        if hasattr(self, "_registered_hotkeys"):
            for hk_id in list(self._registered_hotkeys.keys()):
                try:
                    user32.UnregisterHotKey(self.hwnd, hk_id)
                except Exception:
                    pass
            self._registered_hotkeys.clear()

    def _position_hud(self, pos: str = "top_center"):
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        if pos == "top_right":
            self.x = sw - self.w - 20
            self.y = 38
        elif pos == "bottom_right":
            self.x = sw - self.w - 20
            self.y = sh - self.h - 90
        else:
            self.x = (sw - self.w) // 2
            self.y = 34

        if hasattr(self, "pt_dst"):
            self.pt_dst.x = self.x
            self.pt_dst.y = self.y

    def _set_click_through(self, enabled: bool):
        if self.click_through == enabled:
            return
        self.click_through = enabled
        ex = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        if enabled:
            new_ex = ex | WS_EX_TRANSPARENT
        else:
            new_ex = ex & ~WS_EX_TRANSPARENT
        user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, new_ex)

    def _wnd_proc(self, hwnd, msg, wp, lp):
        if msg == WM_HOTKEY:
            if self.on_action:
                self.on_action("hotkey", int(wp))
            return 0
        elif msg == WM_LBUTTONDOWN:
            lx = lp & 0xFFFF
            ly = (lp >> 16) & 0xFFFF
            self._handle_click(lx, ly)
            return 0
        elif msg == WM_MOUSEMOVE:
            lx = lp & 0xFFFF
            ly = (lp >> 16) & 0xFFFF
            self._handle_mousemove(lx, ly)
            return 0
        elif msg == WM_MOUSEWHEEL:
            raw_delta = (wp >> 16) & 0xFFFF
            wheel_delta = ctypes.c_short(raw_delta).value
            vol_step = 5 if wheel_delta > 0 else -5
            if self.on_action:
                self.on_action("vol_delta", vol_step)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def _get_button_at(self, lx: int, ly: int) -> str:
        px = self.pad_x
        cw = self.card_w
        cov_y = self.pad_y + 14

        # Close button in top-right
        close_x = px + cw - 16
        close_y = cov_y + 8
        if abs(lx - close_x) <= 15 and abs(ly - close_y) <= 15:
            return "close"

        # Theme toggle button (Sun / Moon) beside close button
        theme_btn_x = close_x - 26
        theme_btn_y = close_y
        if abs(lx - theme_btn_x) <= 13 and abs(ly - theme_btn_y) <= 13:
            return "theme_toggle"

        # Bottom Deck Buttons (calibrated 48px center intervals)
        bar_x1 = px + 16
        bar_x2 = px + cw - 16
        deck_y = self.pad_y + self.card_h - 24
        center_x = (bar_x1 + bar_x2) // 2

        if abs(ly - deck_y) <= 22:
            if abs(lx - (bar_x1 + 24)) <= 20:
                return "shuffle"
            elif abs(lx - (center_x - 96)) <= 20:
                return "prev"
            elif abs(lx - (center_x - 48)) <= 20:
                return "rewind"
            elif abs(lx - center_x) <= 22:
                return "play"
            elif abs(lx - (center_x + 48)) <= 20:
                return "forward"
            elif abs(lx - (center_x + 96)) <= 20:
                return "next"
            elif abs(lx - (bar_x2 - 24)) <= 20:
                return "fav"

        return ""

    def _handle_mousemove(self, lx: int, ly: int):
        btn = self._get_button_at(lx, ly)
        if btn != self.hover_btn:
            self.hover_btn = btn
            self.update_surface()

    def _handle_click(self, lx: int, ly: int):
        btn = self._get_button_at(lx, ly)
        if btn == "close":
            self.target_alpha = 0
            return
        elif btn == "theme_toggle":
            new_theme = self.toggle_theme()
            if self.on_action:
                self.on_action("toggle_theme", new_theme)
            return
        elif btn == "shuffle":
            if self.on_action:
                self.on_action("shuffle")
            return
        elif btn == "prev":
            if self.on_action:
                self.on_action("prev")
            return
        elif btn == "rewind":
            if self.on_action:
                self.on_action("seek_delta", -10000)
            return
        elif btn == "play":
            if self.on_action:
                self.on_action("toggle")
            return
        elif btn == "forward":
            if self.on_action:
                self.on_action("seek_delta", 10000)
            return
        elif btn == "next":
            if self.on_action:
                self.on_action("next")
            return
        elif btn == "fav":
            if self.on_action:
                self.on_action("toggle_fav")
            return

        # Progress bar click/seek
        cov_y = self.pad_y + 14
        cov_size = 60
        bar_x1 = self.pad_x + 16
        bar_x2 = self.pad_x + self.card_w - 16
        bar_y = cov_y + cov_size + 12

        if bar_y - 8 <= ly <= bar_y + 14 and bar_x1 <= lx <= bar_x2:
            frac = (lx - bar_x1) / float(bar_x2 - bar_x1)
            if self.on_action:
                self.on_action("seek_fraction", frac)
            return

        # Album cover click toggles play/pause
        cov_x = self.pad_x + 14
        if cov_x <= lx <= cov_x + cov_size and cov_y <= ly <= cov_y + cov_size:
            if self.on_action:
                self.on_action("toggle")
            return

    def render_image(self) -> Image.Image:
        scale = self.scale
        W = self.w * scale
        H = self.h * scale

        hi_canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(hi_canvas)

        px = self.pad_x * scale
        py = self.pad_y * scale
        cw = self.card_w * scale
        ch = self.card_h * scale
        r = self.radius * scale

        is_opal = (self.theme == "opal")

        if is_opal:
            # Opal Frosted Crystal Glass - Clean, Airy, ZERO Dark Borders
            bg_col = (248, 250, 253, 248)
            border_col = (255, 255, 255, 210)
            inner_border = None
            rim_line = (255, 255, 255, 255)
            title_col = (18, 24, 38, 255)
            sub_col = (100, 115, 135, 255)
            status_col = (125, 140, 160, 255)
            bar_bg = (225, 230, 238, 255)  # Clean pastel slider track
            bar_fill = (253, 71, 133, 245)  # Hot coral pink
        else:
            # Obsidian Smoked Glass
            bg_col = (13, 16, 23, 238)
            border_col = (255, 255, 255, 42)
            inner_border = None
            rim_line = (255, 255, 255, 100)
            title_col = (255, 255, 255, 255)
            sub_col = (140, 155, 175, 255)
            status_col = (150, 168, 190, 255)
            bar_bg = (255, 255, 255, 26)
            bar_fill = (255, 255, 255, 235)

        # 1. Glass Card Body
        draw.rounded_rectangle([px, py, px + cw, py + ch], radius=r, fill=bg_col)

        # 2. Outer frosted glass perimeter outline (Pure semi-transparent white)
        draw.rounded_rectangle([px, py, px + cw, py + ch], radius=r, outline=border_col, width=scale)

        # 3. Top specular light highlight
        draw.line([px + r, py + scale, px + cw - r, py + scale], fill=rim_line, width=int(1.2 * scale))

        # -------------------------------------------------------------
        # TOP ROW: Album Cover + Track Metadata + Close Button
        # -------------------------------------------------------------
        cov_size = int(60 * scale)
        cov_x = px + int(14 * scale)
        cov_y = py + int(14 * scale)
        cov_r = int(14 * scale)

        if self.cover_img is not getattr(self, "_last_raw_cover", None):
            self._last_raw_cover = self.cover_img
            if self.cover_img:
                cv = self.cover_img.convert("RGBA").resize((cov_size, cov_size), Image.Resampling.BICUBIC)
                mask = Image.new("L", (cov_size, cov_size), 0)
                md = ImageDraw.Draw(mask)
                md.rounded_rectangle([0, 0, cov_size - 1, cov_size - 1], radius=cov_r, fill=255)
                cv.putalpha(mask)

                inner_border_cov = Image.new("RGBA", (cov_size, cov_size), (0, 0, 0, 0))
                ib_draw = ImageDraw.Draw(inner_border_cov)
                ib_draw.rounded_rectangle([0, 0, cov_size - 1, cov_size - 1], radius=cov_r, outline=(255, 255, 255, 120 if is_opal else 55), width=scale)
                self._prepared_cover = Image.alpha_composite(cv, inner_border_cov)
            else:
                self._prepared_cover = None

        if self._prepared_cover:
            hi_canvas.paste(self._prepared_cover, (cov_x, cov_y), self._prepared_cover)
        else:
            # Fallback cover with music icon
            fallback_bg = (235, 240, 248, 255) if is_opal else (28, 33, 46, 255)
            draw.rounded_rectangle([cov_x, cov_y, cov_x + cov_size, cov_y + cov_size], radius=cov_r, fill=fallback_bg, outline=(255, 255, 255, 50), width=scale)
            if "music" in self.icons:
                m_ico = self.icons["music"]
                hi_canvas.paste(m_ico, (cov_x + (cov_size - m_ico.width) // 2, cov_y + (cov_size - m_ico.height) // 2), m_ico)

        text_x = cov_x + cov_size + int(14 * scale)

        font_status = self.font_status
        font_title = self.font_title
        font_sub = self.font_sub
        font_time = self.font_time

        # Status Dot (Amber paused / Apple Green playing)
        dot_r = int(3.5 * scale)
        dot_y = cov_y + int(4 * scale)
        dot_col = (251, 191, 36) if self.is_paused else (48, 209, 88)

        draw.ellipse([text_x - scale, dot_y - scale, text_x + dot_r * 2 + scale, dot_y + dot_r * 2 + scale], fill=dot_col + (70,))
        draw.ellipse([text_x, dot_y, text_x + dot_r * 2, dot_y + dot_r * 2], fill=dot_col + (255,))

        head_str = clean_header_text(self.header_text).upper()
        if len(head_str) > 36:
            head_str = head_str[:34] + "…"
        draw.text((text_x + dot_r * 2 + int(7 * scale), cov_y + int(1 * scale)), head_str, fill=status_col, font=font_status)

        # Track Title
        disp_title = self.title_text
        if len(disp_title) > 30:
            disp_title = disp_title[:28] + "…"
        draw.text((text_x, cov_y + int(17 * scale)), disp_title, fill=title_col, font=font_title)

        # Artist Info
        if self.artist_text:
            disp_art = self.artist_text
            if len(disp_art) > 35:
                disp_art = disp_art[:33] + "…"
            draw.text((text_x, cov_y + int(40 * scale)), disp_art, fill=sub_col, font=font_sub)

        # Close button in top-right corner (delicate & aligned with status line)
        close_x = px + cw - int(16 * scale)
        close_y = cov_y + int(8 * scale)
        is_close_hover = (self.hover_btn == "close")
        if "close" in self.icons:
            if is_close_hover:
                draw.ellipse([close_x - int(10 * scale), close_y - int(10 * scale), close_x + int(10 * scale), close_y + int(10 * scale)], fill=(255, 255, 255, 180) if is_opal else (255, 255, 255, 25))
            cl_ico = self.icons["close"]
            hi_canvas.paste(cl_ico, (close_x - cl_ico.width // 2, close_y - cl_ico.height // 2), cl_ico)
        else:
            close_col = (255, 255, 255, 240) if is_close_hover else (140, 155, 175, 180)
            draw.line([close_x - int(5 * scale), close_y - int(5 * scale), close_x + int(5 * scale), close_y + int(5 * scale)], fill=close_col, width=int(1.8 * scale))
            draw.line([close_x + int(5 * scale), close_y - int(5 * scale), close_x - int(5 * scale), close_y + int(5 * scale)], fill=close_col, width=int(1.8 * scale))

        # Theme toggle button (Sun in dark mode, Moon in light mode)
        theme_btn_x = close_x - int(26 * scale)
        theme_btn_y = close_y
        is_theme_hover = (self.hover_btn == "theme_toggle")
        if is_theme_hover:
            draw.ellipse([theme_btn_x - int(10 * scale), theme_btn_y - int(10 * scale), theme_btn_x + int(10 * scale), theme_btn_y + int(10 * scale)], fill=(255, 255, 255, 180) if is_opal else (255, 255, 255, 30))

        if is_opal:
            # Moon icon (to switch to dark)
            t_sz = int(13 * scale)
            moon_canvas = Image.new("RGBA", (t_sz * 2, t_sz * 2), (0, 0, 0, 0))
            md = ImageDraw.Draw(moon_canvas)
            mc = t_sz
            mr = int(t_sz * 0.48)
            md.ellipse([mc - mr, mc - mr, mc + mr, mc + mr], fill=(115, 130, 150, 240))
            cut_r = int(mr * 0.88)
            md.ellipse([mc - cut_r + int(mr * 0.45), mc - cut_r - int(mr * 0.22), mc + cut_r + int(mr * 0.45), mc + cut_r - int(mr * 0.22)], fill=(0, 0, 0, 0))
            hi_canvas.paste(moon_canvas, (theme_btn_x - t_sz, theme_btn_y - t_sz), moon_canvas)
        else:
            # Radiant golden Sun icon (to switch to light)
            t_sz = int(14 * scale)
            sun_canvas = Image.new("RGBA", (t_sz * 2, t_sz * 2), (0, 0, 0, 0))
            sd = ImageDraw.Draw(sun_canvas)
            sc = t_sz
            cr = int(t_sz * 0.26)
            sd.ellipse([sc - cr, sc - cr, sc + cr, sc + cr], fill=(255, 210, 60, 255))
            ray_len = int(t_sz * 0.22)
            for i in range(8):
                ang = i * (math.pi / 4)
                x1 = sc + int((cr + int(1.5 * scale)) * math.cos(ang))
                y1 = sc + int((cr + int(1.5 * scale)) * math.sin(ang))
                x2 = sc + int((cr + int(1.5 * scale) + ray_len) * math.cos(ang))
                y2 = sc + int((cr + int(1.5 * scale) + ray_len) * math.sin(ang))
                sd.line([x1, y1, x2, y2], fill=(255, 210, 60, 240), width=max(1, int(1.3 * scale)))
            hi_canvas.paste(sun_canvas, (theme_btn_x - t_sz, theme_btn_y - t_sz), sun_canvas)

        # -------------------------------------------------------------
        # MIDDLE ROW: Progress Bar + Time Stamps
        # -------------------------------------------------------------
        bar_x1 = px + int(16 * scale)
        bar_x2 = px + cw - int(16 * scale)
        bar_y = cov_y + cov_size + int(12 * scale)
        bar_h = int(4 * scale)

        time_text = f"{self.cur_time} / {self.total_time}"
        draw.text((bar_x2, bar_y - int(14 * scale)), time_text, fill=sub_col, font=font_time, anchor="ra")

        # Track background - clean pastel, NO dark slot
        draw.rounded_rectangle([bar_x1, bar_y, bar_x2, bar_y + bar_h], radius=bar_h // 2, fill=bar_bg)

        # Active progress fill
        prog = max(0.0, min(1.0, self.progress))
        if prog > 0.005:
            fill_w = max(bar_h, int((bar_x2 - bar_x1) * prog))
            draw.rounded_rectangle([bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h], radius=bar_h // 2, fill=bar_fill)
            thumb_x = bar_x1 + fill_w
            thumb_r = int(4.5 * scale)
            # Pure white thumb, NO black outline
            thumb_outline = (245, 247, 250, 255) if is_opal else (255, 255, 255, 120)
            draw.ellipse([thumb_x - thumb_r, bar_y + bar_h // 2 - thumb_r, thumb_x + thumb_r, bar_y + bar_h // 2 + thumb_r], fill=(255, 255, 255, 255), outline=thumb_outline, width=scale)

        # -------------------------------------------------------------
        # BOTTOM DECK: Media Controls Bar (Balanced & Mathematically Spaced)
        # -------------------------------------------------------------
        deck_y = py + ch - int(24 * scale)
        center_x = (bar_x1 + bar_x2) // 2

        center_ico_name = "play" if self.is_paused else "stop"

        buttons = [
            ("shuffle", "shuffle", bar_x1 + int(24 * scale), deck_y, int(15 * scale)),
            ("prev", "prev", center_x - int(96 * scale), deck_y, int(16 * scale)),
            ("rewind", "rewind", center_x - int(48 * scale), deck_y, int(15 * scale)),
            ("play", center_ico_name, center_x, deck_y, int(20 * scale)),
            ("forward", "forward", center_x + int(48 * scale), deck_y, int(15 * scale)),
            ("next", "next", center_x + int(96 * scale), deck_y, int(16 * scale)),
            ("fav", "fav", bar_x2 - int(24 * scale), deck_y, int(15 * scale)),
        ]

        has_custom_icons = bool(self.icons)

        for bname, icon_key, bx, by, br in buttons:
            is_hover = (self.hover_btn == bname)

            if has_custom_icons and icon_key in self.icons:
                ico_img = self.icons[icon_key]
                if is_hover:
                    hr = max(ico_img.width, ico_img.height) // 2 + int(4 * scale)
                    draw.ellipse([bx - hr, by - hr, bx + hr, by + hr], fill=(255, 255, 255, 170) if is_opal else (255, 255, 255, 30))

                if not is_opal and bname in ("fav", "prev"):
                    # Soft frosted backlight in dark mode so dark details pop with 100% clarity
                    aur_r = max(ico_img.width, ico_img.height) // 2 + int(2 * scale)
                    draw.ellipse([bx - aur_r, by - aur_r, bx + aur_r, by + aur_r], fill=(255, 255, 255, 28))

                if bname == "shuffle" and self.is_shuffle:
                    # Subtle coral indicator dot matching theme
                    draw.ellipse([bx - int(2.5 * scale), by + int(14 * scale), bx + int(2.5 * scale), by + int(18 * scale)], fill=(253, 71, 133, 240))
                elif bname == "fav" and self.is_fav:
                    # Soft warm glow aura for favorites
                    draw.ellipse([bx - int(16 * scale), by - int(16 * scale), bx + int(16 * scale), by + int(16 * scale)], fill=(253, 71, 133, 50))

                hi_canvas.paste(ico_img, (bx - ico_img.width // 2, by - ico_img.height // 2), ico_img)
            else:
                # Vector math fallback
                if bname == "play":
                    btn_fill = (255, 255, 255, 240) if not is_hover else (255, 255, 255, 255)
                    draw.ellipse([bx - br, by - br, bx + br, by + br], fill=btn_fill)
                    sym_col = (18, 22, 32, 255)
                    if self.is_paused:
                        draw.polygon([(bx - int(4*scale), by - int(7*scale)), (bx + int(7*scale), by), (bx - int(4*scale), by + int(7*scale))], fill=sym_col)
                    else:
                        draw.rounded_rectangle([bx - int(5*scale), by - int(6.5*scale), bx - int(1.5*scale), by + int(6.5*scale)], radius=int(1.2*scale), fill=sym_col)
                        draw.rounded_rectangle([bx + int(1.5*scale), by - int(6.5*scale), bx + int(5*scale), by + int(6.5*scale)], radius=int(1.2*scale), fill=sym_col)
                else:
                    btn_fill = (255, 255, 255, 24) if is_hover else (255, 255, 255, 12)
                    draw.ellipse([bx - br, by - br, bx + br, by + br], fill=btn_fill, outline=(255, 255, 255, 45) if is_hover else (255, 255, 255, 22), width=scale)
                    icon_col = (255, 255, 255, 255) if is_hover else (200, 212, 228, 230)

                    if bname == "prev":
                        draw.polygon([(bx + int(5*scale), by - int(6*scale)), (bx - int(3*scale), by), (bx + int(5*scale), by + int(6*scale))], fill=icon_col)
                        draw.line([(bx - int(5*scale), by - int(6*scale)), (bx - int(5*scale), by + int(6*scale))], fill=icon_col, width=int(1.8*scale))

                    elif bname == "next":
                        draw.polygon([(bx - int(5*scale), by - int(6*scale)), (bx + int(3*scale), by), (bx - int(5*scale), by + int(6*scale))], fill=icon_col)
                        draw.line([(bx + int(5*scale), by - int(6*scale)), (bx + int(5*scale), by + int(6*scale))], fill=icon_col, width=int(1.8*scale))

                    elif bname == "rewind":
                        draw.polygon([(bx - int(1*scale), by - int(5*scale)), (bx - int(6*scale), by), (bx - int(1*scale), by + int(5*scale))], fill=icon_col)
                        draw.polygon([(bx + int(5*scale), by - int(5*scale)), (bx, by), (bx + int(5*scale), by + int(5*scale))], fill=icon_col)

                    elif bname == "forward":
                        draw.polygon([(bx - int(5*scale), by - int(5*scale)), (bx, by), (bx - int(5*scale), by + int(5*scale))], fill=icon_col)
                        draw.polygon([(bx + int(1*scale), by - int(5*scale)), (bx + int(6*scale), by), (bx + int(1*scale), by + int(5*scale))], fill=icon_col)

                    elif bname == "fav":
                        fav_col = (255, 59, 92, 255) if self.is_fav else (icon_col if is_hover else (170, 185, 205, 220))
                        h_pts = []
                        s_heart = int(14 * scale)
                        for deg in range(0, 360, 6):
                            t = math.radians(deg)
                            hx = 16 * (math.sin(t) ** 3)
                            hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                            px_h = bx + hx * (s_heart / 40)
                            py_h = by + (hy + 1.2) * (s_heart / 40)
                            h_pts.append((px_h, py_h))
                        if self.is_fav:
                            draw.polygon(h_pts, fill=fav_col)
                        else:
                            draw.polygon(h_pts, outline=fav_col, width=int(1.6 * scale))

                    elif bname == "shuffle":
                        sh_col = (56, 189, 248, 255) if self.is_shuffle else icon_col
                        sw = int(1.6 * scale)
                        draw.line([(bx - int(6*scale), by - int(4*scale)), (bx - int(2*scale), by - int(4*scale)), (bx + int(2*scale), by + int(4*scale)), (bx + int(6*scale), by + int(4*scale))], fill=sh_col, width=sw)
                        draw.polygon([(bx + int(6*scale), by + int(1*scale)), (bx + int(6*scale), by + int(6*scale)), (bx + int(3*scale), by + int(6*scale))], fill=sh_col)
                        draw.line([(bx - int(6*scale), by + int(4*scale)), (bx - int(2*scale), by + int(4*scale)), (bx - int(1*scale), by + int(2*scale))], fill=sh_col, width=sw)
                        draw.line([(bx + int(1*scale), by - int(2*scale)), (bx + int(2*scale), by - int(4*scale)), (bx + int(6*scale), by - int(4*scale))], fill=sh_col, width=sw)
                        draw.polygon([(bx + int(6*scale), by - int(6*scale)), (bx + int(6*scale), by - int(1*scale)), (bx + int(3*scale), by - int(6*scale))], fill=sh_col)

        # Downsample 2x with Bicubic for clean subpixel anti-aliasing with ultra-low CPU
        rendered_card = hi_canvas.resize((self.w, self.h), Image.Resampling.BICUBIC)
        final_img = Image.alpha_composite(self._cached_shadow, rendered_card)
        return final_img

    def update_surface(self):
        """Re-renders bitmap and updates layered window surface (alias for update_content)."""
        self.update_content()

    def update_content(self):
        """
        Re-renders card contents and pushes pixels to the persistent GDI DIB section.
        Call this ONLY when track, progress, or hover state changes.
        """
        pil_img = self.render_image()
        bgra_data = pil_to_premultiplied_bgra(pil_img)
        ctypes.memmove(self.p_bits, bgra_data, len(bgra_data))
        self._update_alpha_only()

    def _update_alpha_only(self):
        """
        Hardware-accelerated instant alpha update via Windows DWM compositor.
        Takes < 0.1ms with 0% CPU! Used for smooth 60 FPS fade transitions.
        """
        if not self.hwnd or not hasattr(self, "hdc_mem"):
            return

        blend = BLENDFUNCTION()
        blend.BlendOp = AC_SRC_OVER
        blend.BlendFlags = 0
        blend.SourceConstantAlpha = int(max(0, min(255, self.alpha)))
        blend.AlphaFormat = AC_SRC_ALPHA

        user32.UpdateLayeredWindow(
            self.hwnd,
            self.hdc_screen,
            ctypes.byref(self.pt_dst),
            ctypes.byref(self.sz),
            self.hdc_mem,
            ctypes.byref(self.pt_src),
            0,
            ctypes.byref(blend),
            ULW_ALPHA,
        )

    def show(
        self,
        header: str,
        title: str,
        artist: str = "",
        cur_time: str = "00:00",
        total_time: str = "00:00",
        progress: float = 0.0,
        cover_image: Image.Image | None = None,
        accent_rgb: tuple = (16, 225, 125),
        is_paused: bool = False,
        is_fav: bool = False,
        is_shuffle: bool = False,
        duration_s: float = 5.0,
        **kwargs,
    ):
        self.header_text = header
        self.title_text = title
        self.artist_text = artist
        if "time_str" in kwargs and kwargs["time_str"]:
            self.cur_time = str(kwargs["time_str"])
            self.total_time = "100%"
        else:
            self.cur_time = cur_time
            self.total_time = total_time
        self.progress = progress
        self.cover_img = cover_image
        self.accent_rgb = accent_rgb
        self.is_paused = is_paused
        self.is_fav = is_fav
        self.is_shuffle = is_shuffle

        self.hide_at = time.time() + duration_s
        self.target_alpha = 250
        self.update_content()
        user32.ShowWindow(self.hwnd, 8)  # SW_SHOWNA
        self._update_alpha_only()

    def check_hover_and_animate(self):
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        mx, my = pt.x, pt.y

        pad_x, pad_y = self.pad_x, self.pad_y
        x1 = self.x + pad_x
        x2 = self.x + self.w - pad_x
        y1 = self.y + pad_y
        y2 = self.y + self.h - pad_y

        is_in = (x1 <= mx <= x2) and (y1 <= my <= y2) and (self.alpha > 30)

        if is_in != self.is_hovered:
            self.is_hovered = is_in
            self._set_click_through(not is_in)
            if is_in:
                self.hide_at = time.time() + 99999.0  # keep open while user interacts
            else:
                self.hide_at = time.time() + 2.0  # comfortable 2.0s delay after cursor leaves
                self.hover_btn = ""
                self.update_content()

        now = time.time()
        # If not hovered and time expired, trigger fade out
        if self.target_alpha > 0 and now >= self.hide_at and not self.is_hovered:
            self.target_alpha = 0

        # Animate alpha transition (snappy Apple easing: ~90ms in, ~120ms out)
        if abs(self.alpha - self.target_alpha) > 4:
            if self.alpha < self.target_alpha:
                self.alpha = min(self.target_alpha, self.alpha + 85)
            else:
                self.alpha = max(0, self.alpha - 65)

            if self.alpha <= 5 and self.target_alpha == 0:
                self.alpha = 0
                user32.ShowWindow(self.hwnd, 0)
                self._set_click_through(True)

            self._update_alpha_only()
