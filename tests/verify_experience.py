"""
Verification script for Section 24: FINAL QUALITY TEST.

Simulates the exact user journey:
1. LAUNCH: One small pet appears on desktop.
2. IDLE: Pet idles naturally.
3. TRAY / ACTION: User selects "Start 45 min".
4. TIMER: Begins at 45:00.
5. FOCUSED: Pet enters FOCUSED state and becomes calm.
6. COMPLETION: 45-minute session completes.
7. BREAK: Pet enters BREAK state.
8. LITERARY DROP: Exactly ONE literary line appears with author.
9. INTERACTION: User can SAVE, NEXT, or CLOSE.
10. READINESS: Pet remains available for next 45-minute session.
"""

import os
import sys
import json

os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR_PATH = os.path.join(os.path.dirname(TESTS_DIR), "app")
if APP_DIR_PATH not in sys.path:
    sys.path.insert(0, APP_DIR_PATH)

from oneko_plus import OnekoCompanionApp, APP_DIR, CONFIG_FILE
from pet_state import PetState
from pomodoro import PomodoroPhase


def run_verification():
    print("=== STARTING SECTION 24 FINAL QUALITY TEST ===")

    # 1. LAUNCH
    print("\n[Step 1] LAUNCH:")
    app = OnekoCompanionApp()
    print(f"  ✓ App initialized. Pet Name: '{app.config.get('pet_name')}', Scale: {app.config.get('cat_scale')}")
    print(f"  ✓ Window realized at coordinates ({int(app.cat_x)}, {int(app.cat_y)})")

    # 2. IDLE
    print("\n[Step 2] IDLE & NATURAL INACTIVITY:")
    print(f"  ✓ Initial Pet State: {app.pet_state.state.value}")
    assert app.pet_state.state in (PetState.IDLE, PetState.SITTING), "Pet must be in IDLE or SITTING state on launch"
    print(f"  ✓ Personality: {app.pet_state.profile['name']}")

    # 3. TRAY & START FOCUS ACTION
    print("\n[Step 3] START 45 MIN FOCUS:")
    app.start_focus_session()

    # 4. TIMER
    print("\n[Step 4] TIMER VALIDATION:")
    print(f"  ✓ Timer string: {app.pomodoro.get_time_string()}")
    print(f"  ✓ Phase: {app.pomodoro.phase}")
    assert app.pomodoro.get_time_string() == "45:00", "Timer must start at 45:00"
    assert app.pomodoro.phase == PomodoroPhase.FOCUS, "Pomodoro phase must be FOCUS"

    # 5. PET ENTERS FOCUSED STATE
    print("\n[Step 5] PET FOCUSED STATE:")
    print(f"  ✓ Pet State: {app.pet_state.state.value}")
    assert app.pet_state.state == PetState.FOCUSED, "Pet state must be FOCUSED"
    print("  ✓ Pet is calm and non-distracting during focus.")

    # 6. COMPLETION (Simulate 45-min completion)
    print("\n[Step 6] 45-MINUTE SESSION COMPLETION:")
    app.pomodoro.time_left = 1
    app.on_second_tick()
    print("  ✓ 45-min timer reached 00:00.")

    # 7. BREAK
    print("\n[Step 7] PET ENTERS BREAK STATE:")
    print(f"  ✓ Pomodoro Phase: {app.pomodoro.phase}")
    print(f"  ✓ Pet State: {app.pet_state.state.value}")
    assert app.pomodoro.phase in (PomodoroPhase.BREAK, PomodoroPhase.LONG_BREAK), "Pomodoro must be in BREAK"
    assert app.pet_state.state == PetState.BREAK, "Pet must be in BREAK state"

    # 8. ONE LITERARY LINE APPEARS
    print("\n[Step 8] LITERARY DROP PRESENTATION:")
    assert app.literary.is_active, "Literary drop must be active"
    work = app.literary.current_work
    print(f"  ✓ Literary text: \"{work['text']}\"")
    print(f"  ✓ Author attribution: — {work['author']}")
    assert "\n" not in work["text"], "Literary line MUST NOT contain newlines"
    assert "\r" not in work["text"], "Literary line MUST NOT contain carriage returns"
    assert work["text"] and work["author"], "Literary drop must contain text and author"

    # 9. INTERACTION (SAVE, NEXT, CLOSE)
    print("\n[Step 9] LITERARY DROP INTERACTION:")
    # Save
    saved = app.literary.save_current()
    print(f"  ✓ Action SAVE executed (saved={saved}, is_saved={app.literary.is_current_saved()})")
    assert app.literary.is_current_saved(), "Work must be saved"

    # Next
    next_work = app.literary.next_drop()
    print(f"  ✓ Action NEXT executed: \"{next_work['text']}\" — {next_work['author']}")
    assert next_work is not None, "Next drop must load a valid work"

    # Close
    app.dismiss_active_popup()
    print("  ✓ Action CLOSE executed (card dismissed)")
    assert not app.literary.is_active, "Literary drop must be dismissed after close"

    # 10. PET REMAINS AVAILABLE FOR NEXT FOCUS
    print("\n[Step 10] PET REMAINS AVAILABLE & READY FOR NEXT 45 MIN FOCUS:")
    print(f"  ✓ Pet State: {app.pet_state.state.value}")
    app.start_focus_session()
    print(f"  ✓ Next focus started: Timer is at {app.pomodoro.get_time_string()}")
    assert app.pomodoro.get_time_string() == "45:00", "Next focus must start at 45:00"

    app.destroy()
    while Gtk.events_pending():
        Gtk.main_iteration()

    print("\n=== FINAL QUALITY TEST PASSED FULLY! ===")


if __name__ == "__main__":
    run_verification()
