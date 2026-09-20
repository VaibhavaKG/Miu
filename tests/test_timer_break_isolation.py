"""
Test Suite: Timer Completion & Break Failure Isolation
Verifies:
- Test A: Normal completion -> reliable BREAK transition -> 5-minute break countdown.
- Test B: Reset before completion -> cleanly restart focus.
- Test C: Reset during break -> cleanly restart focus without leftover state.
- Test D: Break pause & resume work independently of celebration.
- Test E: MANDATORY: Celebration throwing an intentional exception DOES NOT interrupt or break the break countdown.
- Test F: 60-second celebration lifecycle & strict anti-duplication lock.
- Test G: Simulated focus completion hook without altering permanent 45m config.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.path.dirname(TESTS_DIR), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from pomodoro import PomodoroEngine, PomodoroPhase
from pet_state import PetStateMachine, PetState
from celebration import CelebrationManager, CelebrationState, CelebrationPhase
from oneko_plus import OnekoCompanionApp


class TestTimerBreakIsolation(unittest.TestCase):
    def setUp(self):
        self.config = {
            "focus_duration_min": 45,
            "short_break_min": 5,
            "long_break_min": 15,
            "sound_enabled": False,
            "cat_scale": 1.25,
            "cat_theme": "classic",
            "personality": "calm",
            "literary_mode": "off"
        }

    def test_a_normal_completion_and_break_countdown(self):
        """Test A: Start Focus -> reach zero -> BREAK starts -> 5:00 countdown continues."""
        engine = PomodoroEngine(self.config)
        engine.start_focus()
        self.assertEqual(engine.phase, PomodoroPhase.FOCUS)
        self.assertEqual(engine.time_left, 45 * 60)

        # Fast-forward to 1 second remaining
        engine.time_left = 1
        changed, event = engine.tick()

        # Authoritative transition to BREAK
        self.assertTrue(changed)
        self.assertEqual(event, "focus_finished")
        self.assertEqual(engine.phase, PomodoroPhase.BREAK)
        self.assertEqual(engine.time_left, 5 * 60)
        self.assertEqual(engine.get_time_string(), "05:00")

        # Verify break countdown decrements on subsequent ticks
        for remaining in [299, 298, 297]:
            changed, event = engine.tick()
            self.assertFalse(changed)
            self.assertEqual(engine.phase, PomodoroPhase.BREAK)
            self.assertEqual(engine.time_left, remaining)

    def test_b_reset_before_completion_and_restart(self):
        """Test B: Start Focus -> Reset before completion -> Start Focus again -> works normally."""
        engine = PomodoroEngine(self.config)
        engine.start_focus()
        engine.time_left = 1800  # 30 min in

        engine.reset()
        self.assertEqual(engine.phase, PomodoroPhase.IDLE)
        self.assertEqual(engine.time_left, 45 * 60)

        # Restart focus
        engine.start_focus()
        self.assertEqual(engine.phase, PomodoroPhase.FOCUS)
        self.assertEqual(engine.time_left, 45 * 60)
        engine.tick()
        self.assertEqual(engine.time_left, 45 * 60 - 1)

    def test_c_reset_during_break_and_restart(self):
        """Test C: Focus completes -> BREAK starts -> Reset -> cleanly returns to IDLE ready for Focus."""
        engine = PomodoroEngine(self.config)
        engine.start_focus()
        engine.time_left = 1
        engine.tick()
        self.assertEqual(engine.phase, PomodoroPhase.BREAK)

        # Reset during break
        engine.reset()
        self.assertEqual(engine.phase, PomodoroPhase.IDLE)
        self.assertEqual(engine.time_left, 45 * 60)

        # Restart focus session without residual break state
        engine.start_focus()
        self.assertEqual(engine.phase, PomodoroPhase.FOCUS)
        self.assertEqual(engine.time_left, 45 * 60)

    def test_d_break_pause_and_resume(self):
        """Test D: Focus completes -> BREAK -> pause -> resume -> countdown continues."""
        engine = PomodoroEngine(self.config)
        engine.start_focus()
        engine.time_left = 1
        engine.tick()
        self.assertEqual(engine.phase, PomodoroPhase.BREAK)
        self.assertEqual(engine.time_left, 300)

        # Pause during break
        engine.pause()
        self.assertEqual(engine.phase, PomodoroPhase.PAUSED)
        self.assertEqual(engine.paused_from, PomodoroPhase.BREAK)

        # Ticking while paused should NOT decrement time
        engine.tick()
        self.assertEqual(engine.time_left, 300)

        # Resume
        engine.resume()
        self.assertEqual(engine.phase, PomodoroPhase.BREAK)

        # Ticking resumes countdown
        engine.tick()
        self.assertEqual(engine.time_left, 299)

    def _create_mock_app(self):
        app = OnekoCompanionApp.__new__(OnekoCompanionApp)
        app.config = self.config.copy()
        app.pomodoro = PomodoroEngine(app.config)
        app.pet_state = PetStateMachine()
        app.literary = MagicMock()
        app.literary.mode = "off"
        app.tray = MagicMock()
        app.update_window_shape_and_size = MagicMock()
        app.queue_draw = MagicMock()
        app.status_pill_timer = 0
        app.status_pill_text = None
        app.cat_x = 400.0
        app.cat_y = 300.0
        app.screen_w = 1920
        app.screen_h = 1080
        app.save_config = MagicMock()
        return app

    def test_e_celebration_exception_does_not_break_break_countdown(self):
        """
        Test E: MANDATORY REQUIREMENT:
        Focus completes -> BREAK -> celebration intentionally throws an exception.
        Expected: BREAK CONTINUES NORMALLY without interruption.
        """
        app = self._create_mock_app()

        # Mock celebration that raises an unhandled exception when triggered
        app.celebration = MagicMock()
        app.celebration.start.side_effect = RuntimeError("SIMULATED CELEBRATION CRASH!")

        app.pomodoro.start_focus()
        app.pomodoro.time_left = 1

        # Trigger tick that finishes focus
        # on_second_tick must catch the celebration error, log BREAK CONTINUES,
        # and keep the break running.
        result = app.on_second_tick()
        self.assertTrue(result)

        # Assertions:
        # 1. Break was successfully entered
        self.assertEqual(app.pomodoro.phase, PomodoroPhase.BREAK)
        # 2. Break timer was set to 5 minutes (300s)
        self.assertEqual(app.pomodoro.time_left, 300)
        # 3. Pet state entered break mode
        self.assertTrue(app.pet_state.break_mode)
        self.assertEqual(app.pet_state.state, PetState.BREAK)

        # 4. Subsequent second ticks continue counting down normally
        app.on_second_tick()
        self.assertEqual(app.pomodoro.time_left, 299)
        app.on_second_tick()
        self.assertEqual(app.pomodoro.time_left, 298)

    def test_f_celebration_lifecycle_and_anti_duplication(self):
        """Test F: 60-second celebration lifecycle and anti-duplication state lock."""
        mgr = CelebrationManager()
        self.assertEqual(mgr.state, CelebrationState.IDLE)
        self.assertFalse(mgr.is_active())

        # First start succeeds
        started = mgr.start()
        self.assertTrue(started)
        self.assertEqual(mgr.state, CelebrationState.RUNNING)
        self.assertTrue(mgr.is_active())
        self.assertGreaterEqual(len(mgr.guests), 3)

        # Anti-duplication: duplicate start requests MUST be rejected
        started_again = mgr.start()
        self.assertFalse(started_again)
        self.assertEqual(len(mgr.guests), 3)

        # Test phase transitions over time
        # Phase 1: 0–15s (ARRIVING)
        mgr.elapsed = 5.0
        self.assertEqual(mgr.get_phase(), CelebrationPhase.ARRIVING)

        # Phase 2: 15–30s (PEAK)
        mgr.elapsed = 20.0
        self.assertEqual(mgr.get_phase(), CelebrationPhase.PEAK)

        # Phase 3: 30–45s (SETTLING)
        mgr.elapsed = 35.0
        self.assertEqual(mgr.get_phase(), CelebrationPhase.SETTLING)

        # Phase 4: 45–60s (LEAVING)
        mgr.elapsed = 50.0
        self.assertEqual(mgr.get_phase(), CelebrationPhase.LEAVING)

        # At 60s: Step completes and cleans up
        mgr.step(15.0)  # Advances elapsed to 65.0s -> triggers finish()
        self.assertEqual(mgr.state, CelebrationState.COMPLETE)
        self.assertEqual(len(mgr.guests), 0)
        self.assertFalse(mgr.is_active())

    def test_g_session_reset_and_simulated_completion_hook(self):
        """Test G: Authoritative reset_session and simulate_focus_completion."""
        app = self._create_mock_app()
        app.celebration = CelebrationManager(app)

        # Start simulated focus
        app.simulate_focus_completion()
        self.assertEqual(app.pomodoro.phase, PomodoroPhase.FOCUS)
        self.assertEqual(app.pomodoro.time_left, 1)

        # One tick triggers completion and break
        app.on_second_tick()
        self.assertEqual(app.pomodoro.phase, PomodoroPhase.BREAK)
        self.assertEqual(app.pomodoro.time_left, 300)

        # Reset session
        app.reset_session()
        self.assertEqual(app.pomodoro.phase, PomodoroPhase.IDLE)
        self.assertEqual(app.pomodoro.time_left, 45 * 60)
        self.assertFalse(app.pet_state.break_mode)
        self.assertFalse(app.pet_state.focus_mode)
        self.assertEqual(app.celebration.state, CelebrationState.IDLE)


if __name__ == "__main__":
    unittest.main()
