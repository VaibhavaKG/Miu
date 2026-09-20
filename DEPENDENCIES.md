# Dependencies & System Requirements

Miu is designed to run natively on Linux with standard GNOME / X11 / Xwayland desktop environments.

## Python Requirements
- **Python**: 3.9+ (Python 3.14+ supported)
- Standard library modules: `os`, `sys`, `time`, `json`, `math`, `random`, `subprocess`, `socket`, `pathlib`, `shutil`

## System Libraries & GObject Introspection
Miu uses PyGObject for GTK 3 and Cairo integration:
- `python3-gobject` (`gi`)
- `gtk3` (`Gtk 3.0`, `Gdk 3.0`)
- `cairo` (`pycairo`)
- `libappindicator-gtk3` or `libayatana-appindicator3` (for system tray integration)
- `xdotool` or `wmctrl` (optional, for window topology discovery on X11)
- `libcanberra-gtk3` (optional, for alert sounds)

On Fedora / RHEL:
```bash
sudo dnf install python3-gobject gtk3 pycairo libappindicator-gtk3
```

On Ubuntu / Debian:
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1
```
