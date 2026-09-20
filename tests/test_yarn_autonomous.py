"""
Test Yarn Ball Autonomous Controller behavior, cooldowns, and focus mode suppression.
"""

import os
import sys
import unittest
import time

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from living_world import YarnBallAutonomousController, ToyType


class TestYarnAutonomous(unittest.TestCase):
    def setUp(self):
        self.controller = YarnBallAutonomousController(cooldown=1.0)  # 1 second for fast testing

    def test_can_spawn_initially(self):
        self.assertTrue(self.controller.can_spawn(mode="normal"))

    def test_focus_mode_suppression(self):
        self.assertFalse(self.controller.can_spawn(mode="focused"))

    def test_cooldown_enforcement(self):
        self.assertTrue(self.controller.can_spawn(mode="normal"))
        self.controller.record_spawn()
        self.assertFalse(self.controller.can_spawn(mode="normal"))
        time.sleep(1.1)
        self.assertTrue(self.controller.can_spawn(mode="normal"))

    def test_reset_cooldown(self):
        self.controller.record_spawn()
        self.assertFalse(self.controller.can_spawn(mode="normal"))
        self.controller.reset_cooldown()
        self.assertTrue(self.controller.can_spawn(mode="normal"))


if __name__ == "__main__":
    unittest.main()
