# -*- coding: utf-8 -*-
"""Unit tests for AcrylicHUDWindow performance, GDI, and hit-testing."""

import unittest
from PIL import Image
from hud_acrylic import AcrylicHUDWindow, pil_to_premultiplied_bgra, clean_header_text


class TestAcrylicHUD(unittest.TestCase):
    def test_premultiplied_bgra(self):
        im = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
        data = pil_to_premultiplied_bgra(im)
        self.assertEqual(len(data), 10 * 10 * 4)
        # In BGRa with half alpha: Blue=0, Green=0, Red=128, Alpha=128
        self.assertEqual(data[0], 0)
        self.assertEqual(data[1], 0)
        self.assertEqual(data[2], 128)
        self.assertEqual(data[3], 128)

    def test_clean_header_text(self):
        cleaned = clean_header_text("🎵 TOCANDO AGORA • POP HITS")
        self.assertNotIn("•", cleaned)
        self.assertIn("·", cleaned)

    def test_hud_instance_and_render(self):
        hud = AcrylicHUDWindow()
        self.assertEqual(hud.w, 540)
        self.assertEqual(hud.h, 172)
        self.assertEqual(hud.scale, 2)
        
        img = hud.render_image()
        self.assertEqual(img.size, (540, 172))
        
        # Test content update and alpha update
        hud.update_content()
        hud.alpha = 100
        hud._update_alpha_only()
        
        # Test button hit-testing
        # Close button (near top right)
        cw = hud.card_w
        px = hud.pad_x
        close_x = px + cw - 18
        close_y = hud.pad_y + 14 + 7
        self.assertEqual(hud._get_button_at(close_x, close_y), "close")
        
        # Theme toggle button (beside close button)
        theme_btn_x = px + cw - 16 - 26
        theme_btn_y = hud.pad_y + 14 + 8
        self.assertEqual(hud._get_button_at(theme_btn_x, theme_btn_y), "theme_toggle")
        
        # Test theme toggle functionality
        self.assertEqual(hud.theme, "opal")
        new_th = hud.toggle_theme()
        self.assertEqual(new_th, "dark")
        self.assertEqual(hud.theme, "dark")
        back_th = hud.toggle_theme()
        self.assertEqual(back_th, "opal")
        self.assertEqual(hud.theme, "opal")
        
        # Play button (center deck)
        center_x = (px + 16 + px + cw - 16) // 2
        deck_y = hud.pad_y + hud.card_h - 24
        self.assertEqual(hud._get_button_at(center_x, deck_y), "play")


if __name__ == "__main__":
    unittest.main()

