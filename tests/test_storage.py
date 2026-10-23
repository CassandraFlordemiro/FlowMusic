# -*- coding: utf-8 -*-
"""
Unit tests for FlowMusic 360 Storage & Atomic File I/O.
"""

import json
import os
import tempfile
import unittest

from core.storage import (
    atomic_write_json,
    is_favorite,
    safe_read_json,
    save_favorites,
    toggle_favorite,
)


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.json")

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_atomic_write_and_read(self):
        data = {"app": "FlowMusic 360", "version": "1.1.0", "volume": 85}
        success = atomic_write_json(self.test_file, data)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.test_file))

        # Ensure no stray .tmp files left in the directory
        files = os.listdir(self.test_dir)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "test.json")

        # Read back
        loaded = safe_read_json(self.test_file)
        self.assertEqual(loaded, data)

    def test_safe_read_missing_file(self):
        non_existent = os.path.join(self.test_dir, "missing.json")
        res = safe_read_json(non_existent, default={"default": True})
        self.assertEqual(res, {"default": True})

    def test_safe_read_corrupted_json(self):
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json content :::")

        res = safe_read_json(self.test_file, default={"recovered": True})
        self.assertEqual(res, {"recovered": True})

        # Check that a backup file was created
        files = os.listdir(self.test_dir)
        bak_files = [f for f in files if ".bak" in f]
        self.assertGreaterEqual(len(bak_files), 1)


if __name__ == "__main__":
    unittest.main()

