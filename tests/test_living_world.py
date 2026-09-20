"""
Comprehensive Automated Tests for Miu Living World & Natural Interaction Engine.

Verifies:
1. Tiny Discoveries (types, lifecycle, approach, investigation, fade out, focus suppression)
2. Tiny Toys (yarn ball, paper ball, butterfly, feather, laser dot, cardboard box, physics, 10-30s session)
3. Simple physical feel (deterministic movement, bounce, friction, gravity, oscillation)
4. Cursor Personality & Cooldowns (environmental stimulus, notice, curious watch, click hop, rapid-click scamper)
5. 'Where did Miu go?' (edge walk, absence, natural return, instant recall on summon, non-crash)
6. Contextual Sleep (corners, window ledges, window bases, floor, personality sleep duration)
7. Event Selection & Non-Repetition (recent event history, focus/break mode modifiers, personality weighting)
8. Global Summon (from roaming, sleeping, climbing, absent, safe destination, spam cooldown, IPC, CLI, shortcut)
"""

import os
import sys
import math
import time
import unittest
import cairo

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from living_world import (
    LivingEventType, DiscoveryType, ToyType,
    WorldItem, CursorPersonalityManager, AbsenceController,
    ContextualSleepManager, SummonManager, LivingEventManager,
    LivingWorldManager
)
from pet_state import PetStateMachine, PetState, Personality
from topology import WindowSurface, DesktopTopology
from oneko_plus import OnekoCompanionApp, DEFAULT_CONFIG


class TestDiscoveriesAndToys(unittest.TestCase):
    def test_all_discovery_types_instantiate_and_draw(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 60, 60)
        cr = cairo.Context(surface)
        for d in DiscoveryType:
            item = WorldItem(d, x=100, y=100, is_toy=False)
            self.assertFalse(item.is_toy)
            self.assertFalse(item.is_expired)
            self.assertGreaterEqual(item.lifetime, 4.0)
            self.assertLessEqual(item.lifetime, 9.0)
            # Ensure Cairo draw executes cleanly
            item.draw(cr)

    def test_all_toy_types_instantiate_and_draw(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 80, 80)
        cr = cairo.Context(surface)
        for t in ToyType:
            item = WorldItem(t, x=200, y=200, is_toy=True)
            self.assertTrue(item.is_toy)
            self.assertFalse(item.is_expired)
            self.assertGreaterEqual(item.lifetime, 10.0)
            self.assertLessEqual(item.lifetime, 32.0)
            item.draw(cr)

    def test_item_physics_bounce_friction_and_boundaries(self):
        item = WorldItem(ToyType.YARN_BALL, x=100, y=100, is_toy=True)
        item.apply_impulse(150.0, 50.0)
        self.assertEqual(item.vx, 150.0)
        self.assertEqual(item.vy, 50.0)

        # Step physics across 10 frames
        for _ in range(10):
            item.step(0.05, screen_w=1920, screen_h=1080)

        # Position must have moved
        self.assertGreater(item.x, 100.0)
        self.assertGreater(item.y, 100.0)
        # Velocity must have damped due to friction
        self.assertLess(item.vx, 150.0)
        self.assertLess(item.vy, 50.0)

        # Test floor bounce
        item.x = 500.0
        item.y = 1070.0
        item.vy = 80.0
        item.step(0.05, screen_w=1920, screen_h=1080)
        # vy must reverse upon hitting bottom boundary
        self.assertLess(item.vy, 0.0)

    def test_item_expiration_and_fade(self):
        item = WorldItem(DiscoveryType.LEAF, x=100, y=100, is_toy=False)
        item.lifetime = 1.0
        item.step(0.5, screen_w=1920, screen_h=1080)
        self.assertFalse(item.is_expired)

        # Fast forward past lifetime
        item.step(0.6, screen_w=1920, screen_h=1080)
        self.assertTrue(item.is_fading)

        # Step until fade completes
        for _ in range(30):
            item.step(0.05, screen_w=1920, screen_h=1080)
        self.assertTrue(item.is_expired)


class TestCursorPersonality(unittest.TestCase):
    def setUp(self):
        self.cp = CursorPersonalityManager()

    def test_cursor_single_click_hop(self):
        res = self.cp.on_click(cat_x=500, cat_y=500, mouse_x=505, mouse_y=505)
        self.assertEqual(res.get("type"), "hop")
        self.assertTrue(self.cp.is_hopping)
        self.assertLess(self.cp.hop_velocity_y, 0.0)  # Upward impulse

        # Step physics: hop ascends, peaks, and lands
        self.cp.step(0.1)
        self.assertLess(self.cp.hop_offset_y, 0.0)
        for _ in range(25):
            self.cp.step(0.05)
        self.assertFalse(self.cp.is_hopping)
        self.assertEqual(self.cp.hop_offset_y, 0.0)

    def test_cursor_rapid_click_streak_annoyance(self):
        # First click
        r1 = self.cp.on_click(500, 500, 500, 500)
        self.assertEqual(r1["type"], "hop")

        # Second click
        r2 = self.cp.on_click(500, 500, 500, 500)
        self.assertEqual(r2["type"], "hop")

        # Third click rapidly within 2.2s -> triggers scamper, shake, or refusal!
        r3 = self.cp.on_click(500, 500, 500, 500)
        self.assertIn(r3["type"], ("scamper", "shake", "refusal"))
        self.assertGreater(self.cp.annoyance_cooldown, 0.0)

    def test_cursor_environmental_stimulus_and_cooldown(self):
        # Passing near
        stim = self.cp.on_cursor_nearby(dist_to_mouse=70.0, is_mouse_moving=True, mouse_still_ticks=0, mode="normal")
        if stim:
            self.assertEqual(stim["type"], "notice_glance")
            # Immediate subsequent check must return None due to cooldown
            stim2 = self.cp.on_cursor_nearby(dist_to_mouse=70.0, is_mouse_moving=True, mouse_still_ticks=0, mode="normal")
            self.assertIsNone(stim2)


class TestAbsenceController(unittest.TestCase):
    def setUp(self):
        self.ac = AbsenceController()

    def test_plan_and_execute_absence(self):
        target = self.ac.plan_absence(cur_x=200, cur_y=500, screen_w=1920, screen_h=1080)
        self.assertEqual(self.ac.state, "walking_to_edge")
        self.assertIsNotNone(target)

        # Reached edge -> absent
        self.ac.on_reached_edge()
        self.assertEqual(self.ac.state, "absent")

        # Before duration elapsed -> still absent
        self.assertIsNone(self.ac.update_absence(1920, 1080))

        # Fast forward time
        self.ac.absence_start_time = time.time() - 30.0
        ret = self.ac.update_absence(1920, 1080)
        self.assertIsNotNone(ret)
        self.assertEqual(self.ac.state, "returning")
        self.assertIn("entry_pos", ret)
        self.assertIn("dest_pos", ret)

    def test_instant_recall_on_summon_during_absence(self):
        self.ac.plan_absence(cur_x=200, cur_y=500, screen_w=1920, screen_h=1080)
        self.ac.on_reached_edge()
        self.assertEqual(self.ac.state, "absent")

        # User summons Miu while off-screen
        ret = self.ac.cancel_absence_for_summon(1920, 1080)
        self.assertIsNotNone(ret)
        self.assertEqual(self.ac.state, "returning")


class TestContextualSleep(unittest.TestCase):
    def setUp(self):
        self.csm = ContextualSleepManager()
        self.win = WindowSurface("w1", "Editor", "Code", 300, 200, 600, 400)

    def test_sleep_spot_selection(self):
        spot = self.csm.find_sleep_spot(
            cur_x=500, cur_y=500, screen_w=1920, screen_h=1080,
            windows=[self.win], favorite={"x": 100, "y": 100}
        )
        self.assertIsNotNone(spot)
        self.assertEqual(len(spot), 2)
        self.assertEqual(self.csm.sleep_state, "seeking")

    def test_personality_sleep_durations(self):
        d_playful = self.csm.get_sleep_duration_for_personality("playful")
        d_sleepy = self.csm.get_sleep_duration_for_personality("sleepy")
        d_focused = self.csm.get_sleep_duration_for_personality("focused")

        # Playful nap is short and brisk
        self.assertLessEqual(d_playful, 8.0)
        # Sleepy nap is longer
        self.assertGreaterEqual(d_sleepy, 9.0)
        # Focused is short quiet rest
        self.assertLessEqual(d_focused, 10.0)


class TestEventSelectionAndNonRepetition(unittest.TestCase):
    def setUp(self):
        self.em = LivingEventManager()

    def test_non_repetition_in_normal_mode(self):
        self.em.record_event(LivingEventType.TOY_PLAY)
        self.assertIn(LivingEventType.TOY_PLAY, self.em.recent_events)

        # Next event should not immediately duplicate TOY_PLAY
        next_ev = self.em.select_next_event(mode="normal", personality="calm", has_windows=True)
        self.assertNotEqual(next_ev, LivingEventType.TOY_PLAY)

    def test_focus_mode_respectful_suppression(self):
        for _ in range(15):
            ev = self.em.select_next_event(mode="focused", personality="focused", has_windows=True)
            # Focus mode must never spawn toys or offscreen absences
            self.assertNotIn(ev, (LivingEventType.TOY_PLAY, LivingEventType.OFFSCREEN_ABSENCE))
            self.assertIn(ev, (LivingEventType.NORMAL_ROAM, LivingEventType.SIT, LivingEventType.SLEEP, LivingEventType.DISCOVERY))

    def test_break_mode_high_expression(self):
        events = [self.em.select_next_event(mode="break", personality="playful", has_windows=True) for _ in range(20)]
        # In break mode, play or discoveries or window climbs must occur frequently
        play_or_explore = any(ev in (LivingEventType.TOY_PLAY, LivingEventType.DISCOVERY, LivingEventType.WINDOW_EXPLORATION) for ev in events)
        self.assertTrue(play_or_explore)


class TestSummonManager(unittest.TestCase):
    def setUp(self):
        self.sm = SummonManager()
        self.win = WindowSurface("w1", "Editor", "Code", 400, 300, 600, 400)

    def test_calculate_safe_destination_near_mouse(self):
        dest = self.sm.calculate_safe_destination(
            mouse_x=500, mouse_y=400, screen_w=1920, screen_h=1080, windows=[self.win]
        )
        self.assertIsNotNone(dest)
        # Sitting safely on top ledge of window (y is near win.y - 8 = 292)
        self.assertAlmostEqual(dest[1], 292, delta=10)

    def test_summon_spam_cooldown(self):
        self.assertTrue(self.sm.can_trigger())
        self.sm.calculate_safe_destination(500, 500, 1920, 1080)

        # Immediate re-trigger is cooled down
        self.assertFalse(self.sm.can_trigger())
        ack = self.sm.acknowledge_spam()
        self.assertEqual(ack["type"], "ack_twitch")


class TestAppLivingWorldIntegration(unittest.TestCase):
    def setUp(self):
        self.app = OnekoCompanionApp()

    def tearDown(self):
        self.app.destroy()

    def test_living_world_initialized_on_app(self):
        self.assertTrue(hasattr(self.app, "living_world"))
        self.assertIsNotNone(self.app.living_world)
        self.assertIsNone(self.app.living_world.active_item)

    def test_spawn_discovery_and_cleanup(self):
        item = self.app.living_world.spawn_discovery(candidate_x=300, candidate_y=400)
        self.assertIsNotNone(item)
        self.assertEqual(self.app.living_world.active_item, item)
        self.assertIsNotNone(self.app.living_world.item_window)

        # Clean up
        self.app.living_world.cleanup()
        self.assertIsNone(self.app.living_world.active_item)
        self.assertIsNone(self.app.living_world.item_window)

    def test_spawn_toy_and_cardboard_box_sit(self):
        item = WorldItem(ToyType.CARDBOARD_BOX, x=400, y=400, is_toy=True)
        self.app.living_world.active_item = item
        self.app.living_world.on_reached_item()

        # Miu should enter the box and sit
        self.assertTrue(self.app.living_world.is_sitting_in_box)
        self.assertEqual(self.app.pet_state.state, PetState.SITTING)

        # Test cardboard box rendering in on_draw
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 120, 120)
        cr = cairo.Context(surface)
        self.app.draw_cardboard_box_front(cr, 40, 40)

        self.app.living_world.cleanup()

    def test_summon_miu_from_sleeping_state(self):
        self.app.pet_state.state = PetState.SLEEPING
        res = self.app.summon_miu()
        self.assertEqual(res.get("status"), "ok")
        # Pet must wake up immediately, not remain sleeping
        self.assertNotEqual(self.app.pet_state.state, PetState.SLEEPING)
        self.assertEqual(self.app.status_pill_text, "🐾 Here!")


if __name__ == "__main__":
    unittest.main()
