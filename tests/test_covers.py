# -*- coding: utf-8 -*-
"""
Unit tests for FlowMusic 360 Cover Art Provider & Cache Keys.
"""

import unittest

from ui.covers import extract_embedded_apic, get_track_cache_key


class TestCovers(unittest.TestCase):
    def test_cache_key_stability(self):
        p1 = r"C:\Users\Administrator\Downloads\YouTube_Music\01 - Song.mp3"
        p2 = r"c:\users\administrator\downloads\youtube_music\01 - song.mp3"
        # Case insensitive on Windows
        self.assertEqual(get_track_cache_key(p1), get_track_cache_key(p2))

    def test_cache_key_uniqueness(self):
        p1 = r"C:\Music\Song1.mp3"
        p2 = r"C:\Music\Song2.mp3"
        self.assertNotEqual(get_track_cache_key(p1), get_track_cache_key(p2))

    def test_non_existent_apic(self):
        self.assertIsNone(extract_embedded_apic("non_existent_file.mp3"))


if __name__ == "__main__":
    unittest.main()

