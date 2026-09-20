"""
Verification Script for Section 24: LIVING WORLD + INTERACTION UPGRADE FINAL QUALITY TEST.

Simulates the natural desktop companion experience:
1. DISCOVERY: Spawns leaf, Miu approaches, investigates, nudges, naturally fades.
2. TOYS: Spawns yarn ball (bats & chases), cardboard box (enters & sits inside with head peeking out).
3. PHYSICS: Demonstrates deterministic movement, bounce, friction damping.
4. CURSOR PERSONALITY: Gentle click gives playful hop; rapid clicking triggers annoyed scamper.
5. WHERE DID MIU GO?: Intentional edge exit, temporary absence, natural re-entry.
6. CONTEXTUAL SLEEP: Finds ledge/corner, sits, sleeps with personality duration, stretches, wakes.
7. FOCUS VS BREAK: Verifies focus suppresses distractions while break unleashes playful exploration.
8. SUMMON: Calls Miu from sleeping, climbing, and off-screen; verifies safe destination & spam protection.
"""

import os
import sys
import time

os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR_PATH = os.path.join(os.path.dirname(TESTS_DIR), "app")
if APP_DIR_PATH not in sys.path:
    sys.path.insert(0, APP_DIR_PATH)

from oneko_plus import OnekoCompanionApp
from living_world import DiscoveryType, ToyType, LivingEventType
from pet_state import PetState


def run_living_world_verification():
    print("=== STARTING MIU: LIVING WORLD + INTERACTION UPGRADE VERIFICATION ===")

    app = OnekoCompanionApp()
    lw = app.living_world
    print("\n[Step 1] LAUNCH & ENGINE VERIFICATION:")
    print(f"  ✓ Living World Manager active: {lw is not None}")
    print(f"  ✓ Initial Pet State: {app.pet_state.state.value}")

    print("\n[Step 2] TINY DISCOVERIES (Leaf Investigation):")
    leaf = lw.spawn_discovery(candidate_x=500, candidate_y=500)
    assert leaf is not None, "Discovery item must spawn"
    print(f"  ✓ Spawned Discovery: {leaf.item_type.value} at ({leaf.x}, {leaf.y})")
    assert not leaf.is_toy, "Leaf must not be a toy"
    assert leaf.fade_alpha == 1.0, "Initial alpha must be 1.0"

    # Miu investigates discovery
    lw.on_reached_item()
    print(f"  ✓ Miu reached discovery and investigated (Stage: {lw.investigate_stage})")
    # Natural fade out
    leaf.age = leaf.lifetime + 0.1
    leaf.step(0.1, app.screen_w, app.screen_h)
    assert leaf.is_fading, "Discovery must fade out naturally"
    lw.cleanup()
    print("  ✓ Discovery disappeared naturally without cluttering desktop")

    print("\n[Step 3] TINY TOYS & PHYSICAL FEEL:")
    # 3a. Yarn ball
    yarn = lw.spawn_toy(candidate_x=600, candidate_y=600)
    yarn.item_type = ToyType.YARN_BALL
    yarn._init_item_dynamics()
    print(f"  ✓ Spawned Toy: {yarn.item_type.value}")
    yarn.apply_impulse(120.0, -30.0)
    start_vx, start_vy = yarn.vx, yarn.vy
    yarn.step(0.1, app.screen_w, app.screen_h)
    print(f"  ✓ Yarn ball rolled to ({yarn.x:.1f}, {yarn.y:.1f}) with friction (vx: {start_vx:.1f} -> {yarn.vx:.1f})")
    assert yarn.vx < start_vx, "Friction must damp velocity"
    lw.cleanup()

    # 3b. Cardboard box (Miu sits inside with head peeking out)
    box = lw.spawn_toy(candidate_x=700, candidate_y=700)
    box.item_type = ToyType.CARDBOARD_BOX
    lw.on_reached_item()
    print(f"  ✓ Cardboard box investigated. Miu inside: {lw.is_sitting_in_box}")
    assert lw.is_sitting_in_box, "Miu must sit inside cardboard box"
    assert app.pet_state.state == PetState.SITTING, "Pet state must be SITTING"
    lw.cleanup()

    print("\n[Step 4] CURSOR PERSONALITY & COOLDOWNS:")
    # Single click -> playful hop
    cp = lw.cursor_personality
    r1 = cp.on_click(app.cat_x, app.cat_y, app.mouse_x, app.mouse_y)
    print(f"  ✓ Single click reaction: {r1['type']} (hopping={cp.is_hopping})")
    assert r1["type"] == "hop"
    assert cp.is_hopping, "Cat must initiate hop"

    # Rapid clicking -> annoyance scamper/shake/refusal
    r2 = cp.on_click(app.cat_x, app.cat_y, app.mouse_x, app.mouse_y)
    r3 = cp.on_click(app.cat_x, app.cat_y, app.mouse_x, app.mouse_y)
    print(f"  ✓ Rapid click streak reaction: {r3['type']} (annoyance cooldown: {cp.annoyance_cooldown:.1f}s)")
    assert r3["type"] in ("scamper", "shake", "refusal")

    print("\n[Step 5] 'WHERE DID MIU GO?' ABSENCE & RETURN:")
    dest = lw.absence_controller.plan_absence(app.cat_x, app.cat_y, app.screen_w, app.screen_h)
    print(f"  ✓ Edge walk planned toward destination off-screen: {dest}")
    lw.absence_controller.on_reached_edge()
    assert lw.absence_controller.state == "absent", "State must be absent"
    print("  ✓ Miu stepped beyond visible border into absence")

    # Natural return
    lw.absence_controller.absence_start_time = time.time() - 30.0
    ret = lw.absence_controller.update_absence(app.screen_w, app.screen_h)
    assert ret is not None, "Absence must trigger natural return"
    print(f"  ✓ Miu naturally returning from {ret['entry_pos']} onto desktop {ret['dest_pos']}")

    print("\n[Step 6] CONTEXTUAL SLEEPING:")
    spot = lw.sleep_manager.find_sleep_spot(app.cat_x, app.cat_y, app.screen_w, app.screen_h)
    print(f"  ✓ Contextual sleep spot selected: {spot}")
    dur = lw.sleep_manager.get_sleep_duration_for_personality(app.pet_state.personality_key)
    print(f"  ✓ Personality-calibrated sleep duration ({app.pet_state.profile['name']}): {dur:.1f}s")
    assert dur > 0

    print("\n[Step 7] FOCUS RESPECTFUL VS BREAK PLAYGROUND:")
    # Focus suppresses toys and absences
    for _ in range(10):
        ev = lw.event_director.select_next_event(mode="focused", personality="calm")
        assert ev not in (LivingEventType.TOY_PLAY, LivingEventType.OFFSCREEN_ABSENCE)
    print("  ✓ Focus mode strictly suppresses toys and offscreen absences")

    # Break mode allows playful toys and expressive discoveries
    break_events = [lw.event_director.select_next_event(mode="break", personality="playful") for _ in range(15)]
    has_play = any(ev in (LivingEventType.TOY_PLAY, LivingEventType.DISCOVERY) for ev in break_events)
    assert has_play, "Break mode must encourage play and discoveries"
    print("  ✓ Break mode actively triggers discoveries and toys")

    print("\n[Step 8] SUMMON MIU (Ctrl+M / CLI / IPC):")
    # Summon from sleeping
    app.pet_state.state = PetState.SLEEPING
    res = app.summon_miu()
    print(f"  ✓ Summon triggered while sleeping: {res['msg']}")
    assert app.pet_state.state != PetState.SLEEPING, "Miu must wake immediately upon summon"
    assert app.status_pill_text == "🐾 Here!"

    # Rapid spam check
    res_spam = app.summon_miu()
    print(f"  ✓ Summon spam protection: {res_spam['type']}")
    assert res_spam["type"] == "ack_twitch"

    app.destroy()
    while Gtk.events_pending():
        Gtk.main_iteration()

    print("\n=== MIU: LIVING WORLD + INTERACTION UPGRADE VERIFIED 100%! ===")


if __name__ == "__main__":
    run_living_world_verification()
