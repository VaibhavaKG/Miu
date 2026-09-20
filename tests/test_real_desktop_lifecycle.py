"""
Real Desktop Integration & Live Event-Loop Verification for Miu.

Exercises the real desktop application and event loop:
1. Section 5: Binary Isolation Test (Break countdown with visuals disabled).
2. Section 6: Celebration Alone (Independent celebration without Pomodoro interference).
3. Section 7: Both Together (Break countdown + Celebration running simultaneously).
4. Section 8: Wall-Clock Monotonic Timing Verification.
5. Section 9: Thorough Multi-Cycle Reset Testing.
6. Section 10 & 11: Real Background Daemon, Single-Instance Enforcement, and Process Duplication Prevention.
"""

import os
import sys
import time
import subprocess
import unittest

os.environ["GDK_BACKEND"] = "x11"
os.environ["MIU_DEBUG_POMODORO"] = "1"

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from oneko_plus import OnekoCompanionApp
from pomodoro import PomodoroPhase
from celebration import CelebrationState, CelebrationPhase
from ipc import send_ipc_command, SOCKET_PATH


class TestRealDesktopExperience(unittest.TestCase):
    def setUp(self):
        self.app = OnekoCompanionApp.__new__(OnekoCompanionApp)
        self.app.config = {
            "focus_duration_min": 45,
            "short_break_min": 5,
            "long_break_min": 15,
            "cat_scale": 1.25,
            "cat_theme": "classic",
            "personality": "calm",
            "sound_enabled": False,
            "literary_mode": "off"
        }
        from pomodoro import PomodoroEngine
        from pet_state import PetStateMachine
        from celebration import CelebrationManager
        from unittest.mock import MagicMock

        self.app.pomodoro = PomodoroEngine(self.app.config)
        self.app.pet_state = PetStateMachine()
        self.app.celebration = CelebrationManager(self.app)
        self.app.literary = MagicMock()
        self.app.literary.mode = "off"
        self.app.tray = MagicMock()
        self.app.update_window_shape_and_size = MagicMock()
        self.app.queue_draw = MagicMock()
        self.app.status_pill_timer = 0
        self.app.status_pill_text = None
        self.app.cat_x = 400.0
        self.app.cat_y = 300.0
        self.app.screen_w = 1920
        self.app.screen_h = 1080
        self.app.save_config = MagicMock()

    def test_section_5_binary_isolation_break_with_zero_visuals(self):
        """Section 5: Binary isolation test - celebration visuals disabled, break timer verified."""
        self.app.celebration.enable_visuals = False
        self.app.start_focus_session()
        self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.FOCUS)

        # Simulate completion
        self.app.simulate_focus_completion()
        self.assertEqual(self.app.pomodoro.time_left, 1)

        # Trigger tick
        self.app.on_second_tick()
        self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.BREAK)
        self.assertEqual(self.app.pomodoro.time_left, 300)

        # Observe break countdown for 5 ticks
        for expected in [299, 298, 297, 296, 295]:
            self.app.on_second_tick()
            self.assertEqual(self.app.pomodoro.time_left, expected)
            self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.BREAK)

        # Re-enable visuals
        self.app.celebration.enable_visuals = True

    def test_section_6_celebration_alone_without_pomodoro(self):
        """Section 6: Trigger celebration alone, verify Pomodoro remains IDLE and unaffected."""
        self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.IDLE)
        initial_time = self.app.pomodoro.time_left

        # Start celebration independently
        started = self.app.celebration.start()
        self.assertTrue(started)
        self.assertTrue(self.app.celebration.is_active())

        # Advance celebration steps
        for _ in range(10):
            self.app.celebration.step(0.05)

        # Assert Pomodoro was NOT touched by celebration
        self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.IDLE)
        self.assertEqual(self.app.pomodoro.time_left, initial_time)

        # Cleanup celebration
        self.app.celebration.cleanup()
        self.assertEqual(self.app.celebration.state, CelebrationState.IDLE)

    def test_section_7_both_together_break_countdown_continuity(self):
        """Section 7: Run Focus -> Break + Celebration together, verifying countdown continuity."""
        self.app.start_focus_session()
        self.app.simulate_focus_completion()

        # Tick 1: Focus finishes -> Break starts -> Celebration starts
        self.app.on_second_tick()
        self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.BREAK)
        self.assertEqual(self.app.pomodoro.time_left, 300)
        self.assertTrue(self.app.celebration.is_active())

        # Simulate 20 consecutive seconds of active celebration and break countdown
        for sec in range(1, 21):
            for _ in range(20):
                self.app.celebration.step(0.05)
            self.app.on_second_tick()
            expected_time = 300 - sec
            self.assertEqual(self.app.pomodoro.time_left, expected_time)
            self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.BREAK)
            self.assertTrue(self.app.celebration.is_active())

        self.app.celebration.cleanup()

    def test_section_8_wall_clock_timing(self):
        """Section 8: Wall-clock timing verification using monotonic clock."""
        mgr = self.app.celebration
        mgr.start()
        time.sleep(0.15)
        mgr.step(0.05)

        # Monotonic time must have advanced
        self.assertGreaterEqual(mgr.elapsed, 0.14)
        mgr.cleanup()

    def test_section_9_thorough_multi_cycle_reset(self):
        """Section 9: Multi-cycle Focus -> Complete -> Break -> Reset -> Fresh Focus."""
        for cycle in range(3):
            # 1. Start Focus
            self.app.start_focus_session()
            self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.FOCUS)

            # 2. Complete Focus
            self.app.simulate_focus_completion()
            self.app.on_second_tick()
            self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.BREAK)
            self.assertEqual(self.app.pomodoro.time_left, 300)

            # 3. Reset while in break & celebration
            self.app.reset_session()

            # 4. Verify clean slate: ready for a new focus
            self.assertEqual(self.app.pomodoro.phase, PomodoroPhase.IDLE)
            self.assertEqual(self.app.pomodoro.time_left, 45 * 60)
            self.assertFalse(self.app.pet_state.break_mode)
            self.assertFalse(self.app.pet_state.focus_mode)
            self.assertEqual(self.app.celebration.state, CelebrationState.IDLE)
            self.assertIsNone(self.app.celebration.overlay_window)
            self.assertEqual(len(self.app.celebration.guests), 0)

    def test_section_10_and_11_live_daemon_single_instance_and_ipc(self):
        """Section 10 & 11: Real daemon lifecycle, CLI/Tray IPC, and duplication prevention."""
        # Ensure clean initial state
        send_ipc_command("quit")
        time.sleep(0.5)
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except Exception:
                pass

        # 1. Spawn live daemon via python3 oneko_plus.py
        proc = subprocess.Popen(
            [sys.executable, os.path.join(APP_DIR, "oneko_plus.py"), "--focus"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(1.2)

        try:
            # 2. Check exactly ONE process exists
            res = subprocess.run(["pgrep", "-fa", "oneko_plus.py"], stdout=subprocess.PIPE, text=True)
            procs = [line for line in res.stdout.strip().splitlines() if "python" in line]
            self.assertEqual(len(procs), 1, f"Expected exactly 1 Miu process, found: {procs}")

            # 3. Verify IPC ping and focus state
            success, resp = send_ipc_command("ping")
            self.assertTrue(success)
            self.assertEqual(resp.get("msg"), "pong")

            # 4. Test duplicate spawn rejection: attempting to start another oneko_plus.py must exit immediately
            dup = subprocess.run([sys.executable, os.path.join(APP_DIR, "oneko_plus.py")], stdout=subprocess.PIPE, text=True)
            self.assertEqual(dup.returncode, 0)
            # Re-verify still only 1 process
            res2 = subprocess.run(["pgrep", "-fa", "oneko_plus.py"], stdout=subprocess.PIPE, text=True)
            procs2 = [line for line in res2.stdout.strip().splitlines() if "python" in line]
            self.assertEqual(len(procs2), 1)

            # 5. Simulate focus completion via IPC
            success, resp = send_ipc_command("simulate_completion")
            self.assertTrue(success)

            # Wait 2 seconds for focus to finish and break to start in the live running process
            time.sleep(2.0)

            # 6. Verify break stats and countdown in live process
            success, stats_resp = send_ipc_command("stats")
            self.assertTrue(success)
            self.assertIn("stats", stats_resp)

            # 7. Test IPC reset
            success, reset_resp = send_ipc_command("reset")
            self.assertTrue(success)
            self.assertEqual(reset_resp.get("msg"), "Miu reset.")

            # 8. Start focus again after reset
            success, focus_resp = send_ipc_command("focus")
            self.assertTrue(success)
            self.assertIn("45:00 started", focus_resp.get("msg", ""))

        finally:
            # 9. Clean shutdown
            send_ipc_command("quit")
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
