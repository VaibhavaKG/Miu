"""
End-to-end Integration Test for Oneko Desktop Companion on Fedora/Linux.
Tests the live GTK application lifecycle, focus sessions, literary drops, and preferences dialog.
"""

import os
import sys
import json
import unittest

os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR_PATH = os.path.join(os.path.dirname(TESTS_DIR), "app")
if APP_DIR_PATH not in sys.path:
    sys.path.insert(0, APP_DIR_PATH)

from oneko_plus import OnekoCompanionApp, APP_DIR, CONFIG_FILE
from pet_state import PetState
from pomodoro import PomodoroPhase


class TestOnekoAppIntegration(unittest.TestCase):
    def setUp(self):
        self.app = OnekoCompanionApp()

    def tearDown(self):
        self.app.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration()

    def test_startup_lifecycle(self):
        self.assertEqual(self.app.config["focus_duration_min"], 45)
        self.assertEqual(self.app.pomodoro.focus_duration_min, 45)
        self.assertEqual(self.app.pomodoro.get_time_string(), "45:00")
        self.assertFalse(self.app.literary.is_active)
        self.assertEqual(self.app.pet_state.personality_key, "calm")

    def test_focus_and_literary_flow(self):
        # 1. Start 45 min Focus
        self.app.start_focus_session()
        self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.FOCUS)
        self.assertEqual(self.app.pet_state.state, PetState.FOCUSED)
        self.assertEqual(self.app.pomodoro.time_left, 45 * 60)

        # 2. Fast-forward timer to 1 second
        self.app.pomodoro.time_left = 1
        self.app.on_second_tick()

        # 3. Focus finished -> Break starts
        self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.BREAK)
        self.assertEqual(self.app.pet_state.state, PetState.BREAK)

        # 4. Literary drop triggered automatically on break!
        self.assertTrue(self.app.literary.is_active)
        self.assertIsNotNone(self.app.literary.current_work)
        drop = self.app.literary.current_work
        self.assertIn("text", drop)
        self.assertIn("author", drop)
        self.assertNotIn("\n", drop["text"])

        # 5. Test Save action
        self.app.literary.save_current()
        self.assertTrue(self.app.literary.is_current_saved())

        # 6. Test Next action
        next_work = self.app.literary.next_drop()
        self.assertIsNotNone(next_work)

        # 7. Test Close action
        self.app.dismiss_active_popup()
        self.assertFalse(self.app.literary.is_active)

    def test_dragging_interaction(self):
        initial_x = self.app.cat_x
        initial_y = self.app.cat_y

        # Simulate drag
        self.app.drag_potential = True
        self.app.is_dragging = True
        self.app.pet_state.is_dragged = True
        self.app.cat_start_drag_x = initial_x
        self.app.cat_start_drag_y = initial_y

        # Move 50px right, 30px down
        self.app.cat_x = initial_x + 50
        self.app.cat_y = initial_y + 30
        self.app.update_window_shape_and_size()

        self.assertEqual(self.app.cat_x, initial_x + 50)
        self.assertEqual(self.app.cat_y, initial_y + 30)

        # Release drag
        self.app.is_dragging = False
        self.app.drag_potential = False
        self.app.pet_state.is_dragged = False
        self.app.save_config()

        # Check config persisted position
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["last_pos_x"], int(initial_x + 50))
        self.assertEqual(cfg["last_pos_y"], int(initial_y + 30))

    def test_preferences_dialog_open_and_close(self):
        self.app.open_preferences()
        self.assertIsNotNone(self.app.preferences_dialog)
        self.assertTrue(self.app.preferences_dialog.get_visible())

        # Close dialog
        self.app.preferences_dialog.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.assertIsNone(self.app.preferences_dialog)


if __name__ == "__main__":
    unittest.main()
