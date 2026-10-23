# -*- coding: utf-8 -*-
"""
Unit tests for FlowMusic 360 Library Scanner & Search Engine.
"""

import os
import tempfile
import unittest

from core.library import (
    natural_sort_key,
    normalize_text,
    parse_track_filename,
    search_tracks,
)


class TestLibrary(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(normalize_text("Música"), "musica")
        self.assertEqual(normalize_text("Coração D'Água"), "coracao d'agua")
        self.assertEqual(normalize_text("  Rockafeller SKANK  "), "rockafeller skank")
        self.assertEqual(normalize_text(""), "")

    def test_natural_sort_key(self):
        items = ["01 - Intro.mp3", "10 - Finale.mp3", "02 - Track.mp3", "20 - Bonus.mp3"]
        sorted_items = sorted(items, key=natural_sort_key)
        self.assertEqual(sorted_items[0], "01 - Intro.mp3")
        self.assertEqual(sorted_items[1], "02 - Track.mp3")
        self.assertEqual(sorted_items[2], "10 - Finale.mp3")
        self.assertEqual(sorted_items[3], "20 - Bonus.mp3")

    def test_parse_track_filename(self):
        dummy_path = r"C:\Users\Administrator\Downloads\YouTube_Music\The Best of FIFA\02 - Rockafeller Skank.mp3"
        root_dir = r"C:\Users\Administrator\Downloads\YouTube_Music"
        track = parse_track_filename(dummy_path, root_dir)

        self.assertEqual(track["track_num"], "02")
        self.assertEqual(track["title"], "Rockafeller Skank")
        self.assertEqual(track["display_title"], "02 - Rockafeller Skank")
        self.assertEqual(track["playlist"], "The Best of FIFA")
        self.assertEqual(track["ext"], ".mp3")

    def test_search_tracks(self):
        tracks = [
            {
                "path": r"C:\Music\01 - Song 2.mp3",
                "title": "Song 2",
                "display_title": "01 - Song 2",
                "artist": "Blur",
                "track_num": "01",
                "playlist": "FIFA",
                "is_favorite": True,
                "search_blob": "01 - song 2 song 2 blur fifa 01 - song 2",
            },
            {
                "path": r"C:\Music\02 - Rockafeller Skank.mp3",
                "title": "Rockafeller Skank",
                "display_title": "02 - Rockafeller Skank",
                "artist": "Fatboy Slim",
                "track_num": "02",
                "playlist": "FIFA",
                "is_favorite": False,
                "search_blob": "02 - rockafeller skank rockafeller skank fatboy slim fifa 02 - rockafeller skank",
            },
        ]

        # Exact title match
        results = search_tracks("Song 2", tracks)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Song 2")

        # Artist search
        results_art = search_tracks("Fatboy", tracks)
        self.assertEqual(len(results_art), 1)
        self.assertEqual(results_art[0]["title"], "Rockafeller Skank")

        # Track number search
        results_num = search_tracks("01", tracks)
        self.assertEqual(len(results_num), 1)
        self.assertEqual(results_num[0]["title"], "Song 2")


if __name__ == "__main__":
    unittest.main()

