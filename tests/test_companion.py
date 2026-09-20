"""
Comprehensive automated tests for Oneko Desktop Companion.
Verifies:
- Pomodoro engine (45-minute default, cycles, stats)
- Literary engine (strict one-line limit, works formatting, save/next/close)
- Pet state machine (personalities, states, focus/break transitions)
- Cosmetics & rendering pipeline (themes, accessories, expressions)
"""

import os
import sys
import unittest
import cairo

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(TESTS_DIR)
APP_DIR = os.path.join(PACKAGE_DIR, "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from paths import SPRITE_FILE, LITERATURE_DIR
from pomodoro import PomodoroEngine, PomodoroPhase
from literary import LiteraryEngine
from pet_state import PetStateMachine, PetState, Personality
from cosmetics import SpriteManager, CosmeticManager, COSMETIC_CATALOG


class TestPomodoroEngine(unittest.TestCase):
    def test_default_duration_is_45_min(self):
        engine = PomodoroEngine()
        self.assertEqual(engine.focus_duration_min, 45)
        self.assertEqual(engine.time_left, 45 * 60)
        self.assertEqual(engine.get_time_string(), "45:00")

    def test_focus_cycle_transitions(self):
        engine = PomodoroEngine()
        engine.start_focus()
        self.assertEqual(engine.phase, PomodoroPhase.FOCUS)

        # Pause and resume
        engine.pause()
        self.assertEqual(engine.phase, PomodoroPhase.PAUSED)
        engine.resume()
        self.assertEqual(engine.phase, PomodoroPhase.FOCUS)

        # Fast-forward to end of focus session
        engine.time_left = 1
        changed, event = engine.tick()
        self.assertTrue(changed)
        self.assertEqual(event, "focus_finished")
        self.assertEqual(engine.phase, PomodoroPhase.BREAK)
        self.assertEqual(engine.time_left, engine.short_break_min * 60)

        # End of short break
        engine.time_left = 1
        changed, event = engine.tick()
        self.assertTrue(changed)
        self.assertEqual(event, "break_finished")
        self.assertEqual(engine.phase, PomodoroPhase.FOCUS)

    def test_reset_and_skip(self):
        engine = PomodoroEngine()
        engine.start_focus()
        engine.time_left = 1200
        engine.reset()
        self.assertEqual(engine.phase, PomodoroPhase.IDLE)
        self.assertEqual(engine.time_left, 45 * 60)

        engine.start_focus()
        engine.skip()
        self.assertEqual(engine.phase, PomodoroPhase.BREAK)

    def test_stats_tracking(self):
        engine = PomodoroEngine()
        engine.start_focus()
        engine.time_left = 1
        engine.tick()
        summary = engine.get_stats_summary()
        self.assertGreaterEqual(summary["sessions"], 1)


class TestLiteraryEngine(unittest.TestCase):
    def setUp(self):
        self.engine = LiteraryEngine(LITERATURE_DIR)

    def test_strict_one_line_rule_all_works(self):
        self.assertGreater(len(self.engine.works), 50)
        for i, work in enumerate(self.engine.works):
            text = work["text"]
            author = work["author"]
            self.assertTrue(text, f"Work #{i} has empty text")
            self.assertTrue(author, f"Work #{i} has empty author")
            self.assertNotIn("\n", text, f"Work #{i} violates one-line rule: contains newline")
            self.assertNotIn("\r", text, f"Work #{i} violates one-line rule: contains carriage return")
            # Text should be concise (a single quote sentence/line)
            self.assertLess(len(text.split(".")), 6, f"Work #{i} seems too long: {text}")

    def test_actions_save_next_dismiss(self):
        work1 = self.engine.trigger_drop()
        self.assertTrue(self.engine.is_active)
        self.assertIsNotNone(work1)

        # Save
        saved = self.engine.save_current()
        self.assertTrue(saved)
        self.assertTrue(self.engine.is_current_saved())

        # Next
        work2 = self.engine.next_drop()
        self.assertIsNotNone(work2)

        # Dismiss
        self.engine.dismiss()
        self.assertFalse(self.engine.is_active)


class TestPetState(unittest.TestCase):
    def test_personalities_exist_and_differ(self):
        keys = ["calm", "playful", "sleepy", "energetic", "focused"]
        speeds = []
        for k in keys:
            p = Personality.get(k)
            self.assertIn("speed_mult", p)
            self.assertIn("chase_threshold_px", p)
            speeds.append(p["speed_mult"])

        # Speeds must not be all identical
        self.assertNotEqual(len(set(speeds)), 1)

    def test_state_machine_focus_and_break(self):
        sm = PetStateMachine(personality_key="focused")
        sm.set_focus_mode(True)
        self.assertEqual(sm.state, PetState.FOCUSED)

        # In focus mode, pet does not sprint wildly on mouse movement
        st = sm.update(dt=0.05, dist_to_target=60, is_mouse_moving=True)
        self.assertIn(st, (PetState.FOCUSED, PetState.CURIOUS, PetState.SITTING))

        sm.set_break_mode(True)
        self.assertEqual(sm.state, PetState.BREAK)

    def test_pet_interaction(self):
        sm = PetStateMachine()
        sm.pet_interaction()
        self.assertEqual(sm.state, PetState.HAPPY)


class TestCosmetics(unittest.TestCase):
    def setUp(self):
        self.sheet_path = SPRITE_FILE
        self.sprites = SpriteManager(self.sheet_path, scale=1.25, theme="classic")
        self.cosmetics = CosmeticManager()

    def test_all_themes_render_without_crash(self):
        for theme in COSMETIC_CATALOG["themes"]:
            theme_id = theme["id"]
            self.sprites.set_theme(theme_id)
            frame = self.sprites.get_frame("idle", 0)
            self.assertIsNotNone(frame)
            self.assertEqual(frame.get_width(), int(32 * 1.25))

    def test_all_accessories_and_expressions_cairo(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        cr = cairo.Context(surface)

        for acc in COSMETIC_CATALOG["accessories"]:
            acc_id = acc["id"]
            self.cosmetics.draw_accessory(cr, acc_id, "idle", 20, 20, 1.25)
            self.cosmetics.draw_accessory(cr, acc_id, "sleeping", 20, 20, 1.25)

        for exp in COSMETIC_CATALOG["expressions"]:
            exp_id = exp["id"]
            self.cosmetics.draw_expression(cr, exp_id, "idle", 20, 20, 1.25)


if __name__ == "__main__":
    unittest.main()
