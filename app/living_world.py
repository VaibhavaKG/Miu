"""
Living World & Natural Interaction Engine for Miu Desktop Companion.

Implements:
1. Tiny Discoveries (leaf, paper scrap, star, feather, ball, coin, tiny book)
2. Tiny Toys (yarn ball, paper ball, butterfly, feather, laser dot, cardboard box)
3. Simple physical feel (deterministic movement, bounce, friction, gravity, oscillation)
4. Cursor Personality (environmental stimulus, notice, curious watch, hop, repeated click annoyance scamper)
5. Cursor Cooldowns (probabilistic gating, strong cooldowns)
6. "Where did Miu go?" (walk -> edge -> disappear -> absence -> return)
7. Absence rarity & safety (no crash, instant recall on summon)
8. Contextual Sleep (corners, window ledges, window bases, floor)
9. Sleeping Personality calibration (calm, playful, sleepy, energetic, focused)
10. Break as playground (high expressiveness, discoveries, toys, climbing)
11. Respectful Focus (quiet presence, no comatose, suppressed distractions)
12. Event Selection System (probabilities, cooldowns, modifiers, environmental criteria)
13. Repetition Prevention (recent event history, non-repetitive variety)
14-18. Summon Miu (Ctrl+M, CLI, IPC, Tray, safe destinations, multi-state recall, spam protection)
19-22. Visual style (minimal, elegant, click-through transparent Cairo overlays, zero dashboard clutter)
"""

import os
import sys
import math
import time
import random
from collections import deque
from enum import Enum

# Force x11 for GDK
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


class LivingEventType(Enum):
    NORMAL_ROAM = "NORMAL_ROAM"
    DISCOVERY = "DISCOVERY"
    TOY_PLAY = "TOY_PLAY"
    CURSOR_REACTION = "CURSOR_REACTION"
    WINDOW_EXPLORATION = "WINDOW_EXPLORATION"
    EDGE_EXPLORATION = "EDGE_EXPLORATION"
    SLEEP = "SLEEP"
    STRETCH = "STRETCH"
    SIT = "SIT"
    OFFSCREEN_ABSENCE = "OFFSCREEN_ABSENCE"


class DiscoveryType(Enum):
    LEAF = "leaf"
    PAPER_SCRAP = "paper_scrap"
    STAR = "star"
    FEATHER = "feather"
    SMALL_BALL = "small_ball"
    COIN = "coin"
    TINY_BOOK = "tiny_book"


class ToyType(Enum):
    YARN_BALL = "yarn_ball"
    PAPER_BALL = "paper_ball"
    BUTTERFLY = "butterfly"
    FEATHER_TOY = "feather_toy"
    LASER_DOT = "laser_dot"
    CARDBOARD_BOX = "cardboard_box"


class WorldItem:
    """Represents a lightweight desktop object (discovery or toy) with simple deterministic physics."""

    def __init__(self, item_type, x, y, is_toy=False):
        self.item_type = item_type
        self.is_toy = is_toy
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0
        self.ay = 0.0
        self.friction = 0.94
        self.elasticity = 0.60
        self.rotation = 0.0
        self.rotation_speed = 0.0
        self.age = 0.0
        self.lifetime = random.uniform(5.0, 8.0) if not is_toy else random.uniform(14.0, 26.0)
        self.fade_alpha = 1.0
        self.is_fading = False
        self.is_expired = False
        self.phase = 0.0
        self.width = 36
        self.height = 36

        # Toy-specific attributes
        self.interaction_count = 0
        self.target_points = []
        self.current_point_idx = 0
        self.box_miu_inside = False
        self.trail_points = deque(maxlen=6)

        self._init_item_dynamics()

    def _init_item_dynamics(self):
        t = self.item_type
        if t == DiscoveryType.LEAF:
            self.width, self.height = 32, 32
            self.rotation = random.uniform(-0.4, 0.4)
        elif t == DiscoveryType.STAR:
            self.width, self.height = 32, 32
        elif t == DiscoveryType.TINY_BOOK:
            self.width, self.height = 34, 34
        elif t == ToyType.YARN_BALL:
            self.width, self.height = 40, 40
            self.friction = 0.95
            self.elasticity = 0.70
        elif t == ToyType.PAPER_BALL:
            self.width, self.height = 34, 34
            self.friction = 0.90
            self.elasticity = 0.50
        elif t == ToyType.BUTTERFLY:
            self.width, self.height = 36, 36
            self.lifetime = random.uniform(14.0, 22.0)
            self.vx = random.choice([-25.0, 25.0])
            self.vy = -12.0
        elif t == ToyType.FEATHER_TOY or t == DiscoveryType.FEATHER:
            self.width, self.height = 36, 36
            self.ay = 15.0  # gentle downward drift
        elif t == ToyType.LASER_DOT:
            self.width, self.height = 30, 30
            self.lifetime = random.uniform(12.0, 18.0)
        elif t == ToyType.CARDBOARD_BOX:
            self.width, self.height = 54, 46
            self.lifetime = random.uniform(20.0, 30.0)

    def apply_impulse(self, ivx, ivy):
        self.vx += ivx
        self.vy += ivy

    def step(self, dt, screen_w=1920, screen_h=1080, ledges=None):
        """Advances physics by dt seconds."""
        if self.is_expired:
            return

        self.age += dt
        self.phase += dt

        # Check expiration and fade
        if self.age >= self.lifetime:
            self.is_fading = True
            self.fade_alpha = max(0.0, self.fade_alpha - dt * 1.5)
            if self.fade_alpha <= 0.0:
                self.is_expired = True
                return

        t = self.item_type

        # 1. BUTTERFLY: sinusoidal fluttering flight
        if t == ToyType.BUTTERFLY:
            self.x += self.vx * dt
            self.y += (self.vy + math.sin(self.phase * 5.0) * 22.0) * dt
            # Rebound off screen edges
            if self.x < 30:
                self.x = 30
                self.vx = abs(self.vx)
            elif self.x > screen_w - 30:
                self.x = screen_w - 30
                self.vx = -abs(self.vx)
            if self.y < 30:
                self.y = 30
                self.vy = abs(self.vy)
            elif self.y > screen_h - 100:
                self.y = screen_h - 100
                self.vy = -abs(self.vy)
            return

        # 2. FEATHER: swaying air resistance
        if t in (ToyType.FEATHER_TOY, DiscoveryType.FEATHER):
            self.vy = min(26.0, self.vy + self.ay * dt)
            self.vx = math.cos(self.phase * 2.5) * 20.0
            self.x += self.vx * dt
            self.y += self.vy * dt
            floor_y = screen_h - 35
            if self.y >= floor_y:
                self.y = floor_y
                self.vy = 0.0
                self.vx = 0.0
            return

        # 3. LASER DOT: rapid darting between nearby spots
        if t == ToyType.LASER_DOT:
            if not self.target_points or (self.age > 0.5 and random.random() < 0.02):
                nx = max(40, min(screen_w - 40, self.x + random.uniform(-140, 140)))
                ny = max(40, min(screen_h - 40, self.y + random.uniform(-100, 100)))
                self.target_points = [(nx, ny)]
                self.current_point_idx = 0

            if self.target_points:
                tx, ty = self.target_points[0]
                dx, dy = tx - self.x, ty - self.y
                dist = math.hypot(dx, dy)
                if dist > 6.0:
                    speed = 280.0
                    self.x += (dx / dist) * min(dist, speed * dt)
                    self.y += (dy / dist) * min(dist, speed * dt)
            return

        # 4. GENERAL PHYSICAL INTEGRATION (Balls, Leaf, Coin, etc.)
        self.vx += self.ax * dt
        self.vy += self.ay * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Friction
        friction_factor = self.friction ** (dt / 0.05)
        self.vx *= friction_factor
        self.vy *= friction_factor
        if math.hypot(self.vx, self.vy) < 2.0:
            self.vx = 0.0
            self.vy = 0.0

        # Record trail
        if math.hypot(self.vx, self.vy) > 10.0:
            self.trail_points.append((self.x, self.y))
            self.rotation += (self.vx * dt) * 0.15

        # Screen boundaries
        min_x, max_x = 24.0, float(screen_w - 24)
        min_y, max_y = 24.0, float(screen_h - 36)

        if self.x <= min_x:
            self.x = min_x
            self.vx = -self.vx * self.elasticity
        elif self.x >= max_x:
            self.x = max_x
            self.vx = -self.vx * self.elasticity

        if self.y >= max_y:
            self.y = max_y
            if abs(self.vy) > 8.0:
                self.vy = -self.vy * self.elasticity
            else:
                self.vy = 0.0

        # Collision with window top ledges
        if ledges and self.vy > 0:
            for lx1, lx2, ly in ledges:
                if lx1 - 10 <= self.x <= lx2 + 10 and abs(self.y - ly) < 10:
                    self.y = ly - 2
                    self.vy = -self.vy * self.elasticity
                    break

    def draw(self, cr, offset_x=0, offset_y=0):
        """Draws the item centered at (width // 2, height // 2) with Cairo."""
        cx = self.width / 2.0 + offset_x
        cy = self.height / 2.0 + offset_y

        cr.save()
        t = self.item_type

        # 1. LITTLE LEAF
        if t == DiscoveryType.LEAF:
            cr.translate(cx, cy)
            cr.rotate(self.rotation + math.sin(self.phase * 2.5) * 0.12)
            cr.set_source_rgba(0.78, 0.48, 0.22, 0.95 * self.fade_alpha)
            cr.move_to(-8, 0)
            cr.curve_to(-4, -7, 6, -6, 10, 0)
            cr.curve_to(6, 6, -4, 7, -8, 0)
            cr.fill_preserve()
            cr.set_source_rgba(0.55, 0.32, 0.12, 0.85 * self.fade_alpha)
            cr.set_line_width(0.9)
            cr.stroke()
            # Stem
            cr.move_to(-8, 0)
            cr.line_to(-12, 3)
            cr.stroke()

        # 2. TINY PAPER SCRAP
        elif t == DiscoveryType.PAPER_SCRAP:
            cr.translate(cx, cy)
            cr.rotate(0.18)
            cr.set_source_rgba(0.92, 0.90, 0.84, 0.96 * self.fade_alpha)
            cr.rectangle(-6, -6, 12, 12)
            cr.fill_preserve()
            cr.set_source_rgba(0.65, 0.62, 0.58, 0.80 * self.fade_alpha)
            cr.set_line_width(0.8)
            cr.stroke()
            # Dog-ear corner
            cr.move_to(3, -6)
            cr.line_to(6, -3)
            cr.line_to(3, -3)
            cr.close_path()
            cr.set_source_rgba(0.78, 0.75, 0.70, 0.9 * self.fade_alpha)
            cr.fill()

        # 3. STAR
        elif t == DiscoveryType.STAR:
            cr.translate(cx, cy)
            glow = 0.82 + 0.18 * math.sin(self.phase * 4.0)
            # Soft halo
            cr.arc(0, 0, 9, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 0.88, 0.35, 0.22 * glow * self.fade_alpha)
            cr.fill()
            # 5-point star
            cr.set_source_rgba(1.0, 0.86, 0.25, 0.98 * self.fade_alpha)
            for i in range(10):
                angle = i * (math.pi / 5.0) - math.pi / 2.0
                r = 6.5 if i % 2 == 0 else 2.8
                px = math.cos(angle) * r
                py = math.sin(angle) * r
                if i == 0:
                    cr.move_to(px, py)
                else:
                    cr.line_to(px, py)
            cr.close_path()
            cr.fill()

        # 4. FEATHER
        elif t in (DiscoveryType.FEATHER, ToyType.FEATHER_TOY):
            cr.translate(cx, cy)
            cr.rotate(0.35 + math.sin(self.phase * 2.0) * 0.15)
            cr.set_source_rgba(0.88, 0.90, 0.94, 0.95 * self.fade_alpha)
            cr.move_to(-10, 4)
            cr.curve_to(-6, -7, 6, -8, 11, -4)
            cr.curve_to(6, -2, -4, 5, -10, 4)
            cr.fill_preserve()
            cr.set_source_rgba(0.60, 0.65, 0.72, 0.80 * self.fade_alpha)
            cr.set_line_width(0.8)
            cr.stroke()
            # Quill center
            cr.move_to(-11, 5)
            cr.line_to(10, -4)
            cr.stroke()

        # 5. SMALL BALL
        elif t == DiscoveryType.SMALL_BALL:
            cr.arc(cx, cy, 6, 0, 2 * math.pi)
            cr.set_source_rgba(0.35, 0.65, 0.85, 0.98 * self.fade_alpha)
            cr.fill_preserve()
            cr.set_source_rgba(0.20, 0.45, 0.65, 0.85 * self.fade_alpha)
            cr.set_line_width(1.0)
            cr.stroke()
            # Highlight dot
            cr.arc(cx - 2, cy - 2, 1.8, 0, 2 * math.pi)
            cr.set_source_rgba(0.95, 0.98, 1.0, 0.85 * self.fade_alpha)
            cr.fill()

        # 6. COIN
        elif t == DiscoveryType.COIN:
            shine = math.sin(self.phase * 3.0)
            w_scale = max(0.2, abs(shine))
            cr.translate(cx, cy)
            cr.scale(w_scale, 1.0)
            cr.arc(0, 0, 6, 0, 2 * math.pi)
            cr.set_source_rgba(0.95, 0.78, 0.22, 0.98 * self.fade_alpha)
            cr.fill_preserve()
            cr.set_source_rgba(0.70, 0.52, 0.12, 0.85 * self.fade_alpha)
            cr.set_line_width(1.0)
            cr.stroke()

        # 7. TINY BOOK
        elif t == DiscoveryType.TINY_BOOK:
            cr.translate(cx, cy)
            cr.rotate(-0.15)
            # Cover
            cr.set_source_rgba(0.55, 0.22, 0.24, 0.98 * self.fade_alpha)
            cr.rectangle(-6, -7, 12, 14)
            cr.fill_preserve()
            cr.set_source_rgba(0.35, 0.12, 0.14, 0.90 * self.fade_alpha)
            cr.set_line_width(0.8)
            cr.stroke()
            # Pages rim
            cr.set_source_rgba(0.94, 0.92, 0.86, 0.95 * self.fade_alpha)
            cr.rectangle(-2, -6, 7, 12)
            cr.fill()
            # Gold spine ribbon
            cr.set_source_rgba(0.85, 0.70, 0.30, 0.95 * self.fade_alpha)
            cr.move_to(-6, -7)
            cr.line_to(-6, 7)
            cr.stroke()

        # 8. YARN BALL
        elif t == ToyType.YARN_BALL:
            # Trailing thread
            if len(self.trail_points) >= 2:
                cr.save()
                cr.set_source_rgba(0.88, 0.45, 0.55, 0.55 * self.fade_alpha)
                cr.set_line_width(1.2)
                p0 = self.trail_points[0]
                cr.move_to(p0[0] - self.x + cx, p0[1] - self.y + cy)
                for pt in list(self.trail_points)[1:]:
                    cr.line_to(pt[0] - self.x + cx, pt[1] - self.y + cy)
                cr.stroke()
                cr.restore()

            cr.translate(cx, cy)
            cr.rotate(self.rotation)
            # Yarn sphere
            cr.arc(0, 0, 7.5, 0, 2 * math.pi)
            cr.set_source_rgba(0.88, 0.45, 0.55, 0.98 * self.fade_alpha)
            cr.fill_preserve()
            cr.set_source_rgba(0.65, 0.30, 0.40, 0.85 * self.fade_alpha)
            cr.set_line_width(1.0)
            cr.stroke()
            # Coiled thread curves
            cr.set_source_rgba(0.96, 0.65, 0.72, 0.85 * self.fade_alpha)
            cr.arc(0, 0, 4.5, -0.6, 1.8)
            cr.stroke()
            cr.arc(0, 0, 6.0, 2.2, 4.2)
            cr.stroke()

        # 9. PAPER BALL
        elif t == ToyType.PAPER_BALL:
            cr.translate(cx, cy)
            cr.rotate(self.rotation)
            cr.set_source_rgba(0.88, 0.86, 0.82, 0.98 * self.fade_alpha)
            # Irregular crumpled polygon
            pts = [
                (math.cos(i * math.pi / 3.5) * (6.0 + (i % 2) * 1.5),
                 math.sin(i * math.pi / 3.5) * (6.0 + ((i + 1) % 2) * 1.5))
                for i in range(7)
            ]
            cr.move_to(pts[0][0], pts[0][1])
            for px, py in pts[1:]:
                cr.line_to(px, py)
            cr.close_path()
            cr.fill_preserve()
            cr.set_source_rgba(0.60, 0.58, 0.54, 0.80 * self.fade_alpha)
            cr.set_line_width(0.8)
            cr.stroke()

        # 10. BUTTERFLY
        elif t == ToyType.BUTTERFLY:
            cr.translate(cx, cy)
            cr.rotate(math.sin(self.phase * 3.0) * 0.18)
            wing_flap = abs(math.cos(self.phase * 14.0))
            cr.scale(0.3 + 0.7 * wing_flap, 1.0)
            # Wings
            cr.set_source_rgba(0.40, 0.75, 0.92, 0.95 * self.fade_alpha)
            cr.arc(-5, -3, 5, 0, 2 * math.pi)
            cr.fill()
            cr.arc(5, -3, 5, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgba(0.30, 0.60, 0.80, 0.95 * self.fade_alpha)
            cr.arc(-4, 4, 3.5, 0, 2 * math.pi)
            cr.fill()
            cr.arc(4, 4, 3.5, 0, 2 * math.pi)
            cr.fill()
            # Body
            cr.set_source_rgba(0.20, 0.20, 0.25, 0.95 * self.fade_alpha)
            cr.rectangle(-1, -6, 2, 12)
            cr.fill()

        # 11. LASER DOT
        elif t == ToyType.LASER_DOT:
            cr.translate(cx, cy)
            # Pulsing outer glow
            halo = 0.7 + 0.3 * math.sin(self.phase * 8.0)
            cr.arc(0, 0, 6.0, 0, 2 * math.pi)
            cr.set_source_rgba(0.98, 0.15, 0.22, 0.35 * halo * self.fade_alpha)
            cr.fill()
            # Core bright crimson dot
            cr.arc(0, 0, 2.5, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 0.20, 0.25, 0.98 * self.fade_alpha)
            cr.fill()

        # 12. CARDBOARD BOX
        elif t == ToyType.CARDBOARD_BOX:
            # When Miu sits inside, box front is drawn
            cr.translate(cx, cy)
            bw, bh = 32, 22
            # Box base
            cr.set_source_rgba(0.72, 0.54, 0.36, 0.98 * self.fade_alpha)
            cr.rectangle(-bw / 2, -bh / 2, bw, bh)
            cr.fill_preserve()
            cr.set_source_rgba(0.48, 0.34, 0.20, 0.95 * self.fade_alpha)
            cr.set_line_width(1.0)
            cr.stroke()
            # Flaps
            cr.move_to(-bw / 2, -bh / 2)
            cr.line_to(-bw / 2 - 4, -bh / 2 - 5)
            cr.line_to(0, -bh / 2 - 2)
            cr.stroke()
            cr.move_to(bw / 2, -bh / 2)
            cr.line_to(bw / 2 + 4, -bh / 2 - 5)
            cr.line_to(0, -bh / 2 - 2)
            cr.stroke()
            # Interior shadow
            cr.set_source_rgba(0.38, 0.25, 0.15, 0.60 * self.fade_alpha)
            cr.rectangle(-bw / 2 + 2, -bh / 2 + 2, bw - 4, 6)
            cr.fill()

        cr.restore()


class WorldItemWindow:
    """A small transparent GTK popup hosting the active desktop item with complete click-through."""

    def __init__(self, item):
        self.item = item
        self.window = None
        if HAS_GTK:
            self._create_window()

    def _create_window(self):
        try:
            self.window = Gtk.Window(type=Gtk.WindowType.POPUP)
            self.window.set_app_paintable(True)
            self.window.set_keep_above(True)
            self.window.set_skip_taskbar_hint(True)
            self.window.set_skip_pager_hint(True)
            self.window.set_decorated(False)

            screen = self.window.get_screen()
            visual = screen.get_rgba_visual()
            if visual:
                self.window.set_visual(visual)

            self.window.set_size_request(self.item.width, self.item.height)
            self.window.connect("draw", self.on_draw)
            self.window.realize()

            # Set empty input shape region so all mouse clicks pass directly through to desktop
            reg = cairo.Region()
            self.window.get_window().input_shape_combine_region(reg, 0, 0)

            wx = int(self.item.x - self.item.width // 2)
            wy = int(self.item.y - self.item.height // 2)
            self.window.move(wx, wy)
            self.window.show_all()
        except Exception as e:
            self.window = None

    def update_position(self):
        if not self.window:
            return
        wx = int(self.item.x - self.item.width // 2)
        wy = int(self.item.y - self.item.height // 2)
        self.window.move(wx, wy)
        self.window.queue_draw()

    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        self.item.draw(cr)
        return True

    def destroy(self):
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None


class CursorPersonalityManager:
    """Treats the cursor as a subtle environmental stimulus with natural reactions and cooldowns."""

    def __init__(self):
        self.last_cursor_notice_time = 0.0
        self.click_history = deque(maxlen=8)
        self.last_click_streak = 0
        self.annoyance_cooldown = 0.0
        self.hop_offset_y = 0.0
        self.hop_velocity_y = 0.0
        self.is_hopping = False
        self.shake_timer = 0.0
        self.shake_offset_x = 0.0
        self.refusal_timer = 0.0

    def step(self, dt):
        """Updates animation offsets like hops or shakes."""
        if self.is_hopping:
            self.hop_offset_y += self.hop_velocity_y * dt
            self.hop_velocity_y += 550.0 * dt  # Gravity
            if self.hop_offset_y >= 0.0:
                self.hop_offset_y = 0.0
                self.hop_velocity_y = 0.0
                self.is_hopping = False

        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.shake_offset_x = math.sin(self.shake_timer * 32.0) * 2.5
            if self.shake_timer <= 0:
                self.shake_offset_x = 0.0

        if self.refusal_timer > 0:
            self.refusal_timer -= dt

        if self.annoyance_cooldown > 0:
            self.annoyance_cooldown -= dt

    def on_cursor_nearby(self, dist_to_mouse, is_mouse_moving, mouse_still_ticks, mode="normal"):
        """Evaluates environmental cursor stimulus."""
        now = time.time()
        # Respect cooldown
        if now < self.last_cursor_notice_time or self.refusal_timer > 0:
            return None

        # 1. Cursor stopped near Miu (<85px) for more than 1.5s (30 ticks at 50ms)
        if dist_to_mouse < 85.0 and not is_mouse_moving and mouse_still_ticks > 28:
            prob = 0.35 if mode != "focused" else 0.06
            if random.random() < prob:
                cooldown = random.uniform(9.0, 16.0) if mode != "focused" else 24.0
                self.last_cursor_notice_time = now + cooldown
                return {"type": "watch_sit", "duration": random.uniform(1.8, 3.2)}

        # 2. Cursor passes near Miu (<95px) while moving
        if dist_to_mouse < 95.0 and is_mouse_moving:
            prob = 0.24 if mode == "normal" else (0.38 if mode == "break" else 0.04)
            if random.random() < prob:
                cooldown = random.uniform(8.0, 15.0) if mode != "focused" else 25.0
                self.last_cursor_notice_time = now + cooldown
                return {"type": "notice_glance", "duration": random.uniform(0.6, 1.2)}

        return None

    def on_click(self, cat_x, cat_y, mouse_x, mouse_y):
        """Processes user clicks on Miu with streak tracking."""
        now = time.time()
        self.click_history.append(now)

        # Count clicks within last 2.2 seconds
        recent_clicks = [t for t in self.click_history if now - t <= 2.2]
        count = len(recent_clicks)

        # 1. Repeated clicking (3 or more fast clicks within 2.2s) -> playful/mild annoyance
        if count >= 3:
            self.click_history.clear()
            self.annoyance_cooldown = 9.0
            reaction = random.choice(["scamper", "shake", "refusal"])
            if reaction == "shake":
                self.shake_timer = 0.65
                return {"type": "shake", "duration": 0.65}
            elif reaction == "refusal":
                self.refusal_timer = 2.5
                return {"type": "refusal", "duration": 2.5}
            else:  # scamper
                # Direction away from mouse
                dx = cat_x - mouse_x
                dy = cat_y - mouse_y
                norm = math.hypot(dx, dy) or 1.0
                target_x = cat_x + (dx / norm) * random.uniform(90.0, 130.0)
                target_y = cat_y + (dy / norm) * random.uniform(90.0, 130.0)
                return {"type": "scamper", "target": (target_x, target_y)}

        # 2. Single or second click -> Small playful hop + happy purr/hearts
        self.is_hopping = True
        self.hop_velocity_y = -140.0
        return {"type": "hop", "hop": True}


class AbsenceController:
    """Manages the rare 'Where did Miu go?' edge-walk, off-screen absence, and natural return."""

    def __init__(self):
        self.state = "idle"  # "idle", "walking_to_edge", "absent", "returning"
        self.absence_duration = 0.0
        self.absence_start_time = 0.0
        self.exit_edge = "right"
        self.return_edge = "right"
        self.target_pos = None

    def plan_absence(self, cur_x, cur_y, screen_w, screen_h):
        """Plans an intentional off-screen exploration trip."""
        self.state = "walking_to_edge"
        self.absence_duration = random.uniform(10.0, 20.0)

        # Choose closest or most natural screen edge
        d_left = cur_x
        d_right = screen_w - cur_x
        d_bottom = screen_h - cur_y

        min_d = min(d_left, d_right, d_bottom)
        if min_d == d_left:
            self.exit_edge = "left"
            self.target_pos = (-45.0, cur_y)
            self.return_edge = random.choice(["left", "bottom"])
        elif min_d == d_right:
            self.exit_edge = "right"
            self.target_pos = (float(screen_w + 45), cur_y)
            self.return_edge = random.choice(["right", "bottom"])
        else:
            self.exit_edge = "bottom"
            self.target_pos = (cur_x, float(screen_h + 45))
            self.return_edge = random.choice(["bottom", "left", "right"])

        return self.target_pos

    def on_reached_edge(self):
        """Called when Miu steps past the screen border."""
        self.state = "absent"
        self.absence_start_time = time.time()

    def update_absence(self, screen_w, screen_h):
        """Checks if absence period has completed naturally."""
        if self.state != "absent":
            return None

        if time.time() - self.absence_start_time >= self.absence_duration:
            return self.trigger_return(screen_w, screen_h)
        return None

    def trigger_return(self, screen_w, screen_h):
        """Initiates natural re-entry from screen border."""
        self.state = "returning"
        if self.return_edge == "left":
            entry_x = -20.0
            dest_x = random.uniform(50.0, 110.0)
            dest_y = random.uniform(100.0, screen_h - 100.0)
            entry_y = dest_y
        elif self.return_edge == "right":
            entry_x = float(screen_w + 20)
            dest_x = float(screen_w - random.uniform(50.0, 110.0))
            dest_y = random.uniform(100.0, screen_h - 100.0)
            entry_y = dest_y
        else:
            entry_x = random.uniform(100.0, screen_w - 100.0)
            dest_x = entry_x
            entry_y = float(screen_h + 20)
            dest_y = float(screen_h - random.uniform(50.0, 90.0))

        return {
            "entry_pos": (entry_x, entry_y),
            "dest_pos": (dest_x, dest_y)
        }

    def cancel_absence_for_summon(self, screen_w, screen_h):
        """If Miu is summoned while absent, immediately returns."""
        if self.state in ("absent", "walking_to_edge"):
            return self.trigger_return(screen_w, screen_h)
        return None


class ContextualSleepManager:
    """Manages contextual sleeping in varied locations (corners, ledges, window sides, floor)."""

    def __init__(self):
        self.sleep_state = "awake"  # "awake", "seeking", "sitting", "sleeping", "stretching"
        self.target_spot = None
        self.sleep_duration = 10.0
        self.sleep_start_time = 0.0

    def find_sleep_spot(self, cur_x, cur_y, screen_w, screen_h, windows=None, favorite=None):
        """Selects a contextual resting place."""
        spots = []

        # 1. Window top ledges (peaceful high ground)
        if windows:
            for w in windows:
                spots.append((w.x + w.w // 2, max(24, w.y - 8), "window_ledge"))
                spots.append((max(24, w.x - 16), min(screen_h - 45, w.y + w.h - 10), "window_base"))

        # 2. Desktop corners
        spots.append((screen_w - 65, screen_h - 55, "bottom_right_corner"))
        spots.append((65, screen_h - 55, "bottom_left_corner"))
        spots.append((screen_w - 65, 55, "top_right_corner"))

        # 3. Perimeter floor
        spots.append((random.randint(80, screen_w - 80), screen_h - 50, "floor"))

        # 4. Favorite spot if remembered
        if favorite and isinstance(favorite, dict) and "x" in favorite and "y" in favorite:
            spots.append((favorite["x"], favorite["y"], "favorite"))

        # Choose the most pleasant spot
        chosen = random.choice(spots)
        self.target_spot = (chosen[0], chosen[1])
        self.sleep_state = "seeking"
        return self.target_spot

    def get_sleep_duration_for_personality(self, personality_key):
        """Calibrates sleep duration by personality."""
        pk = str(personality_key).lower()
        if pk == "playful":
            return random.uniform(4.0, 7.0)  # quick nap, wakes alert
        elif pk == "sleepy":
            return random.uniform(10.0, 18.0)  # longer deeper sleep
        elif pk == "energetic":
            return random.uniform(8.0, 14.0)  # rare, but when it does, sleeps well
        elif pk == "focused":
            return random.uniform(5.0, 9.0)  # short quiet rest
        else:  # calm
            return random.uniform(11.0, 16.0)


class SummonManager:
    """Manages the summon workflow (Ctrl+M / CLI / IPC / Tray) with safe destinations and spam protection."""

    def __init__(self):
        self.last_summon_time = 0.0
        self.summon_cooldown = 3.0  # seconds between major summon resets
        self.is_summoning = False
        self.summon_target = None

    def can_trigger(self):
        now = time.time()
        return (now - self.last_summon_time) >= self.summon_cooldown

    def acknowledge_spam(self):
        """Called if user presses shortcut repeatedly within cooldown."""
        return {"type": "ack_twitch", "msg": "Miu acknowledges summon."}

    def calculate_safe_destination(self, mouse_x, mouse_y, screen_w, screen_h, windows=None):
        """Chooses safe desktop coordinates near mouse without covering controls."""
        # Prefer ~85px to left or right of cursor
        offset_x = 90.0 if mouse_x < screen_w - 140 else -90.0
        dest_x = max(40.0, min(float(screen_w - 40), mouse_x + offset_x))
        dest_y = max(40.0, min(float(screen_h - 40), mouse_y + 15.0))

        # Check if destination falls neatly onto a window ledge
        if windows:
            for w in windows:
                if w.contains(mouse_x, mouse_y, margin=30):
                    # Sit on top ledge of active window
                    dest_x = max(w.x + 20, min(w.x + w.w - 20, mouse_x))
                    dest_y = max(24, w.y - 8)
                    break

        self.last_summon_time = time.time()
        self.is_summoning = True
        self.summon_target = (dest_x, dest_y)
        return self.summon_target


class YarnBallAutonomousController:
    """Controls autonomous periodic yarn ball spawn with strict cooldowns, focus suppression, and playful behavior."""

    def __init__(self, cooldown=300.0):
        self.cooldown = cooldown  # 5 minutes by default
        self.last_yarn_time = 0.0
        self.is_active = False

    def can_spawn(self, mode="normal"):
        if mode == "focused":
            return False
        now = time.time()
        return (now - self.last_yarn_time) >= self.cooldown

    def record_spawn(self):
        self.last_yarn_time = time.time()
        self.is_active = True

    def reset_cooldown(self):
        self.last_yarn_time = 0.0


class LivingEventManager:
    """Event selection engine ensuring non-repetitive, personality-guided, context-aware behavior."""

    def __init__(self):
        self.recent_events = deque(maxlen=8)
        self.last_discovery_time = 0.0
        self.last_toy_time = 0.0
        self.last_sleep_time = 0.0
        self.last_absence_time = 0.0
        self.last_climb_time = 0.0

    def record_event(self, event_type):
        self.recent_events.append(event_type)
        now = time.time()
        if event_type == LivingEventType.DISCOVERY:
            self.last_discovery_time = now
        elif event_type == LivingEventType.TOY_PLAY:
            self.last_toy_time = now
        elif event_type == LivingEventType.SLEEP:
            self.last_sleep_time = now
        elif event_type == LivingEventType.OFFSCREEN_ABSENCE:
            self.last_absence_time = now
        elif event_type == LivingEventType.WINDOW_EXPLORATION:
            self.last_climb_time = now

    def select_next_event(self, mode="normal", personality="calm", has_windows=True):
        """Probabilistically selects next activity avoiding repetition."""
        now = time.time()
        recent = list(self.recent_events)

        # 1. FOCUS MODE: Highly respectful, quiet presence
        if mode == "focused":
            # Discoveries very rare (only if >4 min since last)
            if now - self.last_discovery_time > 240.0 and random.random() < 0.05:
                self.record_event(LivingEventType.DISCOVERY)
                return LivingEventType.DISCOVERY
            # Sleep is brief quiet pause
            if now - self.last_sleep_time > 180.0 and random.random() < 0.10:
                self.record_event(LivingEventType.SLEEP)
                return LivingEventType.SLEEP
            # Otherwise calm roaming / sitting
            ev = LivingEventType.SIT if random.random() < 0.65 else LivingEventType.NORMAL_ROAM
            self.record_event(ev)
            return ev

        # 2. BREAK MODE: Expressive playground
        if mode == "break":
            candidates = []
            if now - self.last_toy_time > 35.0 and LivingEventType.TOY_PLAY not in recent[-2:]:
                candidates.append((LivingEventType.TOY_PLAY, 40))
            if now - self.last_discovery_time > 30.0 and LivingEventType.DISCOVERY not in recent[-2:]:
                candidates.append((LivingEventType.DISCOVERY, 35))
            if has_windows and now - self.last_climb_time > 30.0 and LivingEventType.WINDOW_EXPLORATION not in recent[-2:]:
                candidates.append((LivingEventType.WINDOW_EXPLORATION, 25))
            if now - self.last_absence_time > 120.0 and LivingEventType.OFFSCREEN_ABSENCE not in recent[-3:]:
                candidates.append((LivingEventType.OFFSCREEN_ABSENCE, 10))

            if candidates:
                total_w = sum(w for _, w in candidates)
                r = random.uniform(0, total_w)
                cum = 0
                for ev, w in candidates:
                    cum += w
                    if r <= cum:
                        self.record_event(ev)
                        return ev

            ev = LivingEventType.NORMAL_ROAM
            self.record_event(ev)
            return ev

        # 3. NORMAL ROAMING
        candidates = [(LivingEventType.NORMAL_ROAM, 45)]

        # Discoveries (cooldown 90s)
        if now - self.last_discovery_time > 90.0 and LivingEventType.DISCOVERY not in recent[-3:]:
            candidates.append((LivingEventType.DISCOVERY, 12))

        # Toys (cooldown 140s)
        if now - self.last_toy_time > 140.0 and LivingEventType.TOY_PLAY not in recent[-3:]:
            toy_weight = 14 if personality == "playful" else 8
            candidates.append((LivingEventType.TOY_PLAY, toy_weight))

        # Contextual sleep (cooldown 110s)
        if now - self.last_sleep_time > 110.0 and LivingEventType.SLEEP not in recent[-3:]:
            sleep_weight = 16 if personality == "sleepy" else (6 if personality == "energetic" else 10)
            candidates.append((LivingEventType.SLEEP, sleep_weight))

        # Window climbing exploration
        if has_windows and now - self.last_climb_time > 60.0 and LivingEventType.WINDOW_EXPLORATION not in recent[-2:]:
            climb_weight = 18 if personality in ("energetic", "playful") else 10
            candidates.append((LivingEventType.WINDOW_EXPLORATION, climb_weight))

        # Absence / "Where did Miu go?" (cooldown 300s, low probability)
        if now - self.last_absence_time > 300.0 and LivingEventType.OFFSCREEN_ABSENCE not in recent[-4:]:
            candidates.append((LivingEventType.OFFSCREEN_ABSENCE, 3))

        total_w = sum(w for _, w in candidates)
        r = random.uniform(0, total_w)
        cum = 0
        for ev, w in candidates:
            cum += w
            if r <= cum:
                self.record_event(ev)
                return ev

        self.record_event(LivingEventType.NORMAL_ROAM)
        return LivingEventType.NORMAL_ROAM


class LivingWorldManager:
    """Master coordinator integrating all living world sub-systems with the Miu desktop companion."""

    def __init__(self, app):
        self.app = app
        self.event_director = LivingEventManager()
        self.cursor_personality = CursorPersonalityManager()
        self.absence_controller = AbsenceController()
        self.sleep_manager = ContextualSleepManager()
        self.summon_manager = SummonManager()
        self.yarn_controller = YarnBallAutonomousController(cooldown=300.0)

        # Active World Item (Discovery or Toy)
        self.active_item = None
        self.item_window = None

        # State tracking
        self.current_living_event = None
        self.investigate_stage = 0
        self.investigate_timer = 0.0
        self.toy_session_timer = 0.0
        self.box_sit_timer = 0.0
        self.is_sitting_in_box = False

    def cleanup(self):
        """Destroys any active world item windows cleanly on quit."""
        if self.item_window:
            self.item_window.destroy()
            self.item_window = None
        self.active_item = None

    def tick(self, dt):
        """Called every animation frame (50ms)."""
        # Step cursor physics (hop / shake)
        self.cursor_personality.step(dt)

        # Step active item physics and window update
        if self.active_item:
            ledges = []
            if hasattr(self.app, "topology") and self.app.topology:
                for w in self.app.topology.get_climbable_windows():
                    ledges.append((w.x, w.x + w.w, w.y))

            self.active_item.step(dt, self.app.screen_w, self.app.screen_h, ledges=ledges)

            if self.item_window:
                self.item_window.update_position()

            if self.active_item.is_expired:
                self.cleanup()
                if self.is_sitting_in_box:
                    self.is_sitting_in_box = False
                if self.current_living_event in (LivingEventType.DISCOVERY, LivingEventType.TOY_PLAY):
                    self.current_living_event = None
                    self.app.pet_state.on_reached_destination(post_action="look")

        # Step absence controller
        if self.absence_controller.state == "absent":
            res = self.absence_controller.update_absence(self.app.screen_w, self.app.screen_h)
            if res:
                self._execute_absence_return(res)

        # Step cardboard box sit session
        if self.is_sitting_in_box:
            self.box_sit_timer -= dt
            if self.box_sit_timer <= 0:
                self.is_sitting_in_box = False
                self.cursor_personality.is_hopping = True
                self.cursor_personality.hop_velocity_y = -120.0
                self.cleanup()
                self.app.pet_state.on_reached_destination(post_action="stretch")

    def spawn_discovery(self, candidate_x=None, candidate_y=None):
        """Spawns an accessible, subtle discovery in desktop space."""
        if self.active_item:
            return None

        # Choose discovery type
        types = list(DiscoveryType)
        chosen_type = random.choice(types)

        # Determine coordinates (free desktop floor or window ledge)
        screen_w = self.app.screen_w
        screen_h = self.app.screen_h

        if candidate_x is None or candidate_y is None:
            # Check for window ledge
            windows = self.app.topology.get_climbable_windows() if hasattr(self.app, "topology") else []
            if windows and random.random() < 0.40:
                win = random.choice(windows)
                x = random.randint(win.x + 20, win.x + win.w - 20)
                y = max(24, win.y - 8)
            else:
                x = random.randint(50, screen_w - 50)
                y = random.randint(screen_h - 120, screen_h - 40)
        else:
            x, y = candidate_x, candidate_y

        item = WorldItem(chosen_type, x, y, is_toy=False)
        self.active_item = item
        self.item_window = WorldItemWindow(item)
        self.investigate_stage = 0
        self.investigate_timer = 0.0
        return item

    def spawn_toy(self, candidate_x=None, candidate_y=None):
        """Spawns an interactive toy on the desktop."""
        if self.active_item:
            return None

        # Choose toy type with cardboard box being especially rare
        toy_choices = [
            ToyType.YARN_BALL,
            ToyType.PAPER_BALL,
            ToyType.BUTTERFLY,
            ToyType.FEATHER_TOY,
            ToyType.LASER_DOT
        ]
        # Cardboard box is rare (~10% chance when toys are chosen)
        if random.random() < 0.12:
            chosen_type = ToyType.CARDBOARD_BOX
        else:
            chosen_type = random.choice(toy_choices)

        screen_w = self.app.screen_w
        screen_h = self.app.screen_h

        if candidate_x is None or candidate_y is None:
            # Place near Miu (100-220px away) in open space
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(90, 180)
            x = max(40, min(screen_w - 40, self.app.cat_x + math.cos(angle) * dist))
            y = max(40, min(screen_h - 50, self.app.cat_y + math.sin(angle) * dist))
        else:
            x, y = candidate_x, candidate_y

        item = WorldItem(chosen_type, x, y, is_toy=True)
        self.active_item = item
        self.item_window = WorldItemWindow(item)
        self.toy_session_timer = item.lifetime
        return item

    def spawn_yarn_ball(self, candidate_x=None, candidate_y=None):
        """Explicitly spawns an interactive yarn ball with autonomous cooldown tracking."""
        if self.active_item:
            return None

        screen_w = self.app.screen_w
        screen_h = self.app.screen_h

        if candidate_x is None or candidate_y is None:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(80, 160)
            x = max(40, min(screen_w - 40, self.app.cat_x + math.cos(angle) * dist))
            y = max(40, min(screen_h - 50, self.app.cat_y + math.sin(angle) * dist))
        else:
            x, y = candidate_x, candidate_y

        item = WorldItem(ToyType.YARN_BALL, x, y, is_toy=True)
        self.active_item = item
        self.item_window = WorldItemWindow(item)
        self.toy_session_timer = item.lifetime
        self.yarn_controller.record_spawn()
        return item

    def on_reached_item(self):
        """Called when Miu arrives at the active discovery or toy."""
        if not self.active_item:
            return

        item = self.active_item

        # 1. DISCOVERY INTERACTION
        if not item.is_toy:
            self.investigate_stage += 1
            # Random reactions: sniff, look, paw, sit beside, nudge
            reactions = ["look", "sit", "paw", "nudge", "circle"]
            act = random.choice(reactions)

            if act == "paw" or act == "nudge":
                # Nudge object slightly
                item.apply_impulse(random.uniform(-30, 30), random.uniform(-20, -5))
                self.app.pet_state.on_reached_destination(post_action="look")
            elif act == "sit":
                self.app.pet_state.on_reached_destination(post_action="sit")
            else:
                self.app.pet_state.on_reached_destination(post_action="look")

            # Naturally fade discovery after investigation
            if self.investigate_stage >= 2 or random.random() < 0.55:
                item.is_fading = True
            return

        # 2. TOY INTERACTION
        if item.item_type == ToyType.YARN_BALL:
            # Bat yarn ball in a playful direction and chase
            ivx = random.uniform(-130, 130)
            ivy = random.uniform(-60, -20)
            item.apply_impulse(ivx, ivy)
            self.app.current_destination = {
                "type": "walk",
                "pos": (max(30, min(self.app.screen_w - 30, item.x + ivx * 0.4)),
                        max(30, min(self.app.screen_h - 40, item.y + ivy * 0.4))),
                "post_action": "look"
            }
            self.app.pet_state.state = self.app.pet_state.state.RUNNING if hasattr(self.app.pet_state.state, "RUNNING") else self.app.pet_state.state.WALKING

        elif item.item_type == ToyType.PAPER_BALL:
            # Nudge paper ball
            ivx = random.uniform(-70, 70)
            ivy = random.uniform(-40, -15)
            item.apply_impulse(ivx, ivy)
            self.app.pet_state.on_reached_destination(post_action="look")

        elif item.item_type == ToyType.FEATHER_TOY:
            # Paw at feather then sit beside it
            self.app.pet_state.on_reached_destination(post_action="sit")

        elif item.item_type == ToyType.CARDBOARD_BOX:
            # Miu enters box and sits inside
            self.is_sitting_in_box = True
            self.box_sit_timer = random.uniform(7.0, 11.0)
            self.app.cat_x = item.x
            self.app.cat_y = item.y + 4
            self.app.pet_state.state = self.app.pet_state.state.SITTING
            self.app.update_window_shape_and_size()

        elif item.item_type == ToyType.BUTTERFLY:
            # Follow butterfly looking upward
            self.app.pet_state.on_reached_destination(post_action="look")

        elif item.item_type == ToyType.LASER_DOT:
            # Pounce at dot
            self.cursor_personality.is_hopping = True
            self.cursor_personality.hop_velocity_y = -90.0
            self.app.pet_state.on_reached_destination(post_action="look")

    def execute_absence(self):
        """Starts the 'Where did Miu go?' edge walk sequence."""
        target = self.absence_controller.plan_absence(
            self.app.cat_x, self.app.cat_y, self.app.screen_w, self.app.screen_h
        )
        self.app.current_destination = {
            "type": "walk",
            "pos": target,
            "post_action": "edge_exit"
        }
        self.app.pet_state.state = self.app.pet_state.state.WALKING

    def _execute_absence_return(self, return_data):
        """Executes re-entry from screen edge."""
        entry_x, entry_y = return_data["entry_pos"]
        dest_x, dest_y = return_data["dest_pos"]
        self.app.cat_x = float(entry_x)
        self.app.cat_y = float(entry_y)
        self.app.update_window_shape_and_size()
        self.app.current_destination = {
            "type": "walk",
            "pos": (dest_x, dest_y),
            "post_action": "stretch"
        }
        self.app.pet_state.state = self.app.pet_state.state.WALKING
        self.absence_controller.state = "idle"

    def execute_sleep(self):
        """Starts the contextual sleep sequence."""
        windows = self.app.topology.get_climbable_windows() if hasattr(self.app, "topology") else []
        favorite = self.app.config.get("favorite_spot")
        spot = self.sleep_manager.find_sleep_spot(
            self.app.cat_x, self.app.cat_y, self.app.screen_w, self.app.screen_h,
            windows=windows, favorite=favorite
        )
        # Walk to spot, then sit, then sleep
        self.app.current_destination = {
            "type": "walk",
            "pos": spot,
            "post_action": "sleep_sequence"
        }
        self.app.pet_state.state = self.app.pet_state.state.WALKING

    def handle_summon(self):
        """Global summon handler."""
        if not self.summon_manager.can_trigger():
            ack = self.summon_manager.acknowledge_spam()
            self.app.spawn_particles("♥", (0.96, 0.40, 0.50))
            return ack

        # If Miu is off-screen / absent, immediately recall
        if self.absence_controller.state in ("absent", "walking_to_edge"):
            ret = self.absence_controller.cancel_absence_for_summon(self.app.screen_w, self.app.screen_h)
            if ret:
                self.app.cat_x = float(ret["entry_pos"][0])
                self.app.cat_y = float(ret["entry_pos"][1])
                self.absence_controller.state = "idle"

        # Calculate safe summon target near mouse
        windows = self.app.topology.get_climbable_windows() if hasattr(self.app, "topology") else []
        target = self.summon_manager.calculate_safe_destination(
            self.app.mouse_x, self.app.mouse_y, self.app.screen_w, self.app.screen_h, windows=windows
        )

        # Clear climb mission or sleep
        self.app.climb_mission = None
        self.is_sitting_in_box = False

        # If sleeping, wake with stretch
        if self.app.pet_state.state == self.app.pet_state.state.SLEEPING:
            self.app.pet_state.state = self.app.pet_state.state.STRETCHING
            self.app.spawn_particles("!", (0.95, 0.75, 0.25))

        # Jog towards user summon destination
        self.app.current_destination = {
            "type": "walk",
            "pos": target,
            "post_action": "summon_arrival"
        }
        self.app.pet_state.state = self.app.pet_state.state.WALKING
        self.app.status_pill_text = "🐾 Here!"
        self.app.status_pill_timer = 2
        self.app.update_window_shape_and_size()
        self.app.queue_draw()
        return {"status": "ok", "msg": "Miu is on the way!"}
