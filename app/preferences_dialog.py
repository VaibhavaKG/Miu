"""
Preferences & Character Customization Window for Oneko Desktop Companion.

A compact, character-editor style interface:
- Pet: Name, Personality
- Appearance: Body Theme, Accessory, Expression, with Live Cairo Preview
- Behaviour: Movement Speed, Activity Level
- Desktop: Scale, Always-On-Top, Timer Badge Visibility
- Focus: 45-min Default Focus Duration, Short Break, Long Break, Sound Effects
- Literature: Drops Mode (Breaks Only, Occasional, Off), Saved Drops Inspector
- Statistics: Today's Focus and Drops Summary
"""

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import cairo

from cosmetics import COSMETIC_CATALOG, CosmeticManager, SpriteManager
from pet_state import Personality


class PreferencesDialog(Gtk.Window):
    def __init__(self, app):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.app = app
        self.config = app.config
        self.cosmetics = app.cosmetics
        self.sprites = app.sprites

        self.set_title(f"Miu - Customize {self.config.get('pet_name', 'Miu')}")
        self.set_default_size(480, 540)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_modal(True)
        self.set_transient_for(app)

        # Main layout
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_vbox.set_margin_top(16)
        main_vbox.set_margin_bottom(16)
        main_vbox.set_margin_start(20)
        main_vbox.set_margin_end(20)
        self.add(main_vbox)

        # Character Live Preview Area at top
        preview_frame = Gtk.Frame()
        preview_frame.set_shadow_type(Gtk.ShadowType.IN)
        preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        preview_box.set_margin_top(10)
        preview_box.set_margin_bottom(10)
        preview_box.set_margin_start(16)
        preview_box.set_margin_end(16)

        self.preview_area = Gtk.DrawingArea()
        self.preview_area.set_size_request(80, 80)
        self.preview_area.connect("draw", self._on_preview_draw)
        preview_box.pack_start(self.preview_area, False, False, 0)

        preview_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        preview_info.set_valign(Gtk.Align.CENTER)
        self.lbl_preview_title = Gtk.Label()
        self.lbl_preview_title.set_xalign(0.0)
        self.lbl_preview_title.set_markup(f"<b>{self.config.get('pet_name', 'Miu')}</b>")
        preview_info.pack_start(self.lbl_preview_title, False, False, 0)

        self.lbl_preview_sub = Gtk.Label()
        self.lbl_preview_sub.set_xalign(0.0)
        preview_info.pack_start(self.lbl_preview_sub, False, False, 0)

        preview_box.pack_start(preview_info, True, True, 0)
        preview_frame.add(preview_box)
        main_vbox.pack_start(preview_frame, False, False, 0)

        # Notebook for sections
        notebook = Gtk.Notebook()
        main_vbox.pack_start(notebook, True, True, 0)

        notebook.append_page(self._build_pet_tab(), Gtk.Label(label="Pet"))
        notebook.append_page(self._build_appearance_tab(), Gtk.Label(label="Appearance"))
        notebook.append_page(self._build_behaviour_tab(), Gtk.Label(label="Behaviour"))
        notebook.append_page(self._build_focus_tab(), Gtk.Label(label="Focus"))
        notebook.append_page(self._build_literature_tab(), Gtk.Label(label="Literature"))
        notebook.append_page(self._build_stats_tab(), Gtk.Label(label="Stats"))
        notebook.append_page(self._build_about_tab(), Gtk.Label(label="About"))

        # Bottom buttons: Close / Done
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_done = Gtk.Button(label="Done")
        btn_done.connect("clicked", lambda w: self.destroy())
        btn_box.pack_start(btn_done, False, False, 0)
        main_vbox.pack_start(btn_box, False, False, 0)

        self._update_preview_label()
        self.show_all()

    def _update_preview_label(self):
        name = self.config.get("pet_name", "Miu")
        personality = self.config.get("personality", "calm").capitalize()
        theme_id = self.config.get("cat_theme", "classic")
        accessory_id = self.config.get("cat_accessory", "none")
        self.lbl_preview_title.set_markup(f"<span size='large' weight='bold'>{name}</span>")
        self.lbl_preview_sub.set_markup(f"<span size='small' color='#777'>Personality: {personality} • Theme: {theme_id.capitalize()}</span>")
        self.preview_area.queue_draw()

    def _on_preview_draw(self, widget, cr):
        # Soft dark preview background
        cr.set_source_rgba(0.12, 0.13, 0.15, 1.0)
        cr.paint()

        # Center sprite in preview
        scale = 2.0
        size = int(32 * scale)
        cx = (80 - size) // 2
        cy = (80 - size) // 2

        # Draw cat sprite with current theme
        frame = self.sprites.get_frame("idle", 0)
        # Scale to 2.0x for preview
        scaled_frame = frame.scale_simple(size, size, GdkPixbuf.InterpType.NEAREST)
        Gdk.cairo_set_source_pixbuf(cr, scaled_frame, cx, cy)
        cr.paint()

        # Overlay expression & accessory
        exp = self.config.get("cat_expression", "normal")
        acc = self.config.get("cat_accessory", "none")
        self.cosmetics.draw_expression(cr, exp, "idle", cx, cy, scale)
        self.cosmetics.draw_accessory(cr, acc, "idle", cx, cy, scale)
        return True

    def _build_pet_tab(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        grid.set_margin_start(16)
        grid.set_margin_end(16)

        # Pet Name
        lbl_name = Gtk.Label(label="Pet Name:")
        lbl_name.set_xalign(0.0)
        grid.attach(lbl_name, 0, 0, 1, 1)

        ent_name = Gtk.Entry()
        ent_name.set_text(self.config.get("pet_name", "Miu"))
        ent_name.connect("changed", self._on_name_changed)
        grid.attach(ent_name, 1, 0, 1, 1)

        # Personality
        lbl_pers = Gtk.Label(label="Personality:")
        lbl_pers.set_xalign(0.0)
        grid.attach(lbl_pers, 0, 1, 1, 1)

        pers_store = Gtk.ListStore(str, str)
        for key, p in Personality.PROFILES.items():
            pers_store.append([key, p["name"]])

        combo_pers = Gtk.ComboBox.new_with_model(pers_store)
        renderer = Gtk.CellRendererText()
        combo_pers.pack_start(renderer, True)
        combo_pers.add_attribute(renderer, "text", 1)

        current_pers = self.config.get("personality", "calm")
        for i, row in enumerate(pers_store):
            if row[0] == current_pers:
                combo_pers.set_active(i)
                break
        combo_pers.connect("changed", self._on_personality_changed)
        grid.attach(combo_pers, 1, 1, 1, 1)

        # Description of personality
        self.lbl_pers_desc = Gtk.Label()
        self.lbl_pers_desc.set_xalign(0.0)
        self.lbl_pers_desc.set_line_wrap(True)
        self._update_personality_desc(current_pers)
        grid.attach(self.lbl_pers_desc, 0, 2, 2, 1)

        return grid

    def _update_personality_desc(self, key):
        descs = {
            "calm": "Calm: Slower, dignified movements, longer restful pauses, and gentle sitting.",
            "playful": "Playful: Frequent reactions, occasional fast dashes, and inquisitive curiosity.",
            "sleepy": "Sleepy: Frequent peaceful naps, slow relaxed movement, and high calmness.",
            "energetic": "Energetic: High movement frequency, eager edge exploring, and quick strides.",
            "focused": "Focused: Quiet, steady presence, minimal movement; ideal for deep work.",
        }
        text = descs.get(key, "")
        self.lbl_pers_desc.set_markup(f"<span size='small' color='#666'><i>{text}</i></span>")

    def _on_name_changed(self, entry):
        name = entry.get_text().strip() or "Miu"
        self.config["pet_name"] = name
        self.app.save_config()
        self._update_preview_label()

    def _on_personality_changed(self, combo):
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter:
            key = model[tree_iter][0]
            self.config["personality"] = key
            self.app.pet_state.set_personality(key)
            self.app.save_config()
            self._update_personality_desc(key)
            self._update_preview_label()

    def _build_appearance_tab(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        grid.set_margin_start(16)
        grid.set_margin_end(16)

        # Body Theme
        lbl_theme = Gtk.Label(label="Coat / Skin:")
        lbl_theme.set_xalign(0.0)
        grid.attach(lbl_theme, 0, 0, 1, 1)

        theme_store = Gtk.ListStore(str, str)
        for t in COSMETIC_CATALOG["themes"]:
            theme_store.append([t["id"], t["name"]])
        combo_theme = Gtk.ComboBox.new_with_model(theme_store)
        r1 = Gtk.CellRendererText()
        combo_theme.pack_start(r1, True)
        combo_theme.add_attribute(r1, "text", 1)

        cur_theme = self.config.get("cat_theme", "classic")
        for i, row in enumerate(theme_store):
            if row[0] == cur_theme:
                combo_theme.set_active(i)
                break
        combo_theme.connect("changed", self._on_theme_changed)
        grid.attach(combo_theme, 1, 0, 1, 1)

        # Accessory
        lbl_acc = Gtk.Label(label="Accessory:")
        lbl_acc.set_xalign(0.0)
        grid.attach(lbl_acc, 0, 1, 1, 1)

        acc_store = Gtk.ListStore(str, str)
        for a in COSMETIC_CATALOG["accessories"]:
            acc_store.append([a["id"], a["name"]])
        combo_acc = Gtk.ComboBox.new_with_model(acc_store)
        r2 = Gtk.CellRendererText()
        combo_acc.pack_start(r2, True)
        combo_acc.add_attribute(r2, "text", 1)

        cur_acc = self.config.get("cat_accessory", "none")
        for i, row in enumerate(acc_store):
            if row[0] == cur_acc:
                combo_acc.set_active(i)
                break
        combo_acc.connect("changed", self._on_accessory_changed)
        grid.attach(combo_acc, 1, 1, 1, 1)

        # Eyes / Expression
        lbl_exp = Gtk.Label(label="Expression:")
        lbl_exp.set_xalign(0.0)
        grid.attach(lbl_exp, 0, 2, 1, 1)

        exp_store = Gtk.ListStore(str, str)
        for e in COSMETIC_CATALOG["expressions"]:
            exp_store.append([e["id"], e["name"]])
        combo_exp = Gtk.ComboBox.new_with_model(exp_store)
        r3 = Gtk.CellRendererText()
        combo_exp.pack_start(r3, True)
        combo_exp.add_attribute(r3, "text", 1)

        cur_exp = self.config.get("cat_expression", "normal")
        for i, row in enumerate(exp_store):
            if row[0] == cur_exp:
                combo_exp.set_active(i)
                break
        combo_exp.connect("changed", self._on_expression_changed)
        grid.attach(combo_exp, 1, 2, 1, 1)

        return grid

    def _on_theme_changed(self, combo):
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter:
            val = model[tree_iter][0]
            self.config["cat_theme"] = val
            self.sprites.set_theme(val)
            self.app.save_config()
            self._update_preview_label()
            self.app.queue_draw()

    def _on_accessory_changed(self, combo):
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter:
            val = model[tree_iter][0]
            self.config["cat_accessory"] = val
            self.app.save_config()
            self._update_preview_label()
            self.app.queue_draw()

    def _on_expression_changed(self, combo):
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter:
            val = model[tree_iter][0]
            self.config["cat_expression"] = val
            self.app.save_config()
            self._update_preview_label()
            self.app.queue_draw()

    def _build_behaviour_tab(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        grid.set_margin_start(16)
        grid.set_margin_end(16)

        # Movement Speed
        lbl_speed = Gtk.Label(label="Movement Speed:")
        lbl_speed.set_xalign(0.0)
        grid.attach(lbl_speed, 0, 0, 1, 1)

        speed_store = Gtk.ListStore(str, str)
        speed_store.append(["slow", "Slow"])
        speed_store.append(["normal", "Normal"])
        speed_store.append(["fast", "Quick"])
        combo_speed = Gtk.ComboBox.new_with_model(speed_store)
        r = Gtk.CellRendererText()
        combo_speed.pack_start(r, True)
        combo_speed.add_attribute(r, "text", 1)

        cur_speed = self.config.get("movement_speed", "normal")
        for i, row in enumerate(speed_store):
            if row[0] == cur_speed:
                combo_speed.set_active(i)
                break
        combo_speed.connect("changed", self._on_speed_changed)
        grid.attach(combo_speed, 1, 0, 1, 1)

        # Pet Scale
        lbl_scale = Gtk.Label(label="Pet Size:")
        lbl_scale.set_xalign(0.0)
        grid.attach(lbl_scale, 0, 1, 1, 1)

        scale_adj = Gtk.Adjustment(
            value=self.config.get("cat_scale", 1.25),
            lower=1.0,
            upper=2.25,
            step_increment=0.25,
            page_increment=0.25,
        )
        scale_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=scale_adj)
        scale_scale.set_digits(2)
        scale_scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale_scale.set_hexpand(True)
        scale_scale.connect("value-changed", self._on_scale_changed)
        grid.attach(scale_scale, 1, 1, 1, 1)

        # Always On Top
        lbl_ontop = Gtk.Label(label="Always On Top:")
        lbl_ontop.set_xalign(0.0)
        grid.attach(lbl_ontop, 0, 2, 1, 1)

        chk_ontop = Gtk.CheckButton()
        chk_ontop.set_active(self.config.get("always_on_top", True))
        chk_ontop.connect("toggled", lambda w: self._on_ontop_toggled(w.get_active()))
        grid.attach(chk_ontop, 1, 2, 1, 1)

        # Reset Position button
        lbl_pos = Gtk.Label(label="Desktop Position:")
        lbl_pos.set_xalign(0.0)
        grid.attach(lbl_pos, 0, 3, 1, 1)

        btn_reset_pos = Gtk.Button(label="Center Pet on Screen")
        btn_reset_pos.connect("clicked", lambda w: self.app.recenter_pet())
        grid.attach(btn_reset_pos, 1, 3, 1, 1)

        return grid

    def _on_speed_changed(self, combo):
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter:
            val = model[tree_iter][0]
            self.config["movement_speed"] = val
            self.app.save_config()

    def _on_scale_changed(self, scale_widget):
        val = round(scale_widget.get_value(), 2)
        self.config["cat_scale"] = val
        self.app.cat_pixel_size = int(32 * val)
        self.sprites.set_scale(val)
        self.app.speed = 10.0 * val
        self.app.save_config()
        self.app.update_window_shape_and_size()
        self.app.queue_draw()

    def _on_ontop_toggled(self, active):
        self.config["always_on_top"] = active
        self.app.set_keep_above(active)
        self.app.save_config()

    def _build_focus_tab(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        grid.set_margin_start(16)
        grid.set_margin_end(16)

        # Focus duration (default 45)
        lbl_focus = Gtk.Label(label="Focus Duration (min):")
        lbl_focus.set_xalign(0.0)
        grid.attach(lbl_focus, 0, 0, 1, 1)

        spn_focus = Gtk.SpinButton.new_with_range(1, 120, 1)
        spn_focus.set_value(self.config.get("focus_duration_min", 45))
        spn_focus.connect("value-changed", self._on_focus_dur_changed)
        grid.attach(spn_focus, 1, 0, 1, 1)

        # Short break
        lbl_short = Gtk.Label(label="Short Break (min):")
        lbl_short.set_xalign(0.0)
        grid.attach(lbl_short, 0, 1, 1, 1)

        spn_short = Gtk.SpinButton.new_with_range(1, 30, 1)
        spn_short.set_value(self.config.get("short_break_min", 5))
        spn_short.connect("value-changed", self._on_short_dur_changed)
        grid.attach(spn_short, 1, 1, 1, 1)

        # Long break
        lbl_long = Gtk.Label(label="Long Break (min):")
        lbl_long.set_xalign(0.0)
        grid.attach(lbl_long, 0, 2, 1, 1)

        spn_long = Gtk.SpinButton.new_with_range(1, 60, 1)
        spn_long.set_value(self.config.get("long_break_min", 15))
        spn_long.connect("value-changed", self._on_long_dur_changed)
        grid.attach(spn_long, 1, 2, 1, 1)

        # Timer Badge Visibility
        lbl_badge = Gtk.Label(label="Timer Badge:")
        lbl_badge.set_xalign(0.0)
        grid.attach(lbl_badge, 0, 3, 1, 1)

        badge_store = Gtk.ListStore(str, str)
        badge_store.append(["always", "Always Visible"])
        badge_store.append(["hover", "Show on Hover"])
        badge_store.append(["hidden", "Hidden"])
        combo_badge = Gtk.ComboBox.new_with_model(badge_store)
        r = Gtk.CellRendererText()
        combo_badge.pack_start(r, True)
        combo_badge.add_attribute(r, "text", 1)

        cur_badge = self.config.get("badge_display", "always")
        for i, row in enumerate(badge_store):
            if row[0] == cur_badge:
                combo_badge.set_active(i)
                break
        combo_badge.connect("changed", self._on_badge_changed)
        grid.attach(combo_badge, 1, 3, 1, 1)

        # Sound effects
        lbl_sound = Gtk.Label(label="Audio Chimes:")
        lbl_sound.set_xalign(0.0)
        grid.attach(lbl_sound, 0, 4, 1, 1)

        chk_sound = Gtk.CheckButton()
        chk_sound.set_active(self.config.get("sound_enabled", True))
        chk_sound.connect("toggled", lambda w: self._on_sound_toggled(w.get_active()))
        grid.attach(chk_sound, 1, 4, 1, 1)

        return grid

    def _on_focus_dur_changed(self, spin):
        val = int(spin.get_value())
        self.config["focus_duration_min"] = val
        self.app.pomodoro.update_durations(val, self.config.get("short_break_min", 5), self.config.get("long_break_min", 15))
        self.app.save_config()

    def _on_short_dur_changed(self, spin):
        val = int(spin.get_value())
        self.config["short_break_min"] = val
        self.app.pomodoro.update_durations(self.config.get("focus_duration_min", 45), val, self.config.get("long_break_min", 15))
        self.app.save_config()

    def _on_long_dur_changed(self, spin):
        val = int(spin.get_value())
        self.config["long_break_min"] = val
        self.app.pomodoro.update_durations(self.config.get("focus_duration_min", 45), self.config.get("short_break_min", 5), val)
        self.app.save_config()

    def _on_badge_changed(self, combo):
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter:
            val = model[tree_iter][0]
            self.config["badge_display"] = val
            self.app.save_config()
            self.app.update_window_shape_and_size()
            self.app.queue_draw()

    def _on_sound_toggled(self, active):
        self.config["sound_enabled"] = active
        self.app.save_config()

    def _build_literature_tab(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)

        # Mode selector
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_mode = Gtk.Label(label="Delivery Mode:")
        lbl_mode.set_xalign(0.0)
        hbox.pack_start(lbl_mode, False, False, 0)

        mode_store = Gtk.ListStore(str, str)
        mode_store.append(["breaks_only", "Breaks Only (Default)"])
        mode_store.append(["occasional", "Occasional"])
        mode_store.append(["off", "Off"])
        combo_mode = Gtk.ComboBox.new_with_model(mode_store)
        r = Gtk.CellRendererText()
        combo_mode.pack_start(r, True)
        combo_mode.add_attribute(r, "text", 1)

        cur_mode = self.config.get("literary_mode", "breaks_only")
        for i, row in enumerate(mode_store):
            if row[0] == cur_mode:
                combo_mode.set_active(i)
                break
        combo_mode.connect("changed", self._on_literary_mode_changed)
        hbox.pack_start(combo_mode, True, True, 0)
        vbox.pack_start(hbox, False, False, 0)

        # Saved quotes list
        lbl_saved = Gtk.Label(label="Saved Literary Lines:")
        lbl_saved.set_xalign(0.0)
        vbox.pack_start(lbl_saved, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(160)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.saved_store = Gtk.ListStore(str, str)
        for item in self.app.literary.saved_works:
            self.saved_store.append([f"“{item['text']}”", f"— {item['author']}"])

        treeview = Gtk.TreeView(model=self.saved_store)
        r_text = Gtk.CellRendererText()
        r_text.set_property("wrap-mode", 2)
        r_text.set_property("wrap-width", 280)
        col1 = Gtk.TreeViewColumn("Quote", r_text, text=0)
        col1.set_expand(True)
        treeview.append_column(col1)

        r_author = Gtk.CellRendererText()
        col2 = Gtk.TreeViewColumn("Author", r_author, text=1)
        treeview.append_column(col2)

        scrolled.add(treeview)
        vbox.pack_start(scrolled, True, True, 0)

        btn_clear = Gtk.Button(label="Clear Saved Lines")
        btn_clear.connect("clicked", self._on_clear_saved)
        vbox.pack_start(btn_clear, False, False, 0)

        return vbox

    def _on_literary_mode_changed(self, combo):
        model = combo.get_model()
        tree_iter = combo.get_active_iter()
        if tree_iter:
            val = model[tree_iter][0]
            self.config["literary_mode"] = val
            self.app.literary.set_mode(val)
            self.app.save_config()

    def _on_clear_saved(self, btn):
        self.app.literary.saved_works.clear()
        self.config["saved_quotes"] = []
        self.app.save_config()
        self.saved_store.clear()

    def _build_stats_tab(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_start(24)
        vbox.set_margin_end(24)

        summary = self.app.pomodoro.get_stats_summary()

        lbl_header = Gtk.Label()
        lbl_header.set_xalign(0.0)
        lbl_header.set_markup("<b>Today's Focus &amp; Companion Activity</b>")
        vbox.pack_start(lbl_header, False, False, 0)

        # Clean stats card
        stats_frame = Gtk.Frame()
        stats_frame.set_shadow_type(Gtk.ShadowType.IN)
        s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        s_box.set_margin_top(16)
        s_box.set_margin_bottom(16)
        s_box.set_margin_start(16)
        s_box.set_margin_end(16)

        lbl_s1 = Gtk.Label()
        lbl_s1.set_xalign(0.0)
        lbl_s1.set_markup(f"Focus Sessions Completed:  <b>{summary['sessions']}</b>")
        s_box.pack_start(lbl_s1, False, False, 0)

        lbl_s2 = Gtk.Label()
        lbl_s2.set_xalign(0.0)
        lbl_s2.set_markup(f"Total Focus Time:  <b>{summary['focus_time']}</b>")
        s_box.pack_start(lbl_s2, False, False, 0)

        lbl_s3 = Gtk.Label()
        lbl_s3.set_xalign(0.0)
        lbl_s3.set_markup(f"Literary Drops Read:  <b>{summary['drops_read']}</b>")
        s_box.pack_start(lbl_s3, False, False, 0)

        stats_frame.add(s_box)
        vbox.pack_start(stats_frame, False, False, 0)

        lbl_note = Gtk.Label()
        lbl_note.set_xalign(0.0)
        lbl_note.set_markup("<span size='small' color='#777'><i>Daily stats reset naturally each morning. Minimalist, private, stored only on your local system.</i></span>")
        vbox.pack_start(lbl_note, False, False, 0)

        return vbox

    def _build_about_tab(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox.set_margin_top(24)
        vbox.set_margin_bottom(24)
        vbox.set_margin_start(24)
        vbox.set_margin_end(24)

        lbl_app = Gtk.Label()
        lbl_app.set_xalign(0.0)
        lbl_app.set_markup("<span size='x-large' weight='bold'>MIU</span>")
        vbox.pack_start(lbl_app, False, False, 0)

        lbl_desc = Gtk.Label()
        lbl_desc.set_xalign(0.0)
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_markup(
            "A quiet desktop companion for focus,\n"
            "small moments of literature,\n"
            "and a little company while you work."
        )
        vbox.pack_start(lbl_desc, False, False, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        lbl_attr = Gtk.Label()
        lbl_attr.set_xalign(0.0)
        lbl_attr.set_line_wrap(True)
        lbl_attr.set_markup(
            "<span color='#888'>Initially based on Oneko.\n"
            "Later customized and evolved by Vaibhava.</span>"
        )
        vbox.pack_start(lbl_attr, False, False, 0)

        lbl_ver = Gtk.Label()
        lbl_ver.set_xalign(0.0)
        lbl_ver.set_markup("<span size='small' color='#666'>Version 2.0.0</span>")
        vbox.pack_start(lbl_ver, False, False, 0)

        return vbox

