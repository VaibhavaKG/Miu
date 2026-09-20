#!/usr/bin/env python3
"""
Oneko Desktop Companion - Evolved Minimal Desktop Pet.
One Pet + One 45-Minute Focus Session + One-Line Literary Drops + Deep Pet Customization.
"""

import os
import sys
import math
import time
import json
import random
import shutil
import signal
import subprocess

# Force X11 backend for GDK so absolute screen coordinates, pointer queries,
# and transparent overlays work flawlessly under GNOME / Xwayland on Fedora.
os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, PangoCairo
import cairo

from pet_state import PetStateMachine, PetState
from cosmetics import SpriteManager, CosmeticManager, COSMETIC_CATALOG
from pomodoro import PomodoroEngine, PomodoroPhase
from literary import LiteraryEngine
from tray import TrayManager
from preferences_dialog import PreferencesDialog
from ipc import MiuIPCServer
from topology import DesktopTopology, DestinationPicker
from living_world import LivingWorldManager, LivingEventType, DiscoveryType, ToyType
from celebration import CelebrationManager, CelebrationState

try:
    from paths import (
        ensure_user_dirs,
        USER_CONFIG_FILE,
        USER_LOG_FILE,
        SPRITE_FILE,
        CHIME_FILE,
        PURR_FILE,
        PACKAGE_DIR,
        LITERATURE_DIR,
        APP_DIR,
    )
    ensure_user_dirs()
    CONFIG_FILE = USER_CONFIG_FILE
    LOG_FILE = USER_LOG_FILE
except ImportError:
    APP_DIR = os.path.expanduser("~/.local/share/oneko-plus")
    CONFIG_FILE = os.path.join(APP_DIR, "config.json")
    SPRITE_FILE = os.path.join(APP_DIR, "oneko.gif")
    CHIME_FILE = os.path.join(APP_DIR, "chime.wav")
    PURR_FILE = os.path.join(APP_DIR, "purr.wav")
    LOG_FILE = os.path.join(APP_DIR, "miu.log")


def log_event(msg):
    print(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass

DEFAULT_CONFIG = {
    "pet_name": "Miu",
    "personality": "calm",          # "calm", "playful", "sleepy", "energetic", "focused"
    "cat_scale": 1.25,              # 1.0 = 32px, 1.25 = 40px, 1.5 = 48px
    "cat_theme": "classic",         # "classic", "ginger", "black", "sakura", "calico", "siamese", "tuxedo", "midnight_blue"
    "cat_accessory": "none",        # "none", "tophat", "wizard_hat", "beret", "bowtie", "scarf", "glasses", "flower", "crown", "party_hat"
    "cat_expression": "normal",     # "normal", "sparkle", "winking", "sleepy", "scholar"
    "movement_speed": "normal",     # "slow", "normal", "fast"
    "always_on_top": True,
    "pomodoro_enabled": False,      # Pomodoro is OPTIONAL — Miu is a companion first
    "badge_display": "always",      # "always", "hover", "hidden"
    "sound_enabled": True,
    "focus_duration_min": 45,       # EXACTLY 45 MINUTES BY DEFAULT
    "short_break_min": 5,
    "long_break_min": 15,
    "literary_mode": "breaks_only", # "breaks_only", "occasional", "off"
    "quote_interval_min": 15,
    "saved_quotes": [],
    "stats": {
        "date": "",
        "focus_sessions": 0,
        "focus_seconds": 0,
        "quotes_read": 0
    },
    "last_pos_x": -1,
    "last_pos_y": -1
}


def play_sound(sound_path, enabled=True):
    if not enabled or not os.path.exists(sound_path):
        return
    player = shutil.which("paplay") or shutil.which("pw-play") or shutil.which("aplay")
    if player:
        try:
            subprocess.Popen([player, sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


class Particle:
    def __init__(self, x, y, char="♥", color=(0.96, 0.25, 0.37)):
        self.x = x + random.uniform(-8, 8)
        self.y = y
        self.vy = random.uniform(-1.8, -2.8)
        self.vx = random.uniform(-0.5, 0.5)
        self.alpha = 1.0
        self.size = random.uniform(11, 15)
        self.char = char
        self.color = color

    def update(self):
        self.y += self.vy
        self.x += self.vx
        self.alpha -= 0.04
        return self.alpha > 0


class OnekoCompanionApp(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.load_config()

        self.set_title(f"Miu - {self.config.get('pet_name', 'Miu')}")
        self.set_role("miu-companion")
        self.set_app_paintable(True)
        self.set_keep_above(self.config.get("always_on_top", True))
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_decorated(False)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("key-press-event", self.on_key_press)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        self.connect("delete-event", lambda w, e: (self.quit_app(), True)[1])

        # Core engines
        self.sprites = SpriteManager(
            SPRITE_FILE,
            scale=self.config["cat_scale"],
            theme=self.config["cat_theme"]
        )
        self.cosmetics = CosmeticManager()
        self.pet_state = PetStateMachine(personality_key=self.config.get("personality", "calm"))
        self.pomodoro = PomodoroEngine(config=self.config)
        self.literary = LiteraryEngine(config=self.config)
        self.preferences_dialog = None
        self.home_window = None

        self.cat_pixel_size = int(32 * self.config["cat_scale"])
        self.speed = 10.0 * self.config["cat_scale"]

        display = Gdk.Display.get_default()
        self.seat = display.get_default_seat()
        self.update_screen_bounds()

        # Pet positioning
        saved_x = self.config.get("last_pos_x", -1)
        saved_y = self.config.get("last_pos_y", -1)
        if 20 <= saved_x <= self.screen_w - 20 and 20 <= saved_y <= self.screen_h - 20:
            self.cat_x = float(saved_x)
            self.cat_y = float(saved_y)
        else:
            self.cat_x = float(self.screen_w // 2)
            self.cat_y = float(self.screen_h // 2)

        self.mouse_x = self.cat_x
        self.mouse_y = self.cat_y
        self.last_mouse_x = self.mouse_x
        self.last_mouse_y = self.mouse_y
        self.mouse_still_ticks = 0

        # Animation states
        self.current_sprite = "idle"
        self.sprite_frame = 0
        self.step_counter = 0
        self.is_hovered = False

        # Dragging state
        self.is_dragging = False
        self.drag_potential = False
        self.drag_start_root_x = 0.0
        self.drag_start_root_y = 0.0
        self.cat_start_drag_x = 0.0
        self.cat_start_drag_y = 0.0

        # Desktop Topology & Autonomous Navigation
        self.topology = DesktopTopology(self.screen_w, self.screen_h)
        self.picker = DestinationPicker(self.topology)
        self.current_destination = None
        self.climb_mission = None
        self.climb_mission_index = 0
        self.climb_pause_timer = 0.0

        # Status / Feedback
        self.particles = []
        self.status_pill_text = None
        self.status_pill_timer = 0
        self.just_saved_notice = False

        # Window geometry
        self.win_w = self.cat_pixel_size + 36
        self.win_h = self.cat_pixel_size + 36
        self.win_x = int(self.cat_x - self.win_w // 2)
        self.win_y = int(self.cat_y - self.win_h // 2)
        self.quote_flipped = False
        self.quote_card_height = 96

        # Button bounds cache for literary card hit-testing: (btn_name, x1, y1, x2, y2)
        self.lit_buttons = []

        self.realize()
        self.update_window_shape_and_size()
        self.show_all()

        # Living World & Natural Interaction Engine
        self.living_world = LivingWorldManager(self)

        # 60-Second Celebration Subsystem
        self.celebration = CelebrationManager(self)

        # System tray & IPC Server
        self.tray = TrayManager(self)
        self.ipc_server = MiuIPCServer(self)

        # Timers
        GLib.timeout_add(50, self.on_animation_tick)
        GLib.timeout_add(1000, self.on_second_tick)

    def update_screen_bounds(self):
        screen = self.get_screen()
        self.screen_w = max(1024, screen.get_width())
        self.screen_h = max(768, screen.get_height())
        if hasattr(self, "topology") and self.topology:
            self.topology.update_screen_bounds(self.screen_w, self.screen_h)

    def load_config(self):
        self.config = dict(DEFAULT_CONFIG)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception:
                pass
        # Force default focus duration to 45 if it was the old default of 25
        if self.config.get("focus_duration_min") == 25:
            self.config["focus_duration_min"] = 45

    def save_config(self):
        try:
            self.config["stats"] = self.pomodoro.stats
            self.config["saved_quotes"] = self.literary.saved_works
            self.config["last_pos_x"] = int(self.cat_x)
            self.config["last_pos_y"] = int(self.cat_y)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Failed to save config:", e)

    def recenter_pet(self):
        self.cat_x = float(self.screen_w // 2)
        self.cat_y = float(self.screen_h // 2)
        self.current_destination = None
        self.climb_mission = None
        self.picker.record_destination(self.cat_x, self.cat_y)
        self.update_window_shape_and_size()
        self.save_config()
        self.queue_draw()

    def set_pet_paused(self, paused):
        self.pet_state.is_paused = paused
        if paused:
            self.status_pill_text = "🐾 Resting"
        else:
            self.status_pill_text = "🐾 Awake"
        self.status_pill_timer = 2
        self.tray.update_menu()
        self.update_window_shape_and_size()
        self.queue_draw()

    def start_focus_session(self):
        if hasattr(self, "celebration") and self.celebration:
            try:
                self.celebration.cleanup()
            except Exception:
                pass
        self.pomodoro.start_focus()
        self.pet_state.set_focus_mode(True)
        self.status_pill_text = f"🍅 {self.config.get('focus_duration_min', 45)} min Focus"
        self.status_pill_timer = 3
        play_sound(CHIME_FILE, self.config.get("sound_enabled", True))
        self.tray.update_menu()
        self.update_window_shape_and_size()
        self.queue_draw()

    def reset_session(self):
        """
        Authoritative session reset.
        Resets Pomodoro to IDLE (45:00), clears pet state, terminates
        any active celebration, dismisses popups, and updates UI.
        """
        self.pomodoro.reset()
        self.pet_state.set_break_mode(False)
        self.pet_state.set_focus_mode(False)
        self.pet_state.state = PetState.IDLE
        self.pet_state.current_action = None
        if hasattr(self, "celebration") and self.celebration:
            try:
                self.celebration.cleanup()
            except Exception:
                pass
        if hasattr(self, "literary"):
            try:
                self.literary.dismiss()
            except Exception:
                pass
        self.status_pill_text = None
        self.status_pill_timer = 0
        self.tray.update_menu()
        self.update_window_shape_and_size()
        self.queue_draw()

    def simulate_focus_completion(self):
        """
        Test hook: sets focus timer to 1s so the next second tick triggers focus completion.
        Does NOT alter the permanent 45-minute configuration.
        """
        if self.pomodoro.phase != PomodoroPhase.FOCUS:
            self.start_focus_session()
        self.pomodoro.time_left = 1

    def trigger_literary_drop(self):
        work = self.literary.trigger_drop()
        self.just_saved_notice = False
        self.measure_literary_card(work)
        self.update_window_shape_and_size()
        self.pomodoro.stats["quotes_read"] = self.pomodoro.stats.get("quotes_read", 0) + 1
        self.save_config()
        self.tray.update_menu()
        self.queue_draw()

    def measure_literary_card(self, work):
        if not work:
            return
        # Measure single-line text layout
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
        cr = cairo.Context(surface)
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription.from_string("Serif 11")
        layout.set_font_description(desc)
        layout.set_width(340 * Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD)
        layout.set_text(f"“{work['text']}”", -1)
        _, text_ext = layout.get_pixel_extents()

        # Generous whitespace for literary elegance
        self.quote_card_height = max(86, 68 + text_ext.height)

    def dismiss_active_popup(self):
        self.literary.dismiss()
        self.pet_state.curious_timer = 0
        self.current_sprite = "idle"
        self.update_window_shape_and_size()
        self.tray.update_menu()
        self.queue_draw()

    def open_preferences(self):
        if self.preferences_dialog:
            self.preferences_dialog.present()
        else:
            self.preferences_dialog = PreferencesDialog(self)
            self.preferences_dialog.connect("destroy", self._on_preferences_closed)

    def open_preferences_tab(self, tab_name):
        self.open_preferences()

    def open_home(self):
        if self.home_window:
            self.home_window.present()
        else:
            try:
                from miu_home import MiuHomeWindow
                self.home_window = MiuHomeWindow(self)
                self.home_window.connect("destroy", self._on_home_closed)
                self.home_window.show_all()
            except Exception as e:
                print(f"Failed to open Miu Home: {e}")

    def _on_home_closed(self, window):
        self.home_window = None
        self.tray.update_menu()
        self.update_window_shape_and_size()
        self.queue_draw()

    def _on_preferences_closed(self, dialog):
        self.preferences_dialog = None
        self.tray.update_menu()
        self.update_window_shape_and_size()
        self.queue_draw()

    def quit_app(self):
        if hasattr(self, "celebration") and self.celebration:
            self.celebration.cleanup()
        if hasattr(self, "living_world") and self.living_world:
            self.living_world.cleanup()
        if hasattr(self, "ipc_server") and self.ipc_server:
            self.ipc_server.stop()
        self.save_config()
        Gtk.main_quit()

    def summon_miu(self):
        """Summons Miu to user's active workspace or cursor area."""
        if hasattr(self, "living_world") and self.living_world:
            return self.living_world.handle_summon()
        return {"status": "ok", "msg": "Miu is on the way!"}

    def spawn_particles(self, char="♥", color=(0.96, 0.25, 0.37)):
        cat_draw_x, cat_draw_y = self.get_cat_draw_coords()
        scale = self.config.get("cat_scale", 1.25)
        for _ in range(4):
            self.particles.append(
                Particle(cat_draw_x + int(16 * scale), cat_draw_y + int(8 * scale), char=char, color=color)
            )

    def on_mouse_enter(self, widget, event):
        self.is_hovered = True
        self.queue_draw()

    def on_mouse_leave(self, widget, event):
        self.is_hovered = False
        self.queue_draw()

    def on_key_press(self, widget, event):
        # Global/Local summon shortcut: Ctrl + M
        state = event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK)
        if (state & Gdk.ModifierType.CONTROL_MASK) and event.keyval in (Gdk.KEY_m, Gdk.KEY_M):
            self.summon_miu()
            return True

        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_space, Gdk.KEY_Return):
            if self.literary.is_active:
                self.dismiss_active_popup()
                return True
        return False

    def on_button_press(self, widget, event):
        if event.button == 1:  # Left Click
            # Check if user clicked inside literary drop controls
            if self.literary.is_active:
                wx, wy = event.x, event.y
                for btn_id, x1, y1, x2, y2 in self.lit_buttons:
                    if x1 <= wx <= x2 and y1 <= wy <= y2:
                        if btn_id == "save":
                            saved = self.literary.save_current()
                            self.just_saved_notice = True
                            self.save_config()
                            self.tray.update_menu()
                            self.queue_draw()
                            return True
                        elif btn_id == "next":
                            work = self.literary.next_drop()
                            self.just_saved_notice = False
                            self.measure_literary_card(work)
                            self.update_window_shape_and_size()
                            self.pomodoro.stats["quotes_read"] = self.pomodoro.stats.get("quotes_read", 0) + 1
                            self.save_config()
                            self.tray.update_menu()
                            self.queue_draw()
                            return True
                        elif btn_id == "close":
                            self.dismiss_active_popup()
                            return True

            # Prepare for potential drag or pet click
            self.drag_potential = True
            self.is_dragging = False
            self.drag_start_root_x = event.x_root
            self.drag_start_root_y = event.y_root
            self.cat_start_drag_x = self.cat_x
            self.cat_start_drag_y = self.cat_y
            self.current_destination = None
            self.climb_mission = None
            return True

        elif event.button == 3:  # Right Click -> Context Menu
            self.tray.popup_context_menu(event)
            return True
        return False

    def on_motion_notify(self, widget, event):
        if self.drag_potential:
            dx = event.x_root - self.drag_start_root_x
            dy = event.y_root - self.drag_start_root_y
            if not self.is_dragging and math.hypot(dx, dy) > 4:
                self.is_dragging = True
                self.pet_state.is_dragged = True

            if self.is_dragging:
                self.cat_x = max(24.0, min(float(self.screen_w - 24), self.cat_start_drag_x + dx))
                self.cat_y = max(24.0, min(float(self.screen_h - 24), self.cat_start_drag_y + dy))
                self.update_window_shape_and_size()
                self.queue_draw()
                return True
        return False

    def on_button_release(self, widget, event):
        if event.button == 1:
            if self.is_dragging:
                # Finished dragging: save position
                self.is_dragging = False
                self.drag_potential = False
                self.pet_state.is_dragged = False
                self.picker.record_destination(self.cat_x, self.cat_y)
                self.pet_state.on_reached_destination(post_action="idle")
                self.save_config()
                self.queue_draw()
                return True
            elif self.drag_potential:
                self.drag_potential = False
                # If literary card was active and user clicked outside buttons, dismiss it
                if self.literary.is_active:
                    self.dismiss_active_popup()
                    return True

                # Cursor personality click reaction (hops, playful annoyance scamper, or gentle purr)
                if hasattr(self, "living_world") and self.living_world:
                    react = self.living_world.cursor_personality.on_click(
                        self.cat_x, self.cat_y, self.mouse_x, self.mouse_y
                    )
                    rtype = react.get("type")
                    if rtype == "scamper":
                        tx, ty = react["target"]
                        tx = max(30.0, min(float(self.screen_w - 30), tx))
                        ty = max(30.0, min(float(self.screen_h - 30), ty))
                        self.current_destination = {
                            "type": "walk",
                            "pos": (tx, ty),
                            "post_action": "sit"
                        }
                        self.pet_state.state = PetState.RUNNING
                        self.status_pill_text = "💨 Scamper!"
                        self.status_pill_timer = 2
                        self.update_window_shape_and_size()
                        self.queue_draw()
                        return True
                    elif rtype == "shake":
                        self.current_sprite = "alert"
                        self.pet_state.state = PetState.CURIOUS
                        self.status_pill_text = "🐾 *shake*"
                        self.status_pill_timer = 2
                        self.update_window_shape_and_size()
                        self.queue_draw()
                        return True
                    elif rtype == "refusal":
                        self.current_sprite = "tired"
                        self.pet_state.state = PetState.SITTING
                        self.status_pill_text = "🐾 *huff*"
                        self.status_pill_timer = 2
                        self.update_window_shape_and_size()
                        self.queue_draw()
                        return True

                # Gentle click pets the cat!
                self.pet_state.pet_interaction()
                self.spawn_particles("♥", (0.96, 0.25, 0.37))
                play_sound(PURR_FILE, self.config.get("sound_enabled", True))
                pet_name = self.config.get("pet_name", "Miu")
                time_str = self.pomodoro.get_time_string()
                self.status_pill_text = f"{pet_name} · {time_str}"
                self.status_pill_timer = 3
                self.update_window_shape_and_size()
                self.queue_draw()
                return True
        return False

    def on_second_tick(self):
        # 1. Pomodoro Tick (only when enabled or actively running)
        pomodoro_active = self.config.get("pomodoro_enabled", False) or self.pomodoro.phase != PomodoroPhase.IDLE
        if pomodoro_active:
            state_changed, event_type = self.pomodoro.tick()
            if state_changed:
                if event_type == "focus_finished":
                    log_event("FOCUS TIMER COMPLETE")
                    log_event("[MIU] FOCUS COMPLETE")
                    log_event("ENTERING BREAK")
                    log_event("[MIU] ENTERING BREAK")
                    self.pet_state.set_break_mode(True)
                    log_event(f"BREAK TIMER STARTED ({self.pomodoro.get_time_string()})")
                    log_event(f"[MIU] BREAK STARTED {self.pomodoro.time_left}s")

                    try:
                        play_sound(CHIME_FILE, self.config.get("sound_enabled", True))
                    except Exception as e:
                        log_event(f"[MIU] Audio failed: {e}")

                    self.tray.update_menu()
                    self.update_window_shape_and_size()
                    self.queue_draw()

                    # One-break = one literary drop!
                    if self.literary.mode != "off":
                        try:
                            self.trigger_literary_drop()
                        except Exception as e:
                            log_event(f"[MIU] Literary drop failed: {e}\n[MIU] BREAK CONTINUES")

                    # Trigger 60-second celebration (Fail-safe isolated)
                    log_event("CELEBRATION REQUESTED")
                    log_event("[MIU] CELEBRATION REQUESTED")
                    if hasattr(self, "celebration") and self.celebration:
                        try:
                            self.celebration.start()
                        except Exception as e:
                            log_event(f"[MIU] CELEBRATION FAILED: {e}\n[MIU] BREAK CONTINUES")

                elif event_type == "break_finished":
                    log_event("[MIU] BREAK FINISHED")
                    try:
                        play_sound(CHIME_FILE, self.config.get("sound_enabled", True))
                    except Exception as e:
                        log_event(f"[MIU] Audio failed: {e}")
                    self.pet_state.set_focus_mode(True)
                    if hasattr(self, "celebration") and self.celebration:
                        try:
                            self.celebration.cleanup()
                        except Exception:
                            pass
                    self.tray.update_menu()

            # Log break tick during break phases
            if self.pomodoro.phase in (PomodoroPhase.BREAK, PomodoroPhase.LONG_BREAK):
                log_event(f"[MIU] BREAK TICK {self.pomodoro.time_left}s")

        # 2. Literary Occasional Tick (if mode is occasional and user not in focus)
        in_focus = (self.pomodoro.phase == PomodoroPhase.FOCUS)
        if self.literary.tick_second(is_in_focus=in_focus):
            self.measure_literary_card(self.literary.current_work)
            self.update_window_shape_and_size()
            self.pomodoro.stats["quotes_read"] = self.pomodoro.stats.get("quotes_read", 0) + 1
            self.save_config()

        # 3. Status Pill decay
        if self.status_pill_timer > 0:
            self.status_pill_timer -= 1
            if self.status_pill_timer <= 0:
                self.status_pill_text = None
                self.update_window_shape_and_size()

        self.queue_draw()
        return True

    def _step_towards(self, target_x, target_y, is_climbing=False, side="left"):
        """
        Moves Miu towards (target_x, target_y) at effective speed.
        Updates self.cat_x, self.cat_y, window position, and directional/climbing sprite.
        Returns (arrived: bool, dist_remaining: float).
        """
        diff_x = target_x - self.cat_x
        diff_y = target_y - self.cat_y
        dist = math.hypot(diff_x, diff_y)

        speed = self.pet_state.get_effective_speed(self.speed, self.config.get("movement_speed", "normal"))

        if dist <= max(4.0, speed):
            self.cat_x = float(target_x)
            self.cat_y = float(target_y)
            self.win_x = int(self.cat_x - self.win_w // 2)
            self.win_y = int(self.cat_y - self.win_h // 2)
            self.move(self.win_x, self.win_y)
            self.queue_draw()
            return True, 0.0

        self.step_counter += 1
        step_dist = min(speed, dist)
        self.cat_x += (diff_x / dist) * step_dist
        self.cat_y += (diff_y / dist) * step_dist

        self.cat_x = max(20.0, min(float(self.screen_w - 20), self.cat_x))
        self.cat_y = max(20.0, min(float(self.screen_h - 20), self.cat_y))
        self.win_x = int(self.cat_x - self.win_w // 2)
        self.win_y = int(self.cat_y - self.win_h // 2)
        self.move(self.win_x, self.win_y)

        # Set sprite based on movement style
        if is_climbing:
            frame = (self.step_counter // 2) % 2
            if abs(diff_y) >= abs(diff_x):
                # Primarily vertical climb
                scratch_key = "scratchWallE" if side == "left" else "scratchWallW"
                if (self.step_counter // 4) % 2 == 0:
                    self.current_sprite = scratch_key
                    self.sprite_frame = frame
                else:
                    self.current_sprite = "N" if diff_y < 0 else "S"
                    self.sprite_frame = frame
            else:
                # Horizontal ledge traverse
                self.current_sprite = "E" if diff_x > 0 else "W"
                self.sprite_frame = frame
        else:
            # Standard 8-directional walking sprite
            direction = ""
            if diff_y / dist < -0.38:
                direction += "N"
            elif diff_y / dist > 0.38:
                direction += "S"

            if diff_x / dist < -0.38:
                direction += "W"
            elif diff_x / dist > 0.38:
                direction += "E"

            if not direction:
                direction = "E" if diff_x >= 0 else "W"

            self.current_sprite = direction if direction in self.sprites.cached_frames else "idle"
            self.sprite_frame = self.step_counter % 2

        self.queue_draw()
        return False, dist

    def on_animation_tick(self):
        dt = 0.05
        # Step living world physics, active items, and timers
        if hasattr(self, "living_world") and self.living_world:
            self.living_world.tick(dt)

        # Step 60-second celebration with fail-safe error isolation
        if hasattr(self, "celebration") and self.celebration:
            try:
                self.celebration.step(dt)
            except Exception as e:
                print(f"CELEBRATION FAILED: {e}\nBREAK CONTINUES")
                try:
                    self.celebration.cleanup()
                except Exception:
                    pass

        # Update particles
        if self.particles:
            self.particles = [p for p in self.particles if p.update()]
            self.queue_draw()

        # Query pointer position across screen
        pointer = self.seat.get_pointer()
        _, root_x, root_y = pointer.get_position()
        self.mouse_x = float(root_x)
        self.mouse_y = float(root_y)

        # Detect cursor motion
        mouse_dist_moved = math.hypot(self.mouse_x - self.last_mouse_x, self.mouse_y - self.last_mouse_y)
        is_mouse_moving = (mouse_dist_moved > 4.0)

        if not is_mouse_moving:
            self.mouse_still_ticks += 1
        else:
            self.mouse_still_ticks = 0

        self.last_mouse_x = self.mouse_x
        self.last_mouse_y = self.mouse_y

        # If dragging, cat position is locked to drag
        if self.is_dragging:
            return True

        # If literary drop is active, pet sits alert and companion stays still
        if self.literary.is_active:
            self.current_sprite = "alert"
            self.sprite_frame = 0
            self.queue_draw()
            return True

        # Compute distance to mouse
        dist_to_mouse = math.hypot(self.cat_x - self.mouse_x, self.cat_y - self.mouse_y)

        # 1. Cursor courtesy: if user is actively moving mouse nearby, Miu courteously steps aside
        should_evade = (
            dist_to_mouse < 55.0
            and is_mouse_moving
            and not self.is_hovered
            and not self.drag_potential
            and self.pet_state.happy_timer <= 0
        )
        if should_evade:
            self.climb_mission = None
            dx = self.cat_x - self.mouse_x
            dy = self.cat_y - self.mouse_y
            norm = math.hypot(dx, dy) or 1.0
            evade_dist = 90.0
            target_x = max(30.0, min(float(self.screen_w - 30), self.cat_x + (dx / norm) * evade_dist))
            target_y = max(30.0, min(float(self.screen_h - 30), self.cat_y + (dy / norm) * evade_dist))
            self.current_destination = {
                "type": "walk",
                "pos": (target_x, target_y),
                "post_action": "sit"
            }
            self.pet_state.state = PetState.RUNNING

        # 2. Climb mission execution
        if self.climb_mission:
            waypoints = self.climb_mission.get("waypoints", [])
            side = self.climb_mission.get("side", "left")
            if self.climb_mission_index < len(waypoints):
                wp = waypoints[self.climb_mission_index]
                action = wp.get("action", "walk")
                target_x, target_y = wp["pos"]

                if action == "ledge_pause":
                    self.pet_state.state = PetState.CURIOUS
                    self.current_sprite = "alert"
                    self.sprite_frame = 0
                    self.climb_pause_timer += dt
                    if self.climb_pause_timer >= 2.5:
                        self.climb_pause_timer = 0.0
                        self.climb_mission_index += 1
                    self.queue_draw()
                    return True
                else:
                    is_vertical = (action in ("climb_up", "climb_down"))
                    if is_vertical:
                        self.pet_state.state = PetState.CLIMBING
                    else:
                        self.pet_state.state = PetState.WALKING

                    arrived, _ = self._step_towards(target_x, target_y, is_climbing=is_vertical, side=side)
                    if arrived:
                        self.climb_mission_index += 1
                        if self.climb_mission_index >= len(waypoints):
                            self.climb_mission = None
                            self.climb_mission_index = 0
                            self.picker.record_destination(self.cat_x, self.cat_y)
                            self.pet_state.on_reached_destination(post_action="look")
                    return True
            else:
                self.climb_mission = None
                self.climb_mission_index = 0

        # 3. Roaming to current destination
        if self.current_destination:
            target_x, target_y = self.current_destination["pos"]
            post_action = self.current_destination.get("post_action", "idle")
            if self.pet_state.state not in (PetState.RUNNING, PetState.WALKING):
                self.pet_state.state = PetState.WALKING

            arrived, _ = self._step_towards(target_x, target_y, is_climbing=False)
            if arrived:
                self.current_destination = None
                self.picker.record_destination(self.cat_x, self.cat_y)
                if post_action == "investigate_item":
                    if hasattr(self, "living_world") and self.living_world:
                        self.living_world.on_reached_item()
                elif post_action == "edge_exit":
                    if hasattr(self, "living_world") and self.living_world:
                        self.living_world.absence_controller.on_reached_edge()
                    self.win_x = -300
                    self.win_y = -300
                    self.move(self.win_x, self.win_y)
                elif post_action == "sleep_sequence":
                    self.pet_state.state = PetState.SLEEPING
                    duration = 9.0
                    if hasattr(self, "living_world") and self.living_world:
                        duration = self.living_world.sleep_manager.get_sleep_duration_for_personality(
                            self.pet_state.personality_key
                        )
                    self.pet_state.next_idle_action_time = time.time() + duration
                    if not self.config.get("favorite_spot") and random.random() < 0.25:
                        self.config["favorite_spot"] = {"x": int(self.cat_x), "y": int(self.cat_y)}
                        self.save_config()
                elif post_action == "summon_arrival":
                    self.pet_state.state = PetState.HAPPY
                    self.pet_state.happy_timer = 1.5
                    self.spawn_particles("♥", (0.96, 0.40, 0.50))
                    play_sound(PURR_FILE, self.config.get("sound_enabled", True))
                else:
                    self.pet_state.on_reached_destination(post_action=post_action)
            return True

        # 4. Autonomous destination selection when ready
        mode = "normal"
        if self.pomodoro.phase == PomodoroPhase.FOCUS or self.pet_state.focus_mode:
            mode = "focused"
        elif self.pomodoro.phase in (PomodoroPhase.BREAK, PomodoroPhase.LONG_BREAK) or self.pet_state.break_mode:
            mode = "break"

        # Check cursor personality environmental stimulus if idle/sitting/focused
        if not self.current_destination and not self.climb_mission and hasattr(self, "living_world") and self.living_world:
            stimulus = self.living_world.cursor_personality.on_cursor_nearby(
                dist_to_mouse, is_mouse_moving, self.mouse_still_ticks, mode=mode
            )
            if stimulus:
                if stimulus["type"] == "notice_glance":
                    self.current_sprite = "alert"
                    self.pet_state.state = PetState.CURIOUS
                    self.pet_state.next_idle_action_time = time.time() + stimulus["duration"]
                    self.queue_draw()
                    return True
                elif stimulus["type"] == "watch_sit":
                    self.current_sprite = "alert"
                    self.pet_state.state = PetState.SITTING
                    self.pet_state.next_idle_action_time = time.time() + stimulus["duration"]
                    self.queue_draw()
                    return True

        if self.pet_state.should_pick_new_destination():
            # Check autonomous yarn ball spawn first
            if hasattr(self, "living_world") and self.living_world and hasattr(self.living_world, "yarn_controller"):
                if self.living_world.yarn_controller.can_spawn(mode=mode) and random.random() < 0.25:
                    item = self.living_world.spawn_yarn_ball()
                    if item:
                        self.current_destination = {
                            "type": "walk",
                            "pos": (item.x, item.y),
                            "post_action": "investigate_item"
                        }
                        self.pet_state.state = PetState.WALKING
                        return True

            # Check living world event selection!
            if hasattr(self, "living_world") and self.living_world:
                has_windows = bool(self.topology.get_climbable_windows())
                ev = self.living_world.event_director.select_next_event(
                    mode=mode,
                    personality=self.pet_state.personality_key,
                    has_windows=has_windows
                )
                if ev == LivingEventType.DISCOVERY:
                    item = self.living_world.spawn_discovery()
                    if item:
                        self.current_destination = {
                            "type": "walk",
                            "pos": (item.x, item.y),
                            "post_action": "investigate_item"
                        }
                        self.pet_state.state = PetState.WALKING
                        return True
                elif ev == LivingEventType.TOY_PLAY:
                    item = self.living_world.spawn_toy()
                    if item:
                        self.current_destination = {
                            "type": "walk",
                            "pos": (item.x, item.y),
                            "post_action": "investigate_item"
                        }
                        self.pet_state.state = PetState.WALKING
                        return True
                elif ev == LivingEventType.OFFSCREEN_ABSENCE:
                    self.living_world.execute_absence()
                    return True
                elif ev == LivingEventType.SLEEP:
                    self.living_world.execute_sleep()
                    return True

            target = self.picker.pick_next(self.cat_x, self.cat_y, self.mouse_x, self.mouse_y, mode=mode)
            if target:
                if target.get("type") == "climb":
                    self.climb_mission = target
                    self.climb_mission_index = 0
                    self.climb_pause_timer = 0.0
                    self.pet_state.state = PetState.WALKING
                else:
                    self.current_destination = target
                    self.pet_state.state = PetState.WALKING
                return True

        # 5. Idle / sitting / sleeping / happy animation updates
        new_state = self.pet_state.update(dt, dist_to_mouse, is_mouse_moving)

        if new_state == PetState.SLEEPING:
            self.current_sprite = "sleeping"
            self.step_counter += 1
            self.sprite_frame = (self.step_counter // 8) % 2
            self.queue_draw()
            return True

        elif new_state == PetState.STRETCHING:
            self.step_counter += 1
            self.current_sprite = "tired" if (self.step_counter // 15) % 2 == 0 else "scratchWallN"
            self.sprite_frame = (self.step_counter // 6) % 2
            self.queue_draw()
            return True

        elif new_state == PetState.CURIOUS:
            self.current_sprite = "alert"
            self.sprite_frame = 0
            self.queue_draw()
            return True

        elif new_state == PetState.HAPPY:
            self.current_sprite = "scratchSelf"
            self.step_counter += 1
            self.sprite_frame = (self.step_counter // 3) % 3
            self.queue_draw()
            return True

        elif new_state in (PetState.FOCUSED, PetState.SITTING, PetState.BREAK):
            self.current_sprite = "idle"
            self.sprite_frame = 0
            self.queue_draw()
            return True

        else:  # IDLE
            self.current_sprite = "idle"
            self.sprite_frame = 0
            self.queue_draw()
            return True

    def get_cat_draw_coords(self):
        cx = int(self.cat_x - self.win_x - self.cat_pixel_size // 2)
        cy = int(self.cat_y - self.win_y - self.cat_pixel_size // 2)
        if hasattr(self, "living_world") and self.living_world:
            cx += int(self.living_world.cursor_personality.shake_offset_x)
            cy += int(self.living_world.cursor_personality.hop_offset_y)
        return (cx, cy)

    def update_window_shape_and_size(self):
        has_literary = self.literary.is_active and self.literary.current_work
        has_pill = bool(self.status_pill_text)

        if has_literary:
            card_w = 370
            card_h = self.quote_card_height
            self.win_w = card_w + 30
            self.win_h = card_h + self.cat_pixel_size + 24

            if self.cat_y < self.win_h + 30:
                self.quote_flipped = True
                self.win_x = int(self.cat_x - self.win_w // 2)
                self.win_y = int(self.cat_y - 12)
            else:
                self.quote_flipped = False
                self.win_x = int(self.cat_x - self.win_w // 2)
                self.win_y = int(self.cat_y - self.win_h + self.cat_pixel_size // 2 + 10)

        elif has_pill:
            self.win_w = 240
            self.win_h = self.cat_pixel_size + 52
            self.quote_flipped = False
            self.win_x = int(self.cat_x - self.win_w // 2)
            self.win_y = int(self.cat_y - self.win_h + self.cat_pixel_size // 2 + 10)
        else:
            self.win_w = self.cat_pixel_size + 36
            self.win_h = self.cat_pixel_size + 36
            self.quote_flipped = False
            self.win_x = int(self.cat_x - self.win_w // 2)
            self.win_y = int(self.cat_y - self.win_h // 2)

        self.win_x = max(10, min(self.win_x, self.screen_w - self.win_w - 10))
        self.win_y = max(10, min(self.win_y, self.screen_h - self.win_h - 10))

        self.resize(self.win_w, self.win_h)
        self.move(self.win_x, self.win_y)

    def on_draw(self, widget, cr):
        # 1. Clear background to complete transparency
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # 2. Literary Drop Card (Strict One-Line, Minimal, Restrained)
        if self.literary.is_active and self.literary.current_work:
            self.draw_literary_card(cr)

        # 3. Status Pill
        elif self.status_pill_text:
            self.draw_status_pill(cr)

        # 4. Minimal Collar Timer Badge (only when Pomodoro is enabled or during active focus)
        badge_mode = self.config.get("badge_display", "always")
        pomodoro_active = self.config.get("pomodoro_enabled", False) or self.pomodoro.phase != PomodoroPhase.IDLE
        if pomodoro_active and (badge_mode == "always" or (badge_mode == "hover" and self.is_hovered)):
            self.draw_collar_badge(cr)

        # 5. Cat Sprite & Cosmetics
        cat_x, cat_y = self.get_cat_draw_coords()
        frame = self.sprites.get_frame(self.current_sprite, self.sprite_frame)
        Gdk.cairo_set_source_pixbuf(cr, frame, cat_x, cat_y)
        cr.paint()

        # Expression & Accessory layers
        scale = self.config.get("cat_scale", 1.25)
        self.cosmetics.draw_expression(
            cr,
            self.config.get("cat_expression", "normal"),
            self.current_sprite,
            cat_x, cat_y,
            scale
        )
        self.cosmetics.draw_accessory(
            cr,
            self.config.get("cat_accessory", "none"),
            self.current_sprite,
            cat_x, cat_y,
            scale
        )

        # 5b. Cardboard box front (if Miu is sitting inside the box)
        if hasattr(self, "living_world") and self.living_world and self.living_world.is_sitting_in_box:
            self.draw_cardboard_box_front(cr, cat_x, cat_y)

        # 6. Sleeping Zzz
        if self.current_sprite == "sleeping":
            self.draw_zzz(cr, cat_x, cat_y)

        # 7. Floating Particles
        for p in self.particles:
            cr.save()
            cr.set_source_rgba(p.color[0], p.color[1], p.color[2], p.alpha)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(p.size)
            cr.move_to(p.x, p.y)
            cr.show_text(p.char)
            cr.restore()

        return True

    def draw_cardboard_box_front(self, cr, cat_x, cat_y):
        scale = self.config.get("cat_scale", 1.25)
        bw = int(32 * scale)
        bh = int(14 * scale)
        bx = cat_x + (self.cat_pixel_size - bw) // 2
        by = cat_y + self.cat_pixel_size - bh
        cr.save()
        cr.set_source_rgba(0.72, 0.54, 0.36, 0.98)
        cr.rectangle(bx, by, bw, bh)
        cr.fill_preserve()
        cr.set_source_rgba(0.48, 0.34, 0.20, 0.95)
        cr.set_line_width(1.0)
        cr.stroke()
        # Front flap
        cr.move_to(bx + 3, by)
        cr.line_to(bx + bw // 2, by + 3)
        cr.line_to(bx + bw - 3, by)
        cr.stroke()
        cr.restore()

    def draw_zzz(self, cr, cat_x, cat_y):
        t = (self.step_counter % 30) / 30.0
        cr.save()
        cr.set_source_rgba(0.65, 0.75, 0.90, 0.85 * (1.0 - t * 0.4))
        cr.select_font_face("Sans", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(9 + t * 4)
        cr.move_to(cat_x + self.cat_pixel_size - 2 + t * 8, cat_y - 2 - t * 14)
        cr.show_text("z")
        cr.restore()

    def draw_collar_badge(self, cr):
        cat_x, cat_y = self.get_cat_draw_coords()
        time_str = self.pomodoro.get_time_string()
        phase = self.pomodoro.phase

        if phase == PomodoroPhase.FOCUS:
            icon = "🍅"
            accent = (0.95, 0.65, 0.20, 0.6)
        elif phase in (PomodoroPhase.BREAK, PomodoroPhase.LONG_BREAK):
            icon = "☕"
            accent = (0.45, 0.75, 0.65, 0.6)
        elif phase == PomodoroPhase.PAUSED:
            icon = "⏸️"
            accent = (0.65, 0.65, 0.70, 0.6)
        else:
            icon = "🐾"
            accent = (0.50, 0.50, 0.55, 0.4)

        text = f"{icon} {time_str}"
        pill_w = 66
        pill_h = 18
        pill_x = cat_x + (self.cat_pixel_size - pill_w) // 2
        pill_y = max(2, cat_y - 20)

        self._draw_rounded_rect(cr, pill_x, pill_y, pill_w, pill_h, 9)
        cr.set_source_rgba(0.09, 0.09, 0.11, 0.92)
        cr.fill_preserve()
        cr.set_source_rgba(accent[0], accent[1], accent[2], accent[3])
        cr.set_line_width(1.0)
        cr.stroke()

        cr.save()
        cr.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(9)
        cr.set_source_rgba(0.92, 0.92, 0.94, 0.95)
        cr.move_to(pill_x + 6, pill_y + 13)
        cr.show_text(text)
        cr.restore()

    def draw_status_pill(self, cr):
        text = self.status_pill_text
        if not text:
            return

        pill_w = self.win_w - 24
        pill_h = 26
        pill_x = 12
        pill_y = 6

        self._draw_rounded_rect(cr, pill_x, pill_y, pill_w, pill_h, 8)
        cr.set_source_rgba(0.10, 0.10, 0.12, 0.94)
        cr.fill_preserve()
        cr.set_source_rgba(0.85, 0.60, 0.25, 0.5)
        cr.set_line_width(1.0)
        cr.stroke()

        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription.from_string("Sans 8.5")
        layout.set_font_description(desc)
        layout.set_text(text, -1)
        cr.set_source_rgba(0.94, 0.94, 0.96, 0.95)
        cr.move_to(pill_x + 10, pill_y + 5)
        PangoCairo.show_layout(cr, layout)

    def draw_seamless_bubble(self, cr, x, y, w, h, r, tail_x, tail_y, flipped=False):
        tail_x = max(x + r + 12, min(tail_x, x + w - r - 12))
        cr.new_sub_path()
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        if flipped:
            cr.line_to(tail_x - 9, y)
            cr.line_to(tail_x, tail_y)
            cr.line_to(tail_x + 9, y)
        cr.line_to(x + w - r, y)
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.line_to(x + w, y + h - r)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        if not flipped:
            cr.line_to(tail_x + 9, y + h)
            cr.line_to(tail_x, tail_y)
            cr.line_to(tail_x - 9, y + h)
        cr.line_to(x + r, y + h)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.close_path()

    def draw_literary_card(self, cr):
        """
        Renders the strict one-line literary drop.
        Contains: ONE LINE + AUTHOR, and minimal [Save] [Next] [Close] actions.
        """
        cat_x, cat_y = self.get_cat_draw_coords()
        card_x = 15
        card_w = self.win_w - 30
        card_h = self.quote_card_height

        if self.quote_flipped:
            card_y = cat_y + self.cat_pixel_size + 10
            tail_tip_y = cat_y + self.cat_pixel_size + 2
        else:
            card_y = 8
            tail_tip_y = cat_y - 2

        tail_center_x = cat_x + self.cat_pixel_size // 2

        # 1. Subtle shadow
        cr.save()
        self.draw_seamless_bubble(cr, card_x + 1, card_y + 2, card_w, card_h, 12, tail_center_x, tail_tip_y + 2, self.quote_flipped)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.35)
        cr.fill()
        cr.restore()

        # 2. Card body (deep ink obsidian with fine muted border)
        self.draw_seamless_bubble(cr, card_x, card_y, card_w, card_h, 12, tail_center_x, tail_tip_y, self.quote_flipped)
        cr.set_source_rgba(0.08, 0.08, 0.10, 0.96)
        cr.fill_preserve()
        cr.set_source_rgba(0.35, 0.35, 0.40, 0.5)
        cr.set_line_width(1.0)
        cr.stroke()

        work = self.literary.current_work

        # 3. Literary Line (Tasteful serif typeface)
        quote_str = f"“{work['text']}”"
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription.from_string("Serif 11")
        layout.set_font_description(desc)
        layout.set_width((card_w - 32) * Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD)
        layout.set_text(quote_str, -1)

        cr.set_source_rgba(0.95, 0.95, 0.96, 0.98)
        cr.move_to(card_x + 16, card_y + 16)
        PangoCairo.show_layout(cr, layout)

        _, logical = layout.get_pixel_extents()
        author_y = card_y + 18 + logical.height + 4

        # 4. Author
        author_str = f"— {work['author']}"
        a_layout = PangoCairo.create_layout(cr)
        a_desc = Pango.FontDescription.from_string("Sans 8.5")
        a_layout.set_font_description(a_desc)
        a_layout.set_text(author_str, -1)

        cr.set_source_rgba(0.68, 0.70, 0.74, 0.88)
        cr.move_to(card_x + 16, author_y)
        PangoCairo.show_layout(cr, a_layout)

        # 5. Minimal Action Controls: [ Save ] [ Next ] [ Close ]
        self.lit_buttons.clear()
        btn_y = card_y + card_h - 22
        btn_h = 16

        # Close
        close_x = card_x + card_w - 52
        close_w = 40
        self.lit_buttons.append(("close", close_x, btn_y - 2, close_x + close_w, btn_y + btn_h))
        cr.save()
        c_layout = PangoCairo.create_layout(cr)
        c_layout.set_font_description(Pango.FontDescription.from_string("Sans 8"))
        c_layout.set_text("Close", -1)
        cr.set_source_rgba(0.55, 0.58, 0.64, 0.85)
        cr.move_to(close_x, btn_y)
        PangoCairo.show_layout(cr, c_layout)
        cr.restore()

        # Next
        next_x = close_x - 48
        next_w = 38
        self.lit_buttons.append(("next", next_x, btn_y - 2, next_x + next_w, btn_y + btn_h))
        cr.save()
        n_layout = PangoCairo.create_layout(cr)
        n_layout.set_font_description(Pango.FontDescription.from_string("Sans 8"))
        n_layout.set_text("Next", -1)
        cr.set_source_rgba(0.70, 0.75, 0.85, 0.90)
        cr.move_to(next_x, btn_y)
        PangoCairo.show_layout(cr, n_layout)
        cr.restore()

        # Save
        save_x = next_x - 56
        save_w = 46
        self.lit_buttons.append(("save", save_x, btn_y - 2, save_x + save_w, btn_y + btn_h))
        cr.save()
        s_layout = PangoCairo.create_layout(cr)
        s_layout.set_font_description(Pango.FontDescription.from_string("Sans 8"))
        is_saved = self.literary.is_current_saved() or self.just_saved_notice
        s_layout.set_text("Saved ✓" if is_saved else "Save", -1)
        if is_saved:
            cr.set_source_rgba(0.40, 0.85, 0.55, 0.95)
        else:
            cr.set_source_rgba(0.85, 0.70, 0.35, 0.90)
        cr.move_to(save_x, btn_y)
        PangoCairo.show_layout(cr, s_layout)
        cr.restore()

    def _draw_rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Oneko Desktop Companion")
        print("Usage: oneko [options]")
        print("  --customize, -c   Open pet character customization window")
        print("  --focus, -f       Start 45-minute focus session immediately")
        print("  --help, -h        Show this help message")
        sys.exit(0)

    # Strict single-instance check: if Miu is already running, forward command and exit
    from ipc import send_ipc_command, SOCKET_PATH
    if os.path.exists(SOCKET_PATH):
        if "--home" in sys.argv or "-H" in sys.argv or "home" in sys.argv:
            success, resp = send_ipc_command("home")
            if success:
                print(resp.get("msg", "Miu Home opened."))
                sys.exit(0)
        elif "--pomodoro" in sys.argv or "-p" in sys.argv or "pomodoro" in sys.argv:
            success, resp = send_ipc_command("pomodoro_enable")
            if success:
                print(resp.get("msg", "Pomodoro mode enabled."))
                sys.exit(0)
        elif "--focus" in sys.argv or "-f" in sys.argv:
            success, resp = send_ipc_command("focus")
            if success:
                print(resp.get("msg", "Miu is focused."))
                sys.exit(0)
        elif "--customize" in sys.argv or "-c" in sys.argv:
            success, resp = send_ipc_command("customize")
            if success:
                sys.exit(0)
        else:
            success, resp = send_ipc_command("wake")
            if success:
                print(resp.get("msg", "Miu is already running."))
                sys.exit(0)

    app = OnekoCompanionApp()

    signal.signal(signal.SIGINT, lambda s, f: app.quit_app())
    signal.signal(signal.SIGTERM, lambda s, f: app.quit_app())

    if "--pomodoro" in sys.argv or "-p" in sys.argv:
        app.config["pomodoro_enabled"] = True
        app.save_config()
        app.tray.update_menu()
        app.update_window_shape_and_size()
        app.queue_draw()

    if "--customize" in sys.argv or "-c" in sys.argv:
        app.open_preferences()
    if "--home" in sys.argv or "-H" in sys.argv:
        app.open_home()
    if "--focus" in sys.argv or "-f" in sys.argv:
        app.start_focus_session()

    Gtk.main()


if __name__ == "__main__":
    main()

