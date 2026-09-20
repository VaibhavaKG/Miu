"""
60-Second Celebration Subsystem for Miu Desktop Companion.

Core architecture:
- OPTIONAL visual layer: zero control over Pomodoro state.
- Authoritative timer independence: BREAK begins and counts down independently of celebration.
- Single lightweight full-screen click-through overlay window:
  * Eliminates multiple top-level GTK windows.
  * Zero X11 window.move() roundtrips per frame.
  * Zero GTK main-loop starvation.
- Monotonic wall-clock timing (time.monotonic()): guaranteed accurate 60-second duration.
- Explicit lifecycle: IDLE -> STARTING -> RUNNING -> FINISHING -> COMPLETE -> IDLE.
- Strict anti-duplication state lock.
- Complete fail-safe exception isolation: errors cleanly clean up without affecting Pomodoro.
- Binary isolation test toggle: enable_visuals flag to test logic with zero rendering.
"""

import os
import sys
import math
import time
import random
from enum import Enum

os.environ["GDK_BACKEND"] = "x11"

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gtk, Gdk, GLib
    import cairo
    HAS_GTK = True
except Exception:
    HAS_GTK = False

from cosmetics import SpriteManager

try:
    from paths import USER_LOG_FILE
    LOG_FILE = USER_LOG_FILE
except ImportError:
    APP_DIR = os.path.expanduser("~/.local/share/oneko-plus")
    LOG_FILE = os.path.join(APP_DIR, "miu.log")


def log_event(msg):
    print(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


class CelebrationState(Enum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    FINISHING = "FINISHING"
    COMPLETE = "COMPLETE"


class CelebrationPhase(Enum):
    ARRIVING = "ARRIVING"    # 0–15s: Guest Mius arrive from screen borders
    PEAK = "PEAK"            # 15–30s: Peak activity (hops, purrs, heart particles)
    SETTLING = "SETTLING"    # 30–45s: Activity settles, peaceful sitting
    LEAVING = "LEAVING"      # 45–60s: Guest Mius walk toward screen borders and exit


class HeartParticle:
    """Small floating heart particle rendered during celebration peak activity."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.6, 0.6)
        self.vy = random.uniform(-1.4, -0.7)
        self.alpha = 1.0
        self.decay = random.uniform(0.018, 0.035)
        self.size = random.uniform(6.0, 9.0)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.alpha -= self.decay
        return self.alpha > 0.0

    def draw(self, cr):
        if self.alpha <= 0.0:
            return
        cr.save()
        cr.translate(self.x, self.y)
        cr.set_source_rgba(0.95, 0.35, 0.55, max(0.0, min(1.0, self.alpha)))
        s = self.size / 10.0
        cr.scale(s, s)
        cr.move_to(0, 0)
        cr.curve_to(-5, -6, -9, -1, 0, 8)
        cr.curve_to(9, -1, 5, -6, 0, 0)
        cr.fill()
        cr.restore()


class GuestMiu:
    """
    A temporary visiting Miu companion entity drawn on the celebration overlay.
    Does NOT create a separate GTK window; runs inside the single celebration surface.
    """
    def __init__(self, theme, start_x, start_y, target_x, target_y, exit_x, exit_y, scale=1.25):
        self.theme = theme
        self.x = float(start_x)
        self.y = float(start_y)
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.exit_x = float(exit_x)
        self.exit_y = float(exit_y)

        self.scale = scale
        self.current_sprite = "idle"
        self.sprite_frame = 0
        self.anim_tick = 0
        self.hop_offset_y = 0.0

    def move_towards(self, tx, ty, speed):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist <= max(2.5, speed):
            self.x = tx
            self.y = ty
            return True, 0.0

        step_dist = min(speed, dist)
        self.x += (dx / dist) * step_dist
        self.y += (dy / dist) * step_dist

        # Directional sprite
        if abs(dx) > abs(dy):
            self.current_sprite = "E" if dx > 0 else "W"
        else:
            self.current_sprite = "S" if dy > 0 else "N"

        self.anim_tick += 1
        if self.anim_tick % 4 == 0:
            self.sprite_frame = (self.sprite_frame + 1) % 2

        return False, dist

    def draw(self, cr, sprite_manager):
        if not sprite_manager:
            # Fallback simple shape if no sprite manager
            cr.set_source_rgba(0.9, 0.7, 0.4, 0.9)
            cr.arc(self.x, self.y + self.hop_offset_y, 16 * self.scale, 0, 2 * math.pi)
            cr.fill()
            return

        frame = sprite_manager.get_frame(self.current_sprite, self.sprite_frame)
        if frame:
            w = frame.get_width()
            h = frame.get_height()
            draw_x = int(self.x - w / 2)
            draw_y = int(self.y - h / 2 + self.hop_offset_y)
            Gdk.cairo_set_source_pixbuf(cr, frame, draw_x, draw_y)
            cr.paint()


class CelebrationManager:
    """
    Coordinates the 60-second celebration.
    Uses a single transparent click-through canvas window to avoid event-loop starvation.
    """
    def __init__(self, app=None):
        self.app = app
        self.state = CelebrationState.IDLE
        self.start_time = 0.0
        self.elapsed = 0.0
        self.total_duration = 60.0
        self.current_phase = None
        self.enable_visuals = True  # Binary isolation toggle

        self.guests = []
        self.particles = []
        self.overlay_window = None
        self.theme_sprites = {}

    def _init_theme_sprites(self):
        """Pre-loads sprite frames once for guest themes using existing raw_sheet."""
        if self.theme_sprites or not self.app:
            return

        sheet_path = getattr(self.app.sprites, "sheet_path", None) if hasattr(self.app, "sprites") else None
        scale = getattr(self.app, "config", {}).get("cat_scale", 1.25) if self.app else 1.25

        if sheet_path and os.path.exists(sheet_path):
            for th in ("ginger", "black", "calico"):
                try:
                    self.theme_sprites[th] = SpriteManager(sheet_path, scale=scale, theme=th)
                except Exception:
                    pass

    def get_phase(self):
        if self.state not in (CelebrationState.RUNNING, CelebrationState.FINISHING):
            return None
        if self.elapsed < 15.0:
            return CelebrationPhase.ARRIVING
        elif self.elapsed < 30.0:
            return CelebrationPhase.PEAK
        elif self.elapsed < 45.0:
            return CelebrationPhase.SETTLING
        else:
            return CelebrationPhase.LEAVING

    def start(self):
        """
        Requests starting a celebration.
        Guarantees single execution via anti-duplication state lock.
        """
        if self.state != CelebrationState.IDLE:
            return False

        log_event("[MIU] CELEBRATION REQUESTED")
        log_event("[MIU] CELEBRATION START")
        self.state = CelebrationState.STARTING
        self.start_time = time.monotonic()
        self.elapsed = 0.0
        self.current_phase = CelebrationPhase.ARRIVING
        self.particles.clear()

        try:
            self._init_theme_sprites()
            self._spawn_guests()
            if self.enable_visuals and HAS_GTK:
                self._create_overlay_window()
            self.state = CelebrationState.RUNNING
            return True
        except Exception as e:
            log_event(f"[MIU] CELEBRATION FAILED: {e}\n[MIU] BREAK CONTINUES")
            self.cleanup()
            return False

    def _spawn_guests(self):
        self.guests.clear()

        ref_x = getattr(self.app, "cat_x", 400.0) if self.app else 400.0
        ref_y = getattr(self.app, "cat_y", 300.0) if self.app else 300.0
        screen_w = getattr(self.app, "screen_w", 1920) if self.app else 1920
        screen_h = getattr(self.app, "screen_h", 1080) if self.app else 1080
        scale = getattr(self.app, "config", {}).get("cat_scale", 1.25) if self.app else 1.25

        guest_configs = [
            {
                "theme": "ginger",
                "start": (max(20.0, ref_x - 300.0), ref_y + 10.0),
                "target": (max(30.0, ref_x - 55.0), ref_y + 8.0),
                "exit": (max(10.0, ref_x - 350.0), ref_y + 10.0)
            },
            {
                "theme": "black",
                "start": (min(float(screen_w - 20), ref_x + 300.0), ref_y + 10.0),
                "target": (min(float(screen_w - 30), ref_x + 55.0), ref_y + 8.0),
                "exit": (min(float(screen_w - 10), ref_x + 350.0), ref_y + 10.0)
            },
            {
                "theme": "calico",
                "start": (ref_x, min(float(screen_h - 20), ref_y + 220.0)),
                "target": (ref_x, min(float(screen_h - 30), ref_y + 48.0)),
                "exit": (ref_x, min(float(screen_h - 10), ref_y + 260.0))
            }
        ]

        for cfg in guest_configs:
            g = GuestMiu(
                theme=cfg["theme"],
                start_x=cfg["start"][0],
                start_y=cfg["start"][1],
                target_x=cfg["target"][0],
                target_y=cfg["target"][1],
                exit_x=cfg["exit"][0],
                exit_y=cfg["exit"][1],
                scale=scale
            )
            self.guests.append(g)

    def _create_overlay_window(self):
        """Creates ONE transparent, click-through overlay window covering desktop."""
        try:
            screen_w = getattr(self.app, "screen_w", 1920) if self.app else 1920
            screen_h = getattr(self.app, "screen_h", 1080) if self.app else 1080

            win = Gtk.Window(type=Gtk.WindowType.POPUP)
            win.set_app_paintable(True)
            win.set_keep_above(True)
            win.set_skip_taskbar_hint(True)
            win.set_skip_pager_hint(True)
            win.set_decorated(False)

            screen = win.get_screen()
            visual = screen.get_rgba_visual() if screen else None
            if visual:
                win.set_visual(visual)

            win.set_size_request(screen_w, screen_h)
            win.move(0, 0)
            win.connect("draw", self.on_draw)
            win.realize()

            # Empty input region: all mouse clicks pass completely through
            gdk_win = win.get_window()
            if gdk_win:
                reg = cairo.Region()
                gdk_win.input_shape_combine_region(reg, 0, 0)

            win.show_all()
            self.overlay_window = win
        except Exception as e:
            self.overlay_window = None

    def on_draw(self, widget, cr):
        """Draws all celebration guests and heart particles in a single pass."""
        try:
            cr.set_source_rgba(0, 0, 0, 0)
            cr.set_operator(cairo.OPERATOR_CLEAR)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)

            # Draw guest cats
            for g in self.guests:
                sm = self.theme_sprites.get(g.theme)
                if not sm and self.app and hasattr(self.app, "sprites"):
                    sm = self.app.sprites
                g.draw(cr, sm)

            # Draw particles
            for p in self.particles:
                p.draw(cr)

        except Exception:
            pass
        return True

    def step(self, dt=0.05):
        """
        Advances the celebration animation.
        Uses monotonic wall-clock time for accurate 60-second measurement.
        Never throws an unhandled exception.
        """
        if self.state not in (CelebrationState.RUNNING, CelebrationState.FINISHING):
            return

        try:
            now = time.monotonic()
            if self.start_time > 0.0:
                clock_elapsed = now - self.start_time
                self.elapsed = max(self.elapsed + dt, clock_elapsed)
            else:
                self.elapsed += dt

            new_phase = self.get_phase()
            if new_phase != self.current_phase and new_phase is not None:
                self.current_phase = new_phase
                log_event(f"[MIU] CELEBRATION PHASE {new_phase.value}")

            if self.elapsed >= self.total_duration:
                self.finish()
                return

            if self.current_phase == CelebrationPhase.ARRIVING:
                # 0–15s: Guests move to target positions
                for g in self.guests:
                    arrived, _ = g.move_towards(g.target_x, g.target_y, speed=3.5)
                    if arrived:
                        g.current_sprite = "idle"
                    g.hop_offset_y = 0.0

            elif self.current_phase == CelebrationPhase.PEAK:
                # 15–30s: Peak activity (hops, heart particles)
                for i, g in enumerate(self.guests):
                    g.current_sprite = "idle"
                    g.hop_offset_y = -abs(math.sin((self.elapsed + i * 0.7) * 5.0)) * 7.0

                if random.random() < 0.12 and len(self.particles) < 12 and self.guests:
                    cg = random.choice(self.guests)
                    self.particles.append(HeartParticle(cg.x, cg.y - 12))

                self.particles = [p for p in self.particles if p.update()]

            elif self.current_phase == CelebrationPhase.SETTLING:
                # 30–45s: Activity calms down, peaceful resting
                for g in self.guests:
                    g.hop_offset_y = 0.0
                    g.current_sprite = "tired"

                self.particles = [p for p in self.particles if p.update()]

            elif self.current_phase == CelebrationPhase.LEAVING:
                # 45–60s: Guests walk toward exit positions
                self.state = CelebrationState.FINISHING
                for g in self.guests:
                    g.hop_offset_y = 0.0
                    g.move_towards(g.exit_x, g.exit_y, speed=3.2)

                self.particles = [p for p in self.particles if p.update()]

            # Request single redraw of the overlay window
            if self.overlay_window:
                self.overlay_window.queue_draw()

        except Exception as e:
            log_event(f"[MIU] CELEBRATION FAILED: {e}\n[MIU] BREAK CONTINUES")
            self.cleanup()

    def finish(self):
        """Terminates celebration cleanly when timer expires."""
        log_event("CELEBRATION FINISHED")
        log_event(f"[MIU] CELEBRATION COMPLETE ({self.elapsed:.1f}s elapsed)")
        self.cleanup()
        self.state = CelebrationState.COMPLETE

    def cleanup(self):
        """Destroys overlay window and resets state."""
        if self.overlay_window:
            try:
                self.overlay_window.destroy()
            except Exception:
                pass
            self.overlay_window = None

        self.guests.clear()
        self.particles.clear()
        self.state = CelebrationState.IDLE
        self.start_time = 0.0
        self.elapsed = 0.0
        self.current_phase = None

    def is_active(self):
        return self.state in (CelebrationState.STARTING, CelebrationState.RUNNING, CelebrationState.FINISHING)
