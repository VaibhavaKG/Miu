# Miu 2.0 🐾

> A tiny, futuristic, playful desktop companion that happens to live on your Linux screen.

Miu is a lightweight, frameless, transparent desktop companion built natively in Python, GTK 3, and Cairo. Originally inspired by the classic Oneko, Miu has evolved into a complete, modern companion ecosystem: autonomous ambient life, celestial interactive control center, optional Pomodoro focus sessions, strict one-line literary drops, and zero-distraction desktop awareness.

---

## ✦ What Makes Miu Special?

* **Desktop Companion First**: By default, Miu is just Miu — trotting around, napping in cozy window corners, batting yarn balls, and keeping quiet company. No permanent ticking countdowns.
* **Miu Home Console (`miu --home`)**: An astronomical observatory dashboard featuring dynamic telemetry, live viewport habitat, Spotify / MPRIS Now Playing integration, and character customization.
* **Autonomous Living World**: Miu discovers tiny desktop objects (leaves, coins, scraps), plays with yarn balls with real physics, sits in cardboard boxes, and respects your cursor by gently evading your work.
* **Optional Pomodoro Engine (`miu --pomodoro`)**: When you need deep focus, activate dedicated 45-minute focus cycles with short/long breaks and isolated 60-second celebratory overlays.
* **Curated Literary Drops**: 106 verified one-line public-domain literary moments delivered with elegance during breaks or on demand.
* **Zero Bloat & Zero Telemetry**: Native GTK3 and Cairo rendering. No Electron, no browser runtimes, no tracking. All data is saved strictly to your local XDG user directories.

---

## 🚀 Quick Start

### Installation

Ensure system dependencies are installed:

#### Fedora / RHEL
```bash
sudo dnf install python3-gobject gtk3 cairo libappindicator-gtk3 libwnck3
```

#### Ubuntu / Debian
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 gir1.2-wnck-3.0
```

#### Arch Linux
```bash
sudo pacman -S python-gobject gtk3 cairo libappindicator-gtk3 libwnck3
```

Clone and run directly:
```bash
git clone https://github.com/yourusername/Miu.git ~/.local/share/miu-app
~/.local/share/miu-app/bin/miu
```

---

## 🕹 Command-Line Interface (`miu` / `hi miu`)

Miu accepts both `miu` and `hi miu` command styles:

| Command | Action |
| :--- | :--- |
| `miu` or `hi miu` | Start / wake Miu desktop companion |
| `miu --home` | Open the Miu Home futuristic control console |
| `miu --pomodoro` | Start / toggle optional Pomodoro focus mode |
| `miu --focus` | Immediately start a 45-minute deep focus session |
| `miu --pause` | Pause the active focus timer |
| `miu --resume` | Resume the active focus timer |
| `miu --reset` | Reset timer to idle state |
| `miu --break` | Start a 5-minute break |
| `miu --literary` | Deliver a single-line literary quote |
| `miu --customize` | Open pet character customizer |
| `miu --stats` | View focus and reading telemetry |
| `miu summon` | Summon Miu to your cursor / workspace (`Ctrl+M`) |
| `miu --stop` | Cleanly rest and close Miu |

---

## 🛰 Miu Home Observatory

Launch the interactive control console at any time:

```bash
miu --home
```

Inside Miu Home:
* **Habitat**: Watch Miu live inside the celestial viewport, toss a yarn ball, or track what song is currently playing on Spotify.
* **Appearance**: Switch between 8 coat themes (Classic, Ginger, Midnight Black, Sakura, Calico, etc.), hats, glasses, and eye expressions.
* **Focus Hub**: Dedicated focus controls and status readouts.
* **Library**: Browse the full library of classic literature lines and saved favorites.
* **Telemetry**: View daily session counts, total focused hours, and activity logs.

---

## 📁 System Data (XDG Compliant)

Miu strictly isolates static package code from user state:

* **Configuration**: `~/.config/miu/config.json`
* **Custom Overlays**: `~/.local/share/miu/accessories/`
* **Media Cache**: `~/.cache/miu/album_art/`
* **Logs**: `~/.local/share/miu/miu.log`
* **IPC Socket**: `$XDG_RUNTIME_DIR/miu.sock`

---

## 🧪 Testing

Miu includes a comprehensive test suite covering all engines, IPC, Cairo rendering, and desktop lifecycle:

```bash
GDK_BACKEND=x11 python3 -m unittest discover -s tests -v
```

---

## 📜 Attribution & License

Initially based on Oneko. Evolved, redesigned, and packaged by Vaibhava.

Released under the **MIT License**.
