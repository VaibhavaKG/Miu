#!/usr/bin/env python3
"""
Comprehensive tests for Miu Active Desktop-Aware Behaviour.
Tests WindowSurface, DesktopTopology, DestinationPicker, PetStateMachine active timers,
and OnekoCompanionApp movement / evasion mechanics.
"""

import unittest
import os
import sys
import math
import time

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from topology import WindowSurface, DesktopTopology, DestinationPicker
from pet_state import PetStateMachine, PetState, Personality


class TestWindowSurface(unittest.TestCase):
    def setUp(self):
        self.win = WindowSurface(
            win_id="0x123456",
            title="Code - Visual Studio Code",
            app_name="Code",
            x=200,
            y=150,
            w=800,
            h=600
        )

    def test_geometry_and_points(self):
        self.assertEqual(self.win.top_left, (200, 150))
        self.assertEqual(self.win.top_right, (1000, 150))
        self.assertEqual(self.win.bottom_left, (200, 750))
        self.assertEqual(self.win.bottom_right, (1000, 750))
        self.assertEqual(self.win.top_middle, (600, 150))

    def test_contains(self):
        self.assertTrue(self.win.contains(500, 300))
        self.assertTrue(self.win.contains(200, 150))
        self.assertFalse(self.win.contains(100, 100))
        self.assertFalse(self.win.contains(1200, 800))

    def test_climb_mission_from_left(self):
        # Approaching from left side of window
        mission = self.win.get_climb_mission(start_x=50, start_y=400)
        self.assertEqual(mission["type"], "climb")
        self.assertEqual(mission["side"], "left")
        self.assertEqual(mission["window_id"], "0x123456")

        waypoints = mission["waypoints"]
        self.assertEqual(len(waypoints), 5)
        self.assertEqual(waypoints[0]["action"], "walk")
        self.assertEqual(waypoints[1]["action"], "climb_up")
        self.assertEqual(waypoints[2]["action"], "ledge_walk")
        self.assertEqual(waypoints[3]["action"], "ledge_pause")
        self.assertEqual(waypoints[4]["action"], "climb_down")

        # Verify coordinates progression
        # Base approach is near left edge
        self.assertAlmostEqual(waypoints[0]["pos"][0], 192, delta=2)
        # Climb up reaches top left
        self.assertAlmostEqual(waypoints[1]["pos"][0], 192, delta=2)
        self.assertAlmostEqual(waypoints[1]["pos"][1], 146, delta=2)
        # Ledge walk reaches middle
        self.assertEqual(waypoints[2]["pos"][0], 600)
        # Pause is at far right corner
        self.assertAlmostEqual(waypoints[3]["pos"][0], 988, delta=2)

    def test_climb_mission_from_right(self):
        # Approaching from right side of window
        mission = self.win.get_climb_mission(start_x=1150, start_y=500)
        self.assertEqual(mission["type"], "climb")
        self.assertEqual(mission["side"], "right")
        waypoints = mission["waypoints"]
        self.assertEqual(len(waypoints), 5)
        # Base approach is near right edge
        self.assertAlmostEqual(waypoints[0]["pos"][0], 1008, delta=2)
        # Climb up reaches top right
        self.assertAlmostEqual(waypoints[1]["pos"][0], 1008, delta=2)


class TestDesktopTopology(unittest.TestCase):
    def setUp(self):
        self.topo = DesktopTopology(screen_w=1920, screen_h=1080)

    def test_screen_bounds_update(self):
        self.topo.update_screen_bounds(2560, 1440)
        self.assertEqual(self.topo.screen_w, 2560)
        self.assertEqual(self.topo.screen_h, 1440)

    def test_suitability_filtering_wmctrl(self):
        # Simulate wmctrl parsing with mock data
        raw_lines = [
            "0x0100001  0  100  100  800  600  fedora  Editor - File",
            "0x0100002  0    0    0 1920 1080  fedora  Desktop",         # Fullscreen desktop -> ignore
            "0x0100003  0   50   50   50   50  fedora  Small Tooltip",   # Too small -> ignore
            "0x0100004  0  200  200  700  500  fedora  Miu Companion",   # Miu's own window -> ignore
            "0x0100005  0  300  250  600  400  fedora  Terminal",        # Terminal window -> ignore
            "0x0100006  0  300  250  600  400  fedora  Web Browser",     # Suitable window
        ]
        surfaces = []
        ignored_keywords = (
            "miu", "oneko", "terminal", "console", "pty", "bash", "zsh",
            "alacritty", "kitty", "foot", "wezterm", "gnome-terminal",
            "prompt", "auth", "polkit", "dialog", "notification"
        )
        for line in raw_lines:
            parts = line.split(None, 7)
            win_id, desktop_id, x, y, w, h, host, title = parts
            x, y, w, h = int(x), int(y), int(w), int(h)
            name = title.lower()
            if any(k in name for k in ignored_keywords):
                continue
            if w < 200 or h < 180:
                continue
            if w >= self.topo.screen_w - 20 and h >= self.topo.screen_h - 60:
                continue
            surfaces.append(WindowSurface(win_id, title, "", x, y, w, h))

        self.assertEqual(len(surfaces), 2)
        titles = [s.title for s in surfaces]
        self.assertIn("Editor - File", titles)
        self.assertIn("Web Browser", titles)
        self.assertNotIn("Desktop", titles)
        self.assertNotIn("Small Tooltip", titles)
        self.assertNotIn("Miu Companion", titles)
        self.assertNotIn("Terminal", titles)


class TestDestinationPicker(unittest.TestCase):
    def setUp(self):
        self.topo = DesktopTopology(screen_w=1920, screen_h=1080)
        self.win1 = WindowSurface("win1", "Browser", "Chrome", 300, 200, 800, 600)
        self.win2 = WindowSurface("win2", "Docs", "Writer", 1200, 250, 600, 500)
        self.topo.windows = [self.win1, self.win2]
        self.picker = DestinationPicker(self.topo)

    def test_recent_destination_buffer(self):
        self.picker.record_destination(100, 100, "win1")
        self.assertTrue(self.picker.is_too_close_to_recent(120, 110, min_dist=50))
        self.assertFalse(self.picker.is_too_close_to_recent(300, 300, min_dist=50))
        self.assertIn("win1", self.picker.recent_window_ids)

    def test_pick_next_normal_mode(self):
        dest = self.picker.pick_next(cur_x=100, cur_y=100, mouse_x=500, mouse_y=500, mode="normal")
        self.assertIsNotNone(dest)
        self.assertIn(dest.get("type"), ("walk", "climb"))
        if dest["type"] == "walk":
            x, y = dest["pos"]
            self.assertGreaterEqual(x, 20)
            self.assertLessEqual(x, 1900)
            self.assertGreaterEqual(y, 20)
            self.assertLessEqual(y, 1060)

    def test_pick_next_focused_mode_perimeter_and_ledges(self):
        # In focus mode, Miu must pick peaceful spots away from the cursor
        dest = self.picker.pick_next(cur_x=500, cur_y=500, mouse_x=500, mouse_y=500, mode="focused")
        self.assertIsNotNone(dest)
        self.assertEqual(dest["type"], "walk")
        x, y = dest["pos"]
        # Must maintain distance from cursor (at 500, 500)
        dist_from_mouse = math.hypot(x - 500, y - 500)
        self.assertGreaterEqual(dist_from_mouse, 150)
        self.assertEqual(dest.get("post_action"), "sit")

    def test_pick_next_break_mode(self):
        # In break mode, climbs or walks are dispatched
        dest = self.picker.pick_next(cur_x=100, cur_y=100, mouse_x=900, mouse_y=900, mode="break")
        self.assertIsNotNone(dest)
        self.assertIn(dest.get("type"), ("walk", "climb"))


class TestPetStateMachineActive(unittest.TestCase):
    def setUp(self):
        self.sm = PetStateMachine(personality_key="calm")

    def test_active_breathers_not_sleeping(self):
        # Miu should not be stuck in permanent idle
        self.sm.next_idle_action_time = time.time() - 1.0
        self.assertTrue(self.sm.should_pick_new_destination())

        # When walking, should_pick_new_destination is False
        self.sm.state = PetState.WALKING
        self.assertFalse(self.sm.should_pick_new_destination())

        # When climbing, should_pick_new_destination is False
        self.sm.state = PetState.CLIMBING
        self.assertFalse(self.sm.should_pick_new_destination())

    def test_on_reached_destination_transitions(self):
        self.sm.on_reached_destination(post_action="sit")
        self.assertEqual(self.sm.state, PetState.SITTING)

        self.sm.on_reached_destination(post_action="look")
        self.assertEqual(self.sm.state, PetState.CURIOUS)

        self.sm.on_reached_destination(post_action="stretch")
        self.assertEqual(self.sm.state, PetState.STRETCHING)

    def test_anti_comatose_focus_mode(self):
        self.sm.set_focus_mode(True)
        self.assertEqual(self.sm.state, PetState.FOCUSED)
        # In focus mode, sm.update must never send Miu to sleep
        for _ in range(20):
            state = self.sm.update(dt=0.05, dist_to_target=200, is_mouse_moving=False)
            self.assertNotEqual(state, PetState.SLEEPING)

    def test_sleeping_capped_duration(self):
        # If pet enters sleeping state, it must wake up within max 9 seconds
        self.sm.state = PetState.SLEEPING
        self.sm.state_timer = 9.5
        new_state = self.sm.update(dt=0.1, dist_to_target=200, is_mouse_moving=False)
        self.assertEqual(new_state, PetState.STRETCHING)

    def test_effective_speed_climbing(self):
        base_speed = 10.0
        self.sm.state = PetState.CLIMBING
        climb_speed = self.sm.get_effective_speed(base_speed, "normal")
        self.sm.state = PetState.WALKING
        walk_speed = self.sm.get_effective_speed(base_speed, "normal")
        # Climbing speed should be more deliberate and steady than walking speed
        self.assertLess(climb_speed, walk_speed)


if __name__ == "__main__":
    unittest.main()
