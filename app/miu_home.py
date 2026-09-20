"""
Miu Home — Futuristic Interactive Control Center for Miu Desktop Companion.

A native GTK 3 + Cairo observatory-style console:
- Starfield particle animation & astronomical grid background
- Live animated Miu habitat viewport
- Dynamic Status panel & Mood indicators
- Spotify / MPRIS Now Playing telemetry
- Interactive Cosmetics & Personality configuration
- Pomodoro focus hub (Optional / On-Demand)
- Curated literature vault
- Desktop companion statistics
"""

import os
import sys
import math
import time
import random
from pathlib import Path

# Force X11 backend for consistency
os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import cairo

try:
    from cosmetics import COSMETIC_CATALOG, SpriteManager, CosmeticManager
    from pet_state import Personality
    from paths import SPRITE_FILE
except ImportError:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
    from cosmetics import COSMETIC_CATALOG, SpriteManager, CosmeticManager
    from pet_state import Personality
    from paths import SPRITE_FILE


class Star:
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.size = random.uniform(0.8, 2.2)
        self.alpha = random.uniform(0.2, 0.9)
        self.twinkle_speed = random.uniform(1.0, 3.5)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, dt):
        self.phase += dt * self.twinkle_speed

    def draw(self, cr):
        current_alpha = self.alpha * (0.6 + 0.4 * math.sin(self.phase))
        cr.set_source_rgba(0.85, 0.9, 1.0, current_alpha)
        cr.arc(self.x, self.y, self.size, 0, 2 * math.pi)
        cr.fill()


class MiuHomeWindow(Gtk.Window):
    def __init__(self, app=None):
        super().__init__(title="Miu Observatory Control Console")
        self.app = app
        self.set_default_size(840, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

        # Starfield
        self.stars = [Star(840, 600) for _ in range(50)]
        self.last_tick = time.time()

        # Try linking Spotify
        self.spotify = None
        try:
            from spotify import SpotifyManager
            self.spotify = SpotifyManager()
        except Exception:
            self.spotify = None

        # Build UI Structure
        self._build_ui()

        # Connect destroy callback
        self.connect("destroy", self._on_window_destroy)

        # Animation tick: 40ms (25fps)
        self._timer_id = GLib.timeout_add(40, self._on_ui_tick)

    def _build_ui(self):
        # Master overlay container
        overlay = Gtk.Overlay()
        self.add(overlay)

        # 1. Background custom Cairo canvas (Stars, grid, cosmic glow)
        self.bg_canvas = Gtk.DrawingArea()
        self.bg_canvas.connect("draw", self._on_draw_bg)
        overlay.add(self.bg_canvas)

        # 2. Main foreground Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        overlay.add_overlay(main_box)

        # Sidebar navigation
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.sidebar.set_size_request(160, 600)
        self.sidebar.set_margin_top(20)
        self.sidebar.set_margin_bottom(20)
        self.sidebar.set_margin_start(16)
        self.sidebar.set_margin_end(12)

        # Header in sidebar
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span size='large' weight='heavy' color='#00d9ff'>✦ MIU 2.0</span>")
        lbl_title.set_xalign(0.0)
        self.sidebar.pack_start(lbl_title, False, False, 10)

        # Nav Buttons
        self.nav_stack = Gtk.Stack()
        self.nav_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.nav_stack.set_transition_duration(200)

        nav_items = [
            ("home", "✦ Habitat", self._build_tab_habitat),
            ("cosmetics", "◈ Appearance", self._build_tab_cosmetics),
            ("focus", "⏱ Focus Hub", self._build_tab_focus),
            ("literature", "📖 Library", self._build_tab_library),
            ("stats", "📊 Telemetry", self._build_tab_telemetry),
            ("about", "ℹ Info", self._build_tab_info),
        ]

        self.btn_group = []
        for nav_id, label, builder in nav_items:
            btn = Gtk.Button(label=label)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.connect("clicked", lambda b, nid=nav_id: self.nav_stack.set_visible_child_name(nid))
            self.sidebar.pack_start(btn, False, False, 2)
            self.btn_group.append(btn)

            # Build content tab
            content_widget = builder()
            self.nav_stack.add_named(content_widget, nav_id)

        # Spacer in sidebar
        spacer = Gtk.Box()
        self.sidebar.pack_start(spacer, True, True, 0)

        # Summon Button at bottom of sidebar
        btn_summon = Gtk.Button(label="🐾 Summon Miu")
        btn_summon.connect("clicked", self._on_summon_clicked)
        self.sidebar.pack_start(btn_summon, False, False, 4)

        main_box.pack_start(self.sidebar, False, False, 0)
        main_box.pack_start(self.nav_stack, True, True, 10)

    def _on_summon_clicked(self, btn):
        if self.app and hasattr(self.app, "summon_miu"):
            self.app.summon_miu()
        else:
            try:
                from ipc import send_ipc_command
                send_ipc_command("summon")
            except Exception:
                pass

    def _on_draw_bg(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # 1. Deep space obsidian gradient
        pat = cairo.LinearGradient(0, 0, w, h)
        pat.add_color_stop_rgba(0.0, 0.04, 0.05, 0.08, 0.98)
        pat.add_color_stop_rgba(1.0, 0.02, 0.02, 0.04, 0.99)
        cr.set_source(pat)
        cr.paint()

        # 2. Subtle celestial radar grid
        cr.save()
        cr.set_source_rgba(0.12, 0.25, 0.35, 0.15)
        cr.set_line_width(1.0)
        step = 40
        for x in range(0, w, step):
            cr.move_to(x, 0)
            cr.line_to(x, h)
        for y in range(0, h, step):
            cr.move_to(0, y)
            cr.line_to(w, y)
        cr.stroke()

        # Subtle observatory concentric ring
        cr.set_source_rgba(0.0, 0.85, 1.0, 0.06)
        cr.arc(280, 240, 180, 0, 2 * math.pi)
        cr.stroke()
        cr.restore()

        # 3. Twinkling Stars
        for star in self.stars:
            star.draw(cr)

        return False

    def _on_ui_tick(self):
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now

        # Update stars
        for star in self.stars:
            star.update(dt)

        self.bg_canvas.queue_draw()
        if hasattr(self, "pet_canvas"):
            self.pet_canvas.queue_draw()

        # Poll spotify status
        if hasattr(self, "lbl_spotify"):
            self._update_spotify_display()

        # Update focus timer display if on focus tab
        if hasattr(self, "lbl_focus_time"):
            self._update_focus_display()

        return True

    def _on_window_destroy(self, widget):
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        if self.app:
            self.app.home_window = None

    # --- TAB 1: HABITAT (Live Viewport, Status, Spotify) ---
    def _build_tab_habitat(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(20)
        box.set_margin_end(20)

        # Top section: Viewport + Status Panel
        top_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        # 1. Habitat Viewport Frame
        vp_frame = Gtk.Frame()
        vp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vp_box.set_margin_top(8)
        vp_box.set_margin_bottom(8)
        vp_box.set_margin_start(8)
        vp_box.set_margin_end(8)

        self.pet_canvas = Gtk.DrawingArea()
        self.pet_canvas.set_size_request(240, 200)
        self.pet_canvas.connect("draw", self._on_draw_pet_habitat)
        vp_box.pack_start(self.pet_canvas, True, True, 0)
        vp_frame.add(vp_box)
        top_hbox.pack_start(vp_frame, False, False, 0)

        # 2. Telemetry / Status Deck
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        status_box.set_hexpand(True)

        self.lbl_hab_name = Gtk.Label()
        self.lbl_hab_name.set_markup("<span size='x-large' weight='bold' color='#ffffff'>Miu</span>")
        self.lbl_hab_name.set_xalign(0.0)
        status_box.pack_start(self.lbl_hab_name, False, False, 0)

        self.lbl_hab_state = Gtk.Label()
        self.lbl_hab_state.set_markup("<span color='#48cae4'>Activity: </span><span color='#90e0ef'>Observing Desktop</span>")
        self.lbl_hab_state.set_xalign(0.0)
        status_box.pack_start(self.lbl_hab_state, False, False, 0)

        self.lbl_hab_mood = Gtk.Label()
        self.lbl_hab_mood.set_markup("<span color='#48cae4'>Mood: </span><span color='#90e0ef'>Curious &amp; Serene</span>")
        self.lbl_hab_mood.set_xalign(0.0)
        status_box.pack_start(self.lbl_hab_mood, False, False, 0)

        # Quick action buttons
        act_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_yarn = Gtk.Button(label="🧶 Toss Yarn")
        btn_yarn.connect("clicked", self._on_toss_yarn_clicked)
        act_box.pack_start(btn_yarn, False, False, 0)

        btn_nap = Gtk.Button(label="🌙 Rest / Nap")
        btn_nap.connect("clicked", self._on_nap_clicked)
        act_box.pack_start(btn_nap, False, False, 0)

        status_box.pack_start(act_box, False, False, 8)
        top_hbox.pack_start(status_box, True, True, 0)
        box.pack_start(top_hbox, False, False, 0)

        # Bottom section: Spotify MPRIS Display
        spot_frame = Gtk.Frame(label="Now Playing (MPRIS)")
        spot_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        spot_box.set_margin_top(10)
        spot_box.set_margin_bottom(10)
        spot_box.set_margin_start(12)
        spot_box.set_margin_end(12)

        self.lbl_spotify = Gtk.Label()
        self.lbl_spotify.set_markup("<span color='#888899'>Scanning audio telemetry...</span>")
        self.lbl_spotify.set_xalign(0.0)
        spot_box.pack_start(self.lbl_spotify, True, True, 0)

        spot_frame.add(spot_box)
        box.pack_start(spot_frame, False, False, 10)

        return box

    def _on_toss_yarn_clicked(self, btn):
        if self.app and hasattr(self.app, "living_world"):
            item = self.app.living_world.spawn_yarn_ball()
            if item:
                self.app.current_destination = {
                    "type": "walk",
                    "pos": (item.x, item.y),
                    "post_action": "investigate_item"
                }
        else:
            try:
                from ipc import send_ipc_command
                send_ipc_command("yarn")
            except Exception:
                pass

    def _on_nap_clicked(self, btn):
        if self.app and hasattr(self.app, "living_world"):
            self.app.living_world.execute_sleep()

    def _on_draw_pet_habitat(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # Frosted glass viewport inside console
        cr.set_source_rgba(0.08, 0.12, 0.18, 0.85)
        cr.rectangle(0, 0, w, h)
        cr.fill_preserve()
        cr.set_source_rgba(0.0, 0.85, 1.0, 0.3)
        cr.set_line_width(1.2)
        cr.stroke()

        # Habitat platform
        cr.set_source_rgba(0.15, 0.22, 0.30, 0.9)
        cr.rectangle(20, h - 35, w - 40, 8)
        cr.fill()

        # Render pet
        sprites = getattr(self.app, "sprites", None)
        if not sprites and os.path.exists(SPRITE_FILE):
            try:
                theme = getattr(self.app, "config", {}).get("cat_theme", "classic") if self.app else "classic"
                sprites = SpriteManager(SPRITE_FILE, scale=2.0, theme=theme)
            except Exception:
                sprites = None

        scale = 2.0
        cx = int(w // 2 - 16 * scale)
        cy = int(h - 35 - 32 * scale)

        if sprites:
            frame = sprites.get_frame("idle", 0)
            if frame:
                scaled = frame.scale_simple(int(32 * scale), int(32 * scale), GdkPixbuf.InterpType.NEAREST)
                Gdk.cairo_set_source_pixbuf(cr, scaled, cx, cy)
                cr.paint()

        # Overlay accessories
        cosmetics = getattr(self.app, "cosmetics", None)
        if not cosmetics:
            cosmetics = CosmeticManager()

        config = getattr(self.app, "config", {}) if self.app else {}
        exp = config.get("cat_expression", "normal")
        acc = config.get("cat_accessory", "none")

        cosmetics.draw_expression(cr, exp, "idle", cx, cy, scale)
        cosmetics.draw_accessory(cr, acc, "idle", cx, cy, scale)

        return True

    def _update_spotify_display(self):
        if not self.spotify:
            self.lbl_spotify.set_markup("<span color='#777788'>🎵 Spotify integration offline</span>")
            return

        track = self.spotify.get_current_track()
        if track and track.get("is_playing"):
            title = track.get("title", "Unknown Track")
            artist = track.get("artist", "Unknown Artist")
            album = track.get("album", "")
            text = f"▶ <b>{title}</b> — <span color='#00d9ff'>{artist}</span> ({album})"
            self.lbl_spotify.set_markup(text)
        else:
            self.lbl_spotify.set_markup("<span color='#777788'>⏸ No media currently broadcasting</span>")

    # --- TAB 2: COSMETICS ---
    def _build_tab_cosmetics(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(20)
        box.set_margin_end(20)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='large' weight='bold' color='#ffffff'>Pet Customization</span>")
        lbl.set_xalign(0.0)
        box.pack_start(lbl, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)

        # 1. Coat Theme
        lbl_t = Gtk.Label(label="Coat Theme:")
        lbl_t.set_xalign(0.0)
        grid.attach(lbl_t, 0, 0, 1, 1)

        theme_store = Gtk.ListStore(str, str)
        for t in COSMETIC_CATALOG["themes"]:
            theme_store.append([t["id"], t["name"]])
        cb_theme = Gtk.ComboBox.new_with_model(theme_store)
        r1 = Gtk.CellRendererText()
        cb_theme.pack_start(r1, True)
        cb_theme.add_attribute(r1, "text", 1)

        cur_theme = self.app.config.get("cat_theme", "classic") if self.app else "classic"
        for i, row in enumerate(theme_store):
            if row[0] == cur_theme:
                cb_theme.set_active(i)
                break
        cb_theme.connect("changed", self._on_theme_changed)
        grid.attach(cb_theme, 1, 0, 1, 1)

        # 2. Accessory
        lbl_a = Gtk.Label(label="Accessory:")
        lbl_a.set_xalign(0.0)
        grid.attach(lbl_a, 0, 1, 1, 1)

        acc_store = Gtk.ListStore(str, str)
        for a in COSMETIC_CATALOG["accessories"]:
            acc_store.append([a["id"], a["name"]])
        cb_acc = Gtk.ComboBox.new_with_model(acc_store)
        r2 = Gtk.CellRendererText()
        cb_acc.pack_start(r2, True)
        cb_acc.add_attribute(r2, "text", 1)

        cur_acc = self.app.config.get("cat_accessory", "none") if self.app else "none"
        for i, row in enumerate(acc_store):
            if row[0] == cur_acc:
                cb_acc.set_active(i)
                break
        cb_acc.connect("changed", self._on_acc_changed)
        grid.attach(cb_acc, 1, 1, 1, 1)

        # 3. Expression
        lbl_e = Gtk.Label(label="Expression:")
        lbl_e.set_xalign(0.0)
        grid.attach(lbl_e, 0, 2, 1, 1)

        exp_store = Gtk.ListStore(str, str)
        for e in COSMETIC_CATALOG["expressions"]:
            exp_store.append([e["id"], e["name"]])
        cb_exp = Gtk.ComboBox.new_with_model(exp_store)
        r3 = Gtk.CellRendererText()
        cb_exp.pack_start(r3, True)
        cb_exp.add_attribute(r3, "text", 1)

        cur_exp = self.app.config.get("cat_expression", "normal") if self.app else "normal"
        for i, row in enumerate(exp_store):
            if row[0] == cur_exp:
                cb_exp.set_active(i)
                break
        cb_exp.connect("changed", self._on_exp_changed)
        grid.attach(cb_exp, 1, 2, 1, 1)

        box.pack_start(grid, False, False, 0)
        return box

    def _on_theme_changed(self, combo):
        iter_ = combo.get_active_iter()
        if iter_ and self.app:
            val = combo.get_model()[iter_][0]
            self.app.config["cat_theme"] = val
            if hasattr(self.app, "sprites"):
                self.app.sprites.set_theme(val)
            self.app.save_config()
            self.app.queue_draw()

    def _on_acc_changed(self, combo):
        iter_ = combo.get_active_iter()
        if iter_ and self.app:
            val = combo.get_model()[iter_][0]
            self.app.config["cat_accessory"] = val
            self.app.save_config()
            self.app.queue_draw()

    def _on_exp_changed(self, combo):
        iter_ = combo.get_active_iter()
        if iter_ and self.app:
            val = combo.get_model()[iter_][0]
            self.app.config["cat_expression"] = val
            self.app.save_config()
            self.app.queue_draw()

    # --- TAB 3: FOCUS HUB ---
    def _build_tab_focus(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(20)
        box.set_margin_end(20)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='large' weight='bold' color='#ffffff'>Optional Focus Hub</span>")
        lbl.set_xalign(0.0)
        box.pack_start(lbl, False, False, 0)

        # Toggle mode
        self.chk_pom_mode = Gtk.CheckButton(label="Enable Focus Mode (Shows timer on Miu)")
        is_enabled = self.app.config.get("pomodoro_enabled", False) if self.app else False
        self.chk_pom_mode.set_active(is_enabled)
        self.chk_pom_mode.connect("toggled", self._on_pom_toggle)
        box.pack_start(self.chk_pom_mode, False, False, 0)

        # Timer Readout
        self.lbl_focus_time = Gtk.Label()
        self.lbl_focus_time.set_markup("<span size='xx-large' weight='bold' color='#00d9ff'>45:00</span>")
        box.pack_start(self.lbl_focus_time, False, False, 10)

        # Controls
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_start = Gtk.Button(label="Start Focus")
        btn_start.connect("clicked", lambda w: self.app.start_focus_session() if self.app else None)
        btn_box.pack_start(btn_start, False, False, 0)

        btn_pause = Gtk.Button(label="Pause")
        btn_pause.connect("clicked", lambda w: self.app.pomodoro.pause() if self.app else None)
        btn_box.pack_start(btn_pause, False, False, 0)

        btn_resume = Gtk.Button(label="Resume")
        btn_resume.connect("clicked", lambda w: self.app.pomodoro.resume() if self.app else None)
        btn_box.pack_start(btn_resume, False, False, 0)

        btn_reset = Gtk.Button(label="Reset")
        btn_reset.connect("clicked", lambda w: self.app.reset_session() if self.app and hasattr(self.app, "reset_session") else None)
        btn_box.pack_start(btn_reset, False, False, 0)

        box.pack_start(btn_box, False, False, 0)
        return box

    def _on_pom_toggle(self, chk):
        if self.app:
            self.app.config["pomodoro_enabled"] = chk.get_active()
            self.app.save_config()
            self.app.tray.update_menu()
            self.app.update_window_shape_and_size()
            self.app.queue_draw()

    def _update_focus_display(self):
        if self.app and hasattr(self.app, "pomodoro"):
            t_str = self.app.pomodoro.get_time_string()
            phase = self.app.pomodoro.phase
            color = "#00d9ff" if phase == "FOCUS" else ("#70e000" if "BREAK" in phase else "#888899")
            self.lbl_focus_time.set_markup(f"<span size='xx-large' weight='bold' color='{color}'>{t_str}</span>")

    # --- TAB 4: LIBRARY ---
    def _build_tab_library(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(20)
        box.set_margin_end(20)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='large' weight='bold' color='#ffffff'>Literary Works Archive</span>")
        lbl.set_xalign(0.0)
        box.pack_start(lbl, False, False, 0)

        # Scrolled view of saved quotes
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(340)
        store = Gtk.ListStore(str, str)

        if self.app and hasattr(self.app, "literary"):
            for w in self.app.literary.works:
                store.append([f"“{w.get('text', '')}”", f"— {w.get('author', '')}"])

        tv = Gtk.TreeView(model=store)
        r_text = Gtk.CellRendererText()
        r_text.set_property("wrap-mode", 2)
        r_text.set_property("wrap-width", 380)
        c1 = Gtk.TreeViewColumn("Quote", r_text, text=0)
        c1.set_expand(True)
        tv.append_column(c1)

        r_author = Gtk.CellRendererText()
        c2 = Gtk.TreeViewColumn("Author", r_author, text=1)
        tv.append_column(c2)

        scrolled.add(tv)
        box.pack_start(scrolled, True, True, 0)
        return box

    # --- TAB 5: TELEMETRY & STATS ---
    def _build_tab_telemetry(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(20)
        box.set_margin_end(20)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='large' weight='bold' color='#ffffff'>Companion Telemetry</span>")
        lbl.set_xalign(0.0)
        box.pack_start(lbl, False, False, 0)

        summary = self.app.pomodoro.get_stats_summary() if self.app else {
            "sessions": 0, "focus_time": "0m", "drops_read": 0
        }

        f1 = Gtk.Label()
        f1.set_markup(f"<span color='#90e0ef'>Completed Focus Sessions:</span> <b>{summary.get('sessions', 0)}</b>")
        f1.set_xalign(0.0)
        box.pack_start(f1, False, False, 0)

        f2 = Gtk.Label()
        f2.set_markup(f"<span color='#90e0ef'>Total Focus Elapsed:</span> <b>{summary.get('focus_time', '0m')}</b>")
        f2.set_xalign(0.0)
        box.pack_start(f2, False, False, 0)

        f3 = Gtk.Label()
        f3.set_markup(f"<span color='#90e0ef'>Literary Drops Experienced:</span> <b>{summary.get('drops_read', 0)}</b>")
        f3.set_xalign(0.0)
        box.pack_start(f3, False, False, 0)

        return box

    # --- TAB 6: INFO ---
    def _build_tab_info(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(20)
        box.set_margin_end(20)

        lbl = Gtk.Label()
        lbl.set_markup("<span size='x-large' weight='heavy' color='#00d9ff'>Miu Desktop Companion</span>")
        lbl.set_xalign(0.0)
        box.pack_start(lbl, False, False, 0)

        desc = Gtk.Label()
        desc.set_markup(
            "Version 2.1.0\n\n"
            "A tiny futuristic desktop companion that lives quietly on your Linux screen.\n"
            "Pomodoro is optional. Literary drops are one-line. Company is permanent.\n\n"
            "<b>Controls:</b>\n"
            "• Drag Miu with mouse left click\n"
            "• Summon with Ctrl+M or <tt>hi miu summon</tt>\n"
            "• Launch Home: <tt>miu --home</tt>\n"
            "• Enable Focus: <tt>miu --pomodoro</tt>\n\n"
            "<span color='#666677'>Initially based on Oneko. Customized &amp; evolved by Vaibhava.</span>"
        )
        desc.set_xalign(0.0)
        desc.set_line_wrap(True)
        box.pack_start(desc, False, False, 0)

        return box


def open_home_window(app=None):
    win = MiuHomeWindow(app)
    win.show_all()
    return win


if __name__ == "__main__":
    win = open_home_window()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
