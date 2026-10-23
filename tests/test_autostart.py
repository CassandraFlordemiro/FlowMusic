# -*- coding: utf-8 -*-
"""
Unit tests for FlowMusic 360 Windows Autostart Manager.
"""

import os
import unittest

from services.autostart import (
    VBS_PATH,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
)


class TestAutostart(unittest.TestCase):
    def test_autostart_lifecycle(self):
        # Initial status
        init_state = is_autostart_enabled()

        # Enable
        success_enable = enable_autostart()
        self.assertTrue(success_enable)
        self.assertTrue(is_autostart_enabled())
        self.assertTrue(os.path.isfile(VBS_PATH))

        # Disable
        success_disable = disable_autostart()
        self.assertTrue(success_disable)
        self.assertFalse(is_autostart_enabled())
        self.assertFalse(os.path.isfile(VBS_PATH))

        # Restore initial state if it was enabled
        if init_state:
            enable_autostart()


if __name__ == "__main__":
    unittest.main()

