"""
System Tray & Context Menu Architecture for Oneko Desktop Companion.

Integrates with AppIndicator3 (GNOME/X11) and desktop right-click menu:
PET
├── Pause / Wake
└── Customize...
FOCUS
├── Start 45 min Focus (or Pause / Resume)
├── Reset
└── Skip
LITERATURE
├── Show Literary Drop
└── Saved Lines ({count})
SETTINGS
└── Preferences...
QUIT
"""

import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3
    HAS_APP_INDICATOR = True
except Exception:
    HAS_APP_INDICATOR = False


class TrayManager:
    def __init__(self, app):
        self.app = app
        self.indicator = None
        self.menu = None

        if HAS_APP_INDICATOR:
            try:
                self.indicator = AppIndicator3.Indicator.new(
                    f"miu-companion-{os.getpid()}",
                    "oneko",
                    AppIndicator3.IndicatorCategory.APPLICATION_STATUS
                )
                self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
                self.menu = self.build_menu()
                self.indicator.set_menu(self.menu)
            except Exception as e:
                print("Could not initialize AppIndicator3:", e)
                self.indicator = None

    def build_menu(self):
        menu = Gtk.Menu()

        # 1. Active notification dismiss shortcut if open
        if self.app.literary.is_active:
            mi_dismiss = Gtk.MenuItem(label="Dismiss Literary Drop")
            mi_dismiss.connect("activate", lambda w: self.app.dismiss_active_popup())
            menu.append(mi_dismiss)
            menu.append(Gtk.SeparatorMenuItem())

        # 2. PET Section
        pet_title = Gtk.MenuItem(label=f"🐾 {self.app.config.get('pet_name', 'Miu')}")
        pet_title.set_sensitive(False)
        menu.append(pet_title)

        if self.app.pet_state.is_paused:
            mi_pet_wake = Gtk.MenuItem(label="  Wake / Resume Pet")
            mi_pet_wake.connect("activate", lambda w: self.app.set_pet_paused(False))
            menu.append(mi_pet_wake)
        else:
            mi_pet_pause = Gtk.MenuItem(label="  Pause Pet Movement")
            mi_pet_pause.connect("activate", lambda w: self.app.set_pet_paused(True))
            menu.append(mi_pet_pause)

        mi_summon = Gtk.MenuItem(label="  Summon Miu (Ctrl+M)")
        mi_summon.connect("activate", lambda w: self.app.summon_miu())
        menu.append(mi_summon)

        mi_home = Gtk.MenuItem(label="  Open Miu Home")
        mi_home.connect("activate", lambda w: self.app.open_home() if hasattr(self.app, "open_home") else self.app.open_preferences())
        menu.append(mi_home)

        mi_custom = Gtk.MenuItem(label="  Customize...")
        mi_custom.connect("activate", lambda w: self.app.open_preferences())
        menu.append(mi_custom)

        menu.append(Gtk.SeparatorMenuItem())

        # 3. FOCUS Section (Optional / Toggleable)
        pomodoro_enabled = self.app.config.get("pomodoro_enabled", False)
        phase = self.app.pomodoro.phase
        time_str = self.app.pomodoro.get_time_string()
        dur = self.app.config.get("focus_duration_min", 45)

        if pomodoro_enabled or phase != "IDLE":
            if phase == "FOCUS":
                focus_lbl = f"⏱️ Focus ({time_str})"
            elif phase == "PAUSED":
                focus_lbl = f"⏸️ Paused ({time_str})"
            elif phase in ("BREAK", "LONG_BREAK"):
                focus_lbl = f"☕ Break ({time_str})"
            else:
                focus_lbl = f"⏱️ Focus Mode"

            mi_focus_title = Gtk.MenuItem(label=focus_lbl)
            mi_focus_title.set_sensitive(False)
            menu.append(mi_focus_title)

            if phase == "FOCUS":
                mi_pause = Gtk.MenuItem(label="  Pause")
                mi_pause.connect("activate", lambda w: self.app.pomodoro.pause())
                menu.append(mi_pause)
            elif phase == "PAUSED":
                mi_resume = Gtk.MenuItem(label="  Resume")
                mi_resume.connect("activate", lambda w: self.app.pomodoro.resume())
                menu.append(mi_resume)
            else:
                mi_start = Gtk.MenuItem(label=f"  Start {dur} min Focus")
                mi_start.connect("activate", lambda w: self.app.start_focus_session())
                menu.append(mi_start)

            mi_reset = Gtk.MenuItem(label="  Reset")
            mi_reset.connect("activate", lambda w: self.app.reset_session() if hasattr(self.app, "reset_session") else self.app.pomodoro.reset())
            menu.append(mi_reset)

            mi_skip = Gtk.MenuItem(label="  Skip")
            mi_skip.connect("activate", lambda w: self.app.pomodoro.skip())
            menu.append(mi_skip)

            mi_disable_pom = Gtk.MenuItem(label="  Turn Off Focus Mode")
            def _disable_pom(w):
                self.app.config["pomodoro_enabled"] = False
                self.app.save_config()
                self.update_menu()
                self.app.update_window_shape_and_size()
                self.app.queue_draw()
            mi_disable_pom.connect("activate", _disable_pom)
            menu.append(mi_disable_pom)
        else:
            mi_enable_pom = Gtk.MenuItem(label="⏱️ Enable Focus Mode")
            def _enable_pom(w):
                self.app.config["pomodoro_enabled"] = True
                self.app.save_config()
                self.update_menu()
                self.app.update_window_shape_and_size()
                self.app.queue_draw()
            mi_enable_pom.connect("activate", _enable_pom)
            menu.append(mi_enable_pom)

        menu.append(Gtk.SeparatorMenuItem())

        # 4. LITERATURE Section
        lit_title = Gtk.MenuItem(label="📖 Literature")
        lit_title.set_sensitive(False)
        menu.append(lit_title)

        mi_drop = Gtk.MenuItem(label="  Show Literary Drop")
        mi_drop.connect("activate", lambda w: self.app.trigger_literary_drop())
        menu.append(mi_drop)

        saved_count = len(self.app.literary.saved_works)
        mi_saved = Gtk.MenuItem(label=f"  Saved Lines ({saved_count})")
        mi_saved.connect("activate", lambda w: self.app.open_preferences_tab("literature"))
        menu.append(mi_saved)

        menu.append(Gtk.SeparatorMenuItem())

        # 5. SETTINGS Section
        mi_settings = Gtk.MenuItem(label="⚙️ Preferences...")
        mi_settings.connect("activate", lambda w: self.app.open_preferences())
        menu.append(mi_settings)

        menu.append(Gtk.SeparatorMenuItem())

        # 6. QUIT
        mi_quit = Gtk.MenuItem(label="❌ Quit Miu")
        mi_quit.connect("activate", lambda w: self.app.quit_app())
        menu.append(mi_quit)

        menu.show_all()
        return menu

    def update_menu(self):
        if self.indicator:
            self.menu = self.build_menu()
            self.indicator.set_menu(self.menu)

    def popup_context_menu(self, event):
        menu = self.build_menu()
        menu.popup_at_pointer(event)
