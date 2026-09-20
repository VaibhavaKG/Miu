"""
Test Miu Home Window creation, navigation, and state display.
"""

import os
import sys
import unittest

os.environ["GDK_BACKEND"] = "x11"

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from miu_home import MiuHomeWindow, Star


class TestMiuHome(unittest.TestCase):
    def setUp(self):
        self.home = MiuHomeWindow(app=None)

    def tearDown(self):
        if self.home:
            self.home.destroy()

    def test_window_creation(self):
        self.assertIsNotNone(self.home)
        self.assertEqual(self.home.get_title(), "Miu Observatory Control Console")

    def test_stars_initialization(self):
        self.assertGreaterEqual(len(self.home.stars), 40)
        star = self.home.stars[0]
        self.assertIsInstance(star, Star)

    def test_nav_stack_pages_exist(self):
        pages = ["home", "cosmetics", "focus", "literature", "stats", "about"]
        for p in pages:
            child = self.home.nav_stack.get_child_by_name(p)
            self.assertIsNotNone(child, f"Page '{p}' should exist in nav_stack")

    def test_habitat_tab_components(self):
        self.assertIsNotNone(self.home.pet_canvas)
        self.assertIsNotNone(self.home.lbl_spotify)
        self.assertIsNotNone(self.home.lbl_hab_name)


if __name__ == "__main__":
    unittest.main()
