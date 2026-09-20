"""
Desktop Topology & Window Discovery Engine for Miu.

Treats the desktop as an active, navigable environment:
- Discovers visible application windows using libwnck (with wmctrl fallback).
- Filters out docks, panels, dialogs, tiny widgets, and fullscreen overlays.
- Identifies navigable ledges, vertical climbing sides, and free desktop floor.
- Implements intelligent, non-repetitive destination selection with history tracking.
- Respects user workspace and cursor proximity.
"""

import os
import sys
import math
import time
import random
import subprocess
from collections import deque

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Ensure GDK_BACKEND is x11 for Wnck & absolute X11 coords
os.environ["GDK_BACKEND"] = "x11"

HAS_WNCK = False
try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Wnck", "3.0")
    from gi.repository import Gtk, Wnck
    HAS_WNCK = True
except Exception:
    HAS_WNCK = False


class WindowSurface:
    """Represents a visible application window surface on the desktop."""
    def __init__(self, win_id, title, app_name, x, y, w, h):
        self.win_id = win_id
        self.title = title or "Window"
        self.app_name = app_name or "Application"
        self.x = max(0, int(x))
        self.y = max(0, int(y))
        self.w = max(50, int(w))
        self.h = max(50, int(h))

    @property
    def top_left(self):
        return (self.x, self.y)

    @property
    def top_right(self):
        return (self.x + self.w, self.y)

    @property
    def bottom_left(self):
        return (self.x, self.y + self.h)

    @property
    def bottom_right(self):
        return (self.x + self.w, self.y + self.h)

    @property
    def top_middle(self):
        return (self.x + self.w // 2, self.y)

    def contains(self, px, py, margin=0):
        return (self.x - margin <= px <= self.x + self.w + margin and
                self.y - margin <= py <= self.y + self.h + margin)

    def get_climb_mission(self, start_x, start_y):
        """
        Builds a multi-stage climbing path:
        1. Approach base of side (left or right, whichever is closer)
        2. Ascend to top corner of window
        3. Walk along top ledge across window
        4. Sit / pause point at top ledge
        5. Descend down opposite side or step off
        """
        dist_to_left = abs(start_x - self.x)
        dist_to_right = abs(start_x - (self.x + self.w))
        climb_left = (dist_to_left <= dist_to_right)

        if climb_left:
            # Climb up left side, traverse to right
            base = (self.x - 8, min(start_y, self.y + self.h - 10))
            top_corner = (self.x - 8, self.y - 4)
            ledge_mid = (self.x + self.w // 2, self.y - 6)
            far_corner = (self.x + self.w - 12, self.y - 6)
            far_base = (self.x + self.w + 10, self.y + self.h // 2)
            side = "left"
        else:
            # Climb up right side, traverse to left
            base = (self.x + self.w + 8, min(start_y, self.y + self.h - 10))
            top_corner = (self.x + self.w + 8, self.y - 4)
            ledge_mid = (self.x + self.w // 2, self.y - 6)
            far_corner = (self.x + 12, self.y - 6)
            far_base = (self.x - 10, self.y + self.h // 2)
            side = "right"

        return {
            "type": "climb",
            "window_id": self.win_id,
            "window_title": self.title,
            "side": side,
            "waypoints": [
                {"action": "walk", "pos": base},
                {"action": "climb_up", "pos": top_corner},
                {"action": "ledge_walk", "pos": ledge_mid},
                {"action": "ledge_pause", "pos": far_corner},
                {"action": "climb_down", "pos": far_base}
            ]
        }

    def __repr__(self):
        return f"<WindowSurface '{self.title}' at ({self.x}, {self.y}, {self.w}x{self.h})>"


class DesktopTopology:
    """Discovers and tracks application windows and navigable desktop geometry."""
    def __init__(self, screen_w=1920, screen_h=1080):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.windows = []
        self.active_window = None
        self.last_scan_time = 0.0
        self.scan_interval = 2.0  # seconds between low-frequency re-scans

        self._wnck_screen = None
        self._init_wnck()

    def update_screen_bounds(self, w, h):
        self.screen_w = max(800, int(w))
        self.screen_h = max(600, int(h))

    def _init_wnck(self):
        if not HAS_WNCK:
            return
        try:
            self._wnck_screen = Wnck.Screen.get_default()
            if self._wnck_screen:
                self._wnck_screen.connect("window-opened", self._on_window_event)
                self._wnck_screen.connect("window-closed", self._on_window_event)
                self._wnck_screen.connect("active-window-changed", self._on_window_event)
        except Exception:
            self._wnck_screen = None

    def _on_window_event(self, *args):
        # Mark scan as expired so next update triggers immediate refresh
        self.last_scan_time = 0.0

    def refresh_if_needed(self):
        now = time.time()
        if now - self.last_scan_time >= self.scan_interval:
            self.refresh_windows()
            self.last_scan_time = now

    def refresh_windows(self):
        """Scans for suitable visible windows via Wnck or wmctrl fallback."""
        if HAS_WNCK and self._wnck_screen:
            try:
                self._refresh_wnck()
                return
            except Exception:
                pass

        # Fallback to wmctrl
        self._refresh_wmctrl()

    def _refresh_wnck(self):
        self._wnck_screen.force_update()
        while Gtk.events_pending():
            Gtk.main_iteration()

        raw_windows = self._wnck_screen.get_windows()
        active_w = self._wnck_screen.get_active_window()
        active_id = active_w.get_xid() if active_w else None

        surfaces = []
        for w in raw_windows:
            if not self._is_suitable_wnck_window(w):
                continue
            x, y, width, height = w.get_geometry()
            name = w.get_name() or "Window"
            app = w.get_application().get_name() if w.get_application() else ""
            surface = WindowSurface(w.get_xid(), name, app, x, y, width, height)
            surfaces.append(surface)
            if w.get_xid() == active_id:
                self.active_window = surface

        self.windows = surfaces

    def _is_suitable_wnck_window(self, w):
        if not w or w.is_minimized():
            return False

        # Only standard application windows (never dialogs, docks, or utility popups)
        try:
            wtype = w.get_window_type()
            if wtype != Wnck.WindowType.NORMAL:
                return False
        except Exception:
            pass

        name = (w.get_name() or "").lower()
        # Ignore Miu's own windows
        if "miu" in name or "oneko" in name:
            return False

        # Ignore terminal windows, security prompts, authentication dialogs, and notifications
        ignored_keywords = (
            "terminal", "console", "pty", "bash", "zsh", "alacritty",
            "kitty", "foot", "wezterm", "gnome-terminal", "prompt", "auth",
            "polkit", "dialog", "notification"
        )
        if any(k in name for k in ignored_keywords):
            return False

        x, y, width, height = w.get_geometry()
        # Ignore tiny floating popups / widgets
        if width < 200 or height < 180:
            return False

        # Ignore fullscreen windows that cover entire desktop
        if width >= self.screen_w - 20 and height >= self.screen_h - 60 and x <= 10 and y <= 40:
            return False

        # Ignore off-screen windows
        if x + width < 40 or y + height < 40 or x > self.screen_w - 40 or y > self.screen_h - 40:
            return False

        return True

    def _refresh_wmctrl(self):
        """Fallback window query using wmctrl -l -G."""
        try:
            res = subprocess.run(["wmctrl", "-l", "-G"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.0)
            if res.returncode != 0:
                return
            surfaces = []
            ignored_keywords = (
                "miu", "oneko", "terminal", "console", "pty", "bash", "zsh",
                "alacritty", "kitty", "foot", "wezterm", "gnome-terminal",
                "prompt", "auth", "polkit", "dialog", "notification"
            )
            for line in res.stdout.strip().splitlines():
                parts = line.split(None, 7)
                if len(parts) < 8:
                    continue
                win_id, desktop_id, x, y, w, h, host, title = parts
                x, y, w, h = int(x), int(y), int(w), int(h)
                name = title.lower()
                if any(k in name for k in ignored_keywords):
                    continue
                if w < 200 or h < 180:
                    continue
                if w >= self.screen_w - 20 and h >= self.screen_h - 60 and x <= 10 and y <= 40:
                    continue
                surfaces.append(WindowSurface(win_id, title, "", x, y, w, h))
            self.windows = surfaces
        except Exception:
            pass

    def get_climbable_windows(self):
        self.refresh_if_needed()
        return list(self.windows)


class DestinationPicker:
    """Intelligently selects the next destination for Miu, avoiding repetition and clutter."""
    def __init__(self, topology):
        self.topology = topology
        self.recent_positions = deque(maxlen=6)
        self.recent_window_ids = deque(maxlen=3)

    def record_destination(self, x, y, window_id=None):
        self.recent_positions.append((int(x), int(y)))
        if window_id:
            self.recent_window_ids.append(window_id)

    def is_too_close_to_recent(self, x, y, min_dist=120):
        for rx, ry in self.recent_positions:
            if math.hypot(x - rx, y - ry) < min_dist:
                return True
        return False

    def pick_next(self, cur_x, cur_y, mouse_x, mouse_y, mode="normal"):
        """
        Picks the next purposeful destination or mission.
        mode can be 'normal', 'focused', or 'break'.
        Returns a target dict:
        {"type": "walk", "pos": (x, y)} or {"type": "climb", "mission": {...}}
        """
        self.topology.refresh_if_needed()
        windows = self.topology.get_climbable_windows()
        screen_w = self.topology.screen_w
        screen_h = self.topology.screen_h

        # Available climbable windows not recently climbed
        fresh_windows = [w for w in windows if w.win_id not in self.recent_window_ids]

        # In BREAK mode: High chance to climb and explore windows
        if mode == "break" and fresh_windows and random.random() < 0.45:
            target_win = random.choice(fresh_windows)
            self.recent_window_ids.append(target_win.win_id)
            return target_win.get_climb_mission(cur_x, cur_y)

        # In FOCUS mode: Prefer top ledges of windows or quiet perimeter corners away from mouse
        if mode == "focused":
            # 50% chance to sit on a window top ledge quietly away from mouse
            if fresh_windows and random.random() < 0.50:
                target_win = random.choice(fresh_windows)
                # Ledge position away from mouse
                tx = target_win.x + target_win.w // 2
                ty = max(24, target_win.y - 8)
                if math.hypot(tx - mouse_x, ty - mouse_y) > 180:
                    self.record_destination(tx, ty, target_win.win_id)
                    return {"type": "walk", "pos": (tx, ty), "post_action": "sit"}

            # Otherwise quiet perimeter walk away from mouse
            best_p = None
            best_dist = -1
            for _ in range(12):
                px = random.randint(40, screen_w - 40)
                py = random.choice([random.randint(30, 80), random.randint(screen_h - 100, screen_h - 40)])
                d = math.hypot(px - mouse_x, py - mouse_y)
                if d > 220:
                    self.record_destination(px, py)
                    return {"type": "walk", "pos": (px, py), "post_action": "sit"}
                if d > best_dist:
                    best_dist = d
                    best_p = (px, py)

            if best_p:
                self.record_destination(best_p[0], best_p[1])
                return {"type": "walk", "pos": best_p, "post_action": "sit"}
            else:
                p = (screen_w - 50, 50)
                self.record_destination(p[0], p[1])
                return {"type": "walk", "pos": p, "post_action": "sit"}

        # NORMAL ROAMING: Weighted distribution
        # 1. Window Climb (~15% when fresh windows exist)
        if fresh_windows and random.random() < 0.18:
            target_win = random.choice(fresh_windows)
            self.recent_window_ids.append(target_win.win_id)
            return target_win.get_climb_mission(cur_x, cur_y)

        # 2. Window Approach / Ledge Patrol (~20% when windows exist)
        if fresh_windows and random.random() < 0.25:
            target_win = random.choice(fresh_windows)
            edge_choice = random.choice(["top", "left", "right"])
            if edge_choice == "top":
                pos = (random.randint(target_win.x + 20, target_win.x + target_win.w - 20), max(24, target_win.y - 8))
            elif edge_choice == "left":
                pos = (max(24, target_win.x - 16), random.randint(target_win.y + 20, target_win.y + target_win.h - 20))
            else:
                pos = (min(screen_w - 24, target_win.x + target_win.w + 16), random.randint(target_win.y + 20, target_win.y + target_win.h - 20))

            if not self.is_too_close_to_recent(pos[0], pos[1], min_dist=80):
                self.record_destination(pos[0], pos[1], target_win.win_id)
                return {"type": "walk", "pos": pos, "post_action": random.choice(["look", "sit", "idle"])}

        # 3. Nearby Desktop Wander (~45%)
        # Wander in a random direction 80-220px from current position
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(90, 240)
            nx = cur_x + math.cos(angle) * dist
            ny = cur_y + math.sin(angle) * dist
            nx = max(30, min(screen_w - 30, nx))
            ny = max(30, min(screen_h - 30, ny))

            # Avoid active mouse area
            if math.hypot(nx - mouse_x, ny - mouse_y) < 70:
                continue

            if not self.is_too_close_to_recent(nx, ny, min_dist=70):
                self.record_destination(nx, ny)
                return {"type": "walk", "pos": (int(nx), int(ny)), "post_action": random.choice(["idle", "look", "stretch", "sit"])}

        # 4. Fallback: Across Desktop Exploration (~20%)
        # Jump to a different quadrant of the screen
        quad_x = screen_w // 2
        quad_y = screen_h // 2
        dest_x = random.randint(40, quad_x - 40) if cur_x > quad_x else random.randint(quad_x + 40, screen_w - 40)
        dest_y = random.randint(40, quad_y - 40) if cur_y > quad_y else random.randint(quad_y + 40, screen_h - 40)

        self.record_destination(dest_x, dest_y)
        return {"type": "walk", "pos": (int(dest_x), int(dest_y)), "post_action": random.choice(["sit", "idle"])}
